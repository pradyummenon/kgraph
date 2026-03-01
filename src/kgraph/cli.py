"""CLI entry point for kgraph.

Commands:
    init    — Set up Neo4j connection + config
    ingest  — Extract entities/relationships from documents → Neo4j
    query   — Natural language → hybrid retrieval → answer
    explore — Show an entity's neighborhood as a Rich tree
    stats   — Display graph statistics
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(
    name="kgraph",
    help="Build and query knowledge graphs from documents.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
) -> None:
    """Build and query knowledge graphs from documents."""
    from kgraph.logging import configure_logging

    configure_logging(level="DEBUG" if verbose else "INFO")


@app.command()
def init() -> None:
    """Set up Neo4j connection, API keys, and required indexes."""
    from kgraph.application.use_cases import InitUseCase

    use_case = InitUseCase(console=console)
    use_case.execute()


@app.command()
def ingest(
    path: Annotated[
        Path,
        typer.Argument(help="File or directory to ingest (.txt, .md)"),
    ],
    batch_size: Annotated[
        int,
        typer.Option("--batch-size", "-b", help="Batch size for Neo4j writes"),
    ] = 10_000,
) -> None:
    """Extract entities and relationships from documents into Neo4j."""
    import asyncio

    from kgraph.application.factories import create_embedder, create_extractor, create_graph
    from kgraph.application.use_cases import IngestUseCase
    from kgraph.config import load_config

    config = load_config()
    extractor = create_extractor(config)
    embedder = create_embedder(config)
    graph = create_graph(config)
    use_case = IngestUseCase(extractor=extractor, embedder=embedder, graph=graph, console=console)
    asyncio.run(use_case.execute(path=path, batch_size=batch_size))


@app.command()
def query(
    question: Annotated[
        str,
        typer.Argument(help="Natural language question to answer"),
    ],
    mode: Annotated[
        str,
        typer.Option("--mode", "-m", help="Retrieval mode: hybrid, vector, cypher"),
    ] = "hybrid",
    top_k: Annotated[
        int,
        typer.Option("--top-k", "-k", help="Number of initial vector matches"),
    ] = 20,
    hops: Annotated[
        int,
        typer.Option("--hops", help="Graph traversal depth"),
    ] = 2,
    raw: Annotated[
        bool,
        typer.Option("--raw", help="Show raw context sent to LLM"),
    ] = False,
) -> None:
    """Query the knowledge graph with natural language."""
    import asyncio

    from kgraph.application.factories import create_embedder, create_graph
    from kgraph.application.use_cases import QueryUseCase
    from kgraph.config import load_config

    config = load_config()
    embedder = create_embedder(config)
    graph = create_graph(config)
    use_case = QueryUseCase(embedder=embedder, graph=graph, config=config, console=console)
    asyncio.run(
        use_case.execute(
            question=question,
            mode=mode,
            top_k=top_k,
            hops=hops,
            show_raw=raw,
        )
    )


@app.command()
def explore(
    entity_name: Annotated[
        str,
        typer.Argument(help="Entity name to explore"),
    ],
    hops: Annotated[
        int,
        typer.Option("--hops", help="Neighborhood depth"),
    ] = 2,
    types: Annotated[
        str | None,
        typer.Option("--types", "-t", help="Comma-separated entity type filter"),
    ] = None,
    rels: Annotated[
        str | None,
        typer.Option("--rels", "-r", help="Comma-separated relationship type filter"),
    ] = None,
) -> None:
    """Show an entity's neighborhood as a Rich tree with incoming/outgoing edges."""
    import asyncio

    from kgraph.application.factories import create_graph
    from kgraph.application.use_cases import ExploreUseCase
    from kgraph.config import load_config

    type_filters = set(types.upper().split(",")) if types else None
    rel_filters = set(rels.upper().split(",")) if rels else None

    config = load_config()
    graph = create_graph(config)
    use_case = ExploreUseCase(graph=graph, console=console)
    asyncio.run(
        use_case.execute(
            entity_name=entity_name,
            hops=hops,
            type_filters=type_filters,
            rel_filters=rel_filters,
        )
    )


@app.command()
def visualize(
    entity_name: Annotated[
        str | None,
        typer.Argument(help="Entity name to center on (omit for overview)"),
    ] = None,
    hops: Annotated[
        int,
        typer.Option("--hops", help="Neighborhood depth for entity-centered mode"),
    ] = 2,
    types: Annotated[
        str | None,
        typer.Option("--types", "-t", help="Comma-separated entity type filter"),
    ] = None,
    no_labels: Annotated[
        bool,
        typer.Option("--no-labels", help="Omit edge labels from the ASCII diagram"),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write ASCII diagram to this file path"),
    ] = None,
    max_nodes: Annotated[
        int,
        typer.Option("--max-nodes", help="Maximum number of nodes for overview mode"),
    ] = 50,
) -> None:
    """Render knowledge graph as ASCII art."""
    import asyncio

    from kgraph.application.factories import create_graph
    from kgraph.application.use_cases import VisualizeUseCase
    from kgraph.config import load_config

    type_filters = set(types.upper().split(",")) if types else None
    config = load_config()
    graph = create_graph(config)
    use_case = VisualizeUseCase(graph=graph, console=console)
    asyncio.run(
        use_case.execute(
            entity_name=entity_name,
            hops=hops,
            entity_types=type_filters,
            show_edge_labels=not no_labels,
            output_path=output,
            max_nodes=max_nodes,
        )
    )


@app.command()
def browse(
    entity_name: Annotated[
        str | None,
        typer.Argument(help="Entity to start from (omit for overview)"),
    ] = None,
    hops: Annotated[
        int,
        typer.Option("--hops", help="Initial neighborhood depth"),
    ] = 2,
) -> None:
    """Launch interactive graph browser TUI."""
    from kgraph.application.factories import create_graph
    from kgraph.config import load_config
    from kgraph.interfaces.browser import GraphBrowser

    config = load_config()
    graph = create_graph(config)
    app = GraphBrowser(graph=graph, start_entity=entity_name, hops=hops)
    app.run()


@app.command()
def stats() -> None:
    """Display knowledge graph statistics."""
    import asyncio

    from kgraph.application.factories import create_graph
    from kgraph.application.use_cases import StatsUseCase
    from kgraph.config import load_config

    config = load_config()
    graph = create_graph(config)
    use_case = StatsUseCase(graph=graph, console=console)
    asyncio.run(use_case.execute())


if __name__ == "__main__":
    app()
