"""CLI entry point for kgraph.

Commands:
    init    — Set up Neo4j connection + config
    ingest  — Extract entities/relationships from documents → Neo4j
    query   — Natural language → hybrid retrieval → answer
    explore — Show an entity's neighborhood as a Rich tree
    stats   — Display graph statistics
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="kgraph",
    help="Build and query knowledge graphs from documents.",
    no_args_is_help=True,
)
console = Console()


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
    from kgraph.application.use_cases import IngestUseCase
    from kgraph.config import load_config

    config = load_config()
    use_case = IngestUseCase(config=config, console=console)
    use_case.execute(path=path, batch_size=batch_size)


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
    from kgraph.application.use_cases import QueryUseCase
    from kgraph.config import load_config

    config = load_config()
    use_case = QueryUseCase(config=config, console=console)
    use_case.execute(
        question=question,
        mode=mode,
        top_k=top_k,
        hops=hops,
        show_raw=raw,
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
) -> None:
    """Show an entity's neighborhood as a Rich tree."""
    from kgraph.application.use_cases import ExploreUseCase
    from kgraph.config import load_config

    config = load_config()
    use_case = ExploreUseCase(config=config, console=console)
    use_case.execute(entity_name=entity_name, hops=hops)


@app.command()
def stats() -> None:
    """Display knowledge graph statistics."""
    from kgraph.application.use_cases import StatsUseCase
    from kgraph.config import load_config

    config = load_config()
    use_case = StatsUseCase(config=config, console=console)
    use_case.execute()


if __name__ == "__main__":
    app()
