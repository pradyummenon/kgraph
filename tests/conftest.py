"""Shared test fixtures for kgraph."""

from unittest.mock import AsyncMock

import pytest

from kgraph.domain.models import Chunk, Entity, EntityType, Relationship


@pytest.fixture
def sample_chunk() -> Chunk:
    """A sample text chunk for testing."""
    return Chunk(
        text=(
            "Marie Curie was a Polish-French physicist who conducted pioneering "
            "research on radioactivity. She was the first woman to win a Nobel Prize "
            "and worked at the University of Paris."
        ),
        source_file="test.md",
        chunk_index=0,
        total_chunks=1,
    )


@pytest.fixture
def sample_entities() -> list[Entity]:
    """Sample entities for testing."""
    return [
        Entity(
            name="Marie Curie",
            entity_type=EntityType.PERSON,
            description="Polish-French physicist, pioneer in radioactivity research",
            source="test.md [chunk 1/1]",
        ),
        Entity(
            name="University of Paris",
            entity_type=EntityType.ORGANIZATION,
            description="French university where Marie Curie worked",
            source="test.md [chunk 1/1]",
        ),
        Entity(
            name="Nobel Prize",
            entity_type=EntityType.EVENT,
            description="Prestigious international award in physics",
            source="test.md [chunk 1/1]",
        ),
    ]


@pytest.fixture
def sample_relationships() -> list[Relationship]:
    """Sample relationships for testing."""
    return [
        Relationship(
            source="Marie Curie",
            target="University of Paris",
            relationship_type="WORKS_AT",
            description="Marie Curie worked at the University of Paris",
        ),
        Relationship(
            source="Marie Curie",
            target="Nobel Prize",
            relationship_type="WON",
            description="First woman to win the Nobel Prize",
        ),
    ]


@pytest.fixture
def mock_graph() -> AsyncMock:
    """Mock GraphRepository for testing."""
    return AsyncMock()


@pytest.fixture
def mock_extractor() -> AsyncMock:
    """Mock EntityExtractor for testing."""
    return AsyncMock()


@pytest.fixture
def mock_embedder() -> AsyncMock:
    """Mock EmbeddingGenerator for testing."""
    mock = AsyncMock()
    mock.dimensions = 1536
    return mock
