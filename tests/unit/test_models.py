"""Tests for domain models."""

from kgraph.domain.models import Entity, Relationship
from kgraph.domain.services import deduplicate_entities, deduplicate_relationships


class TestEntity:
    """Tests for the Entity domain model."""

    def test_normalized_name_is_lowercase_stripped(self) -> None:
        entity = Entity(
            name="  Marie Curie  ",
            entity_type="PERSON",
            description="Physicist",
            source="test.md",
        )
        assert entity.normalized_name == "marie curie"

    def test_embedding_text_combines_name_and_description(self) -> None:
        entity = Entity(
            name="Marie Curie",
            entity_type="PERSON",
            description="Polish-French physicist",
            source="test.md",
        )
        assert entity.embedding_text == "Marie Curie: Polish-French physicist"


class TestDeduplication:
    """Tests for entity and relationship deduplication."""

    def test_deduplicate_entities_by_normalized_name(self) -> None:
        entities = [
            Entity(name="Marie Curie", entity_type="PERSON", description="Short", source="a"),
            Entity(name="marie curie", entity_type="PERSON", description="Longer description", source="b"),
        ]
        result = deduplicate_entities(entities)
        assert len(result) == 1
        assert result[0].description == "Longer description"

    def test_deduplicate_relationships(self) -> None:
        rels = [
            Relationship(source="A", target="B", relationship_type="KNOWS", description="v1"),
            Relationship(source="a", target="b", relationship_type="KNOWS", description="longer v2"),
        ]
        result = deduplicate_relationships(rels)
        assert len(result) == 1
        assert result[0].description == "longer v2"
