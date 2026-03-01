"""Application use cases for kgraph.

Orchestrates domain services and infrastructure adapters
to implement the CLI commands.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from kgraph.config import (
    CONFIG_FILE,
    EmbeddingConfig,
    KgraphConfig,
    LLMConfig,
    Neo4jConfig,
    save_config,
)
from kgraph.domain.models import Entity
from kgraph.domain.services import (
    EmbeddingGenerator,
    EntityExtractor,
    GraphRepository,
    deduplicate_entities,
    deduplicate_relationships,
)
from kgraph.infrastructure.chunker import chunk_text, read_documents
from kgraph.infrastructure.graph import Neo4jGraph
from kgraph.infrastructure.retriever import HybridRetriever

if TYPE_CHECKING:
    pass


class InitUseCase:
    """Set up Neo4j connection, API keys, and required indexes."""

    def __init__(self, console: Console) -> None:
        self._console = console

    def execute(self) -> None:
        import typer

        self._console.print("\n[bold]kgraph init[/bold] — setting up your knowledge graph\n")

        # Collect Neo4j config
        uri = typer.prompt("Neo4j URI", default="bolt://localhost:7687")
        username = typer.prompt("Neo4j username", default="neo4j")
        password = typer.prompt("Neo4j password", default="kgraph-password", hide_input=True)

        # Collect LLM provider
        llm_provider = typer.prompt("LLM provider (anthropic/gemini)", default="gemini")

        anthropic_key = ""
        gemini_llm_key = ""
        llm_model = ""
        if llm_provider == "anthropic":
            anthropic_key = typer.prompt("Anthropic API key", hide_input=True)
            llm_model = "claude-sonnet-4-20250514"
        else:
            gemini_llm_key = typer.prompt("Gemini API key", hide_input=True)
            llm_model = "gemini-2.0-flash"

        # Collect embedding provider
        default_embed = "gemini" if llm_provider == "gemini" else "openai"
        embedding_provider = typer.prompt(
            "Embedding provider (openai/gemini/local)", default=default_embed
        )

        openai_key = ""
        gemini_embed_key = ""
        if embedding_provider == "openai":
            openai_key = typer.prompt("OpenAI API key (for embeddings)", hide_input=True)
            dim = 1536
        elif embedding_provider == "gemini":
            # Reuse Gemini key if already provided, otherwise ask
            if gemini_llm_key:
                gemini_embed_key = gemini_llm_key
                self._console.print("  [dim]Reusing Gemini API key for embeddings[/dim]")
            else:
                gemini_embed_key = typer.prompt("Gemini API key (for embeddings)", hide_input=True)
            dim = 768
        else:
            dim = 768

        config = KgraphConfig(
            neo4j=Neo4jConfig(uri=uri, username=username, password=password),
            llm=LLMConfig(
                provider=llm_provider,
                anthropic_api_key=anthropic_key,
                gemini_api_key=gemini_llm_key,
                model=llm_model,
            ),
            embedding=EmbeddingConfig(
                provider=embedding_provider,
                openai_api_key=openai_key,
                gemini_api_key=gemini_embed_key,
                dimensions=dim,
            ),
        )

        # Save config
        save_config(config)
        self._console.print(f"  [green]✓[/green] Config saved to {CONFIG_FILE}")

        # Test Neo4j connection — all async ops in a single event loop
        import asyncio

        async def _test_and_setup() -> None:
            graph = Neo4jGraph(uri=uri, username=username, password=password)
            connected = await graph.verify_connection()
            if connected:
                self._console.print("  [green]✓[/green] Neo4j connection verified")
                await graph.ensure_indexes(vector_dimensions=dim)
                self._console.print("  [green]✓[/green] Indexes and constraints created")
                await graph.close()
            else:
                self._console.print("  [red]✗[/red] Could not connect to Neo4j")
                self._console.print("    Make sure Neo4j is running and credentials are correct.")

        asyncio.run(_test_and_setup())

        self._console.print("\n[bold green]Setup complete![/bold green]\n")


class IngestUseCase:
    """Extract entities and relationships from documents into Neo4j."""

    def __init__(
        self,
        extractor: EntityExtractor,
        embedder: EmbeddingGenerator,
        graph: GraphRepository,
        console: Console,
    ) -> None:
        self._extractor = extractor
        self._embedder = embedder
        self._graph = graph
        self._console = console

    async def execute(self, path: Path, batch_size: int = 10_000) -> None:
        async with self._graph:
            await self._run(path, batch_size)

    async def _run(self, path: Path, batch_size: int) -> None:
        # Read documents
        documents = read_documents(path)
        self._console.print(f"  Found {len(documents)} document(s)")

        # Chunk all documents
        all_chunks = []
        for filename, content in documents:
            chunks = chunk_text(content, filename)
            all_chunks.extend(chunks)
        self._console.print(f"  Split into {len(all_chunks)} chunks")

        all_entities: list[Entity] = []
        all_relationships = []

        # Extract entities and relationships
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self._console,
        ) as progress:
            task = progress.add_task("Extracting entities...", total=len(all_chunks))

            for chunk in all_chunks:
                result = await self._extractor.extract(chunk)
                all_entities.extend(result.entities)
                all_relationships.extend(result.relationships)
                progress.advance(task)

        # Deduplicate
        all_entities = deduplicate_entities(all_entities)
        all_relationships = deduplicate_relationships(all_relationships)
        self._console.print(
            f"  Extracted {len(all_entities)} unique entities, "
            f"{len(all_relationships)} unique relationships"
        )

        # Generate embeddings
        self._console.print("  Generating embeddings...")
        texts = [e.embedding_text for e in all_entities]
        embeddings = await self._embedder.embed(texts)

        # Attach embeddings to entities
        entities_with_embeddings = [
            Entity(
                name=e.name,
                entity_type=e.entity_type,
                description=e.description,
                source=e.source,
                embedding=tuple(emb),
            )
            for e, emb in zip(all_entities, embeddings, strict=True)
        ]

        # Ingest into Neo4j
        self._console.print("  Writing to Neo4j...")
        entity_count = await self._graph.ingest_entities(entities_with_embeddings, batch_size)
        rel_count = await self._graph.ingest_relationships(all_relationships, batch_size)

        # Summary
        table = Table(title="Ingestion Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_row("Documents processed", str(len(documents)))
        table.add_row("Chunks processed", str(len(all_chunks)))
        table.add_row("Entities written", str(entity_count))
        table.add_row("Relationships written", str(rel_count))
        self._console.print(table)


class QueryUseCase:
    """Query the knowledge graph with natural language."""

    def __init__(
        self,
        embedder: EmbeddingGenerator,
        graph: GraphRepository,
        config: KgraphConfig,
        console: Console,
    ) -> None:
        self._embedder = embedder
        self._graph = graph
        self._config = config
        self._console = console

    async def execute(
        self,
        question: str,
        mode: str = "hybrid",
        top_k: int = 20,
        hops: int = 2,
        show_raw: bool = False,
    ) -> None:
        async with self._graph:
            await self._run(question, mode, top_k, hops, show_raw)

    async def _run(self, question: str, mode: str, top_k: int, hops: int, show_raw: bool) -> None:
        start = time.monotonic()

        # Embed the question
        question_embedding = (await self._embedder.embed([question]))[0]

        # Retrieve context
        retriever = HybridRetriever(self._graph)
        retrieval = await retriever.retrieve(question_embedding, top_k=top_k, hops=hops)

        if show_raw:
            self._console.print(Panel(retrieval.context_text, title="Raw Context"))

        # Generate answer using configured LLM
        answer_system = (
            "You are a knowledge graph assistant. Answer the question using ONLY "
            "the provided graph context. If the context doesn't contain enough "
            "information, say so. Cite entity names when referencing information."
        )
        answer_prompt = f"Graph context:\n{retrieval.context_text}\n\nQuestion: {question}"

        if self._config.llm.provider == "gemini":
            from google import genai
            from google.genai import types as genai_types

            gemini_client = genai.Client(api_key=self._config.llm.gemini_api_key)
            response = await gemini_client.aio.models.generate_content(
                model=self._config.llm.model,
                contents=answer_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=answer_system,
                ),
            )
            answer = response.text
        else:
            client = anthropic.AsyncAnthropic(api_key=self._config.llm.anthropic_api_key)
            response = await client.messages.create(
                model=self._config.llm.model,
                max_tokens=self._config.llm.max_tokens,
                system=answer_system,
                messages=[{"role": "user", "content": answer_prompt}],
            )
            answer = response.content[0].text
        elapsed = (time.monotonic() - start) * 1000

        # Display
        self._console.print(Panel(answer, title="Answer", border_style="green"))
        self._console.print(
            f"  [dim]Retrieved {len(retrieval.entities)} entities, "
            f"{len(retrieval.relationships)} relationships "
            f"in {elapsed:.0f}ms[/dim]"
        )


class ExploreUseCase:
    """Show an entity's neighborhood as a Rich tree."""

    def __init__(self, graph: GraphRepository, console: Console) -> None:
        self._graph = graph
        self._console = console

    async def execute(self, entity_name: str, hops: int = 2) -> None:
        async with self._graph:
            await self._run(entity_name, hops)

    async def _run(self, entity_name: str, hops: int) -> None:
        # Fuzzy match entity name
        matches = await self._graph.fulltext_search(entity_name, limit=1)
        if not matches:
            self._console.print(f"[red]No entity found matching '{entity_name}'[/red]")
            return

        root_entity = matches[0]
        entities, relationships = await self._graph.expand_neighborhood([root_entity.name], hops)

        # Build tree
        tree = Tree(
            f"[bold cyan]{root_entity.name}[/bold cyan] "
            f"({root_entity.entity_type}) — {root_entity.description}"
        )

        # Group relationships by type
        rels_from_root = [r for r in relationships if r.source == root_entity.name]
        by_type: dict[str, list[str]] = {}
        for r in rels_from_root:
            by_type.setdefault(r.relationship_type, []).append(r.target)

        for rel_type, targets in by_type.items():
            branch = tree.add(f"[yellow]{rel_type}[/yellow]")
            for target_name in targets:
                target = next((e for e in entities if e.name == target_name), None)
                if target:
                    branch.add(
                        f"[green]{target.name}[/green] "
                        f"({target.entity_type}) — {target.description}"
                    )
                else:
                    branch.add(f"[green]{target_name}[/green]")

        self._console.print(tree)


class StatsUseCase:
    """Display knowledge graph statistics."""

    def __init__(self, graph: GraphRepository, console: Console) -> None:
        self._graph = graph
        self._console = console

    async def execute(self) -> None:
        async with self._graph:
            await self._run()

    async def _run(self) -> None:
        stats = await self._graph.get_stats()

        table = Table(title="Knowledge Graph Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_row("Total entities", str(stats.get("nodes", 0)))
        table.add_row("Total relationships", str(stats.get("relationships", 0)))
        self._console.print(table)
