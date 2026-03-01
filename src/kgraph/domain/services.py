"""Domain services for kgraph.

Pure business logic that orchestrates domain objects.
No infrastructure dependencies — those are injected via protocols.
"""

from __future__ import annotations

from typing import Protocol

from kgraph.domain.models import (
    Chunk,
    Entity,
    ExtractionResult,
    Relationship,
)


class EntityExtractor(Protocol):
    """Protocol for extracting entities and relationships from text."""

    async def extract(self, chunk: Chunk) -> ExtractionResult:
        """Extract entities and relationships from a text chunk."""
        ...


class EmbeddingGenerator(Protocol):
    """Protocol for generating text embeddings."""

    async def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Generate embeddings for a batch of texts."""
        ...

    @property
    def dimensions(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        ...


class GraphRepository(Protocol):
    """Protocol for graph database operations."""

    async def ensure_indexes(self, vector_dimensions: int) -> None:
        """Create required indexes and constraints."""
        ...

    async def ingest_entities(self, entities: list[Entity]) -> int:
        """Batch ingest entities. Returns count of entities written."""
        ...

    async def ingest_relationships(self, relationships: list[Relationship]) -> int:
        """Batch ingest relationships. Returns count of relationships written."""
        ...

    async def vector_search(self, embedding: list[float], top_k: int) -> list[tuple[Entity, float]]:
        """Find similar entities by vector similarity. Returns (entity, score) pairs."""
        ...

    async def expand_neighborhood(
        self, entity_names: list[str], hops: int
    ) -> tuple[list[Entity], list[Relationship]]:
        """Expand entity neighborhoods by traversing the graph."""
        ...

    async def fulltext_search(self, query: str, limit: int) -> list[Entity]:
        """Search entities by name/description using full-text index."""
        ...

    async def get_stats(self) -> dict[str, int]:
        """Get graph statistics (node count, relationship count, etc.)."""
        ...

    async def close(self) -> None:
        """Release all database connections and resources."""
        ...

    async def __aenter__(self) -> GraphRepository:
        """Enter async context manager."""
        ...

    async def __aexit__(self, *args: object) -> None:
        """Exit async context manager, closing all connections."""
        ...


def deduplicate_entities(entities: list[Entity]) -> list[Entity]:
    """Deduplicate entities by normalized name.

    When duplicates are found, keeps the entity with the longest description
    (likely the most informative).
    """
    seen: dict[str, Entity] = {}
    for entity in entities:
        key = entity.normalized_name
        if key not in seen or len(entity.description) > len(seen[key].description):
            seen[key] = entity
    return list(seen.values())


def deduplicate_relationships(relationships: list[Relationship]) -> list[Relationship]:
    """Deduplicate relationships by (source, target, type) tuple."""
    seen: dict[tuple[str, str, str], Relationship] = {}
    for rel in relationships:
        key = (rel.source.lower(), rel.target.lower(), rel.relationship_type)
        if key not in seen or len(rel.description) > len(seen[key].description):
            seen[key] = rel
    return list(seen.values())
