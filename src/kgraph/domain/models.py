"""Domain models for kgraph.

Core entities that represent the knowledge graph structure.
These are pure domain objects with no infrastructure dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EntityType(StrEnum):
    """Canonical entity types for the knowledge graph."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    CONCEPT = "CONCEPT"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    TECHNOLOGY = "TECHNOLOGY"

    @classmethod
    def from_llm_output(cls, value: str) -> EntityType:
        """Parse an EntityType from raw LLM output, defaulting to CONCEPT on unknown values."""
        try:
            return cls(value.upper())
        except ValueError:
            return cls.CONCEPT


@dataclass(frozen=True)
class Entity:
    """A node in the knowledge graph.

    Represents a real-world concept, person, organization, event, etc.
    extracted from source documents.
    """

    name: str
    entity_type: EntityType
    description: str
    source: str  # Source file + chunk reference
    embedding: tuple[float, ...] = ()

    @property
    def normalized_name(self) -> str:
        """Lowercase, stripped name for deduplication."""
        return self.name.lower().strip()

    @property
    def embedding_text(self) -> str:
        """Text to embed for vector search."""
        return f"{self.name}: {self.description}"


@dataclass(frozen=True)
class Relationship:
    """An edge in the knowledge graph.

    Represents a typed connection between two entities,
    with a description providing context.
    """

    source: str  # Source entity name
    target: str  # Target entity name
    relationship_type: str  # WORKS_AT, PART_OF, CAUSES, RELATES_TO, etc.
    description: str  # Context of the relationship


@dataclass(frozen=True)
class Chunk:
    """A text chunk from a source document.

    Tracks provenance back to the original file and position.
    """

    text: str
    source_file: str
    chunk_index: int
    total_chunks: int

    @property
    def source_reference(self) -> str:
        """Human-readable source reference."""
        return f"{self.source_file} [chunk {self.chunk_index + 1}/{self.total_chunks}]"


@dataclass(frozen=True)
class ExtractionResult:
    """Result of entity/relationship extraction from a single chunk."""

    entities: list[Entity]
    relationships: list[Relationship]
    source_chunk: Chunk


@dataclass(frozen=True)
class RetrievalResult:
    """Result of a retrieval query against the graph."""

    entities: list[Entity]
    relationships: list[Relationship]
    context_text: str  # Formatted context for LLM
    vector_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryResult:
    """Final result of a natural language query."""

    answer: str
    retrieval: RetrievalResult
    latency_ms: float
