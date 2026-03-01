"""Tests for domain models."""

import pytest

from kgraph.config import (
    EmbeddingConfig,
    KgraphConfig,
    LLMConfig,
    Neo4jConfig,
    validate_config,
)
from kgraph.domain.errors import ConfigError
from kgraph.domain.models import Entity, EntityType, Relationship
from kgraph.domain.services import deduplicate_entities, deduplicate_relationships


class TestEntity:
    """Tests for the Entity domain model."""

    def test_normalized_name_is_lowercase_stripped(self) -> None:
        entity = Entity(
            name="  Marie Curie  ",
            entity_type=EntityType.PERSON,
            description="Physicist",
            source="test.md",
        )
        assert entity.normalized_name == "marie curie"

    def test_embedding_text_combines_name_and_description(self) -> None:
        entity = Entity(
            name="Marie Curie",
            entity_type=EntityType.PERSON,
            description="Polish-French physicist",
            source="test.md",
        )
        assert entity.embedding_text == "Marie Curie: Polish-French physicist"


class TestEntityType:
    """Tests for EntityType enum and from_llm_output factory."""

    def test_known_type_person_returns_enum(self) -> None:
        assert EntityType.from_llm_output("PERSON") == EntityType.PERSON

    def test_lowercase_input_is_normalized(self) -> None:
        assert EntityType.from_llm_output("person") == EntityType.PERSON

    def test_unknown_type_defaults_to_concept(self) -> None:
        assert EntityType.from_llm_output("MYTHICAL") == EntityType.CONCEPT

    def test_mixed_case_organization_is_parsed(self) -> None:
        assert EntityType.from_llm_output("Organization") == EntityType.ORGANIZATION

    def test_empty_string_defaults_to_concept(self) -> None:
        assert EntityType.from_llm_output("") == EntityType.CONCEPT


class TestDeduplication:
    """Tests for entity and relationship deduplication."""

    def test_deduplicate_entities_by_normalized_name(self) -> None:
        entities = [
            Entity(
                name="Marie Curie",
                entity_type=EntityType.PERSON,
                description="Short",
                source="a",
            ),
            Entity(
                name="marie curie",
                entity_type=EntityType.PERSON,
                description="Longer description",
                source="b",
            ),
        ]
        result = deduplicate_entities(entities)
        assert len(result) == 1
        assert result[0].description == "Longer description"

    def test_deduplicate_relationships(self) -> None:
        rels = [
            Relationship(source="A", target="B", relationship_type="KNOWS", description="v1"),
            Relationship(
                source="a",
                target="b",
                relationship_type="KNOWS",
                description="longer v2",
            ),
        ]
        result = deduplicate_relationships(rels)
        assert len(result) == 1
        assert result[0].description == "longer v2"


class TestValidateConfig:
    """Tests for validate_config function."""

    def _make_config(
        self,
        llm_provider: str = "anthropic",
        anthropic_key: str = "key-abc",
        gemini_llm_key: str = "",
        embedding_provider: str = "openai",
        openai_key: str = "key-xyz",
        gemini_embed_key: str = "",
    ) -> KgraphConfig:
        return KgraphConfig(
            neo4j=Neo4jConfig(),
            llm=LLMConfig(
                provider=llm_provider,  # type: ignore[arg-type]
                anthropic_api_key=anthropic_key,
                gemini_api_key=gemini_llm_key,
            ),
            embedding=EmbeddingConfig(
                provider=embedding_provider,  # type: ignore[arg-type]
                openai_api_key=openai_key,
                gemini_api_key=gemini_embed_key,
            ),
        )

    def test_valid_anthropic_openai_config_passes(self) -> None:
        config = self._make_config()
        validate_config(config)  # should not raise

    def test_missing_anthropic_key_raises_config_error(self) -> None:
        config = self._make_config(llm_provider="anthropic", anthropic_key="")
        with pytest.raises(ConfigError, match="anthropic_api_key"):
            validate_config(config)

    def test_missing_gemini_llm_key_raises_config_error(self) -> None:
        config = self._make_config(llm_provider="gemini", gemini_llm_key="", anthropic_key="")
        with pytest.raises(ConfigError, match="gemini_api_key"):
            validate_config(config)

    def test_missing_openai_embedding_key_raises_config_error(self) -> None:
        config = self._make_config(embedding_provider="openai", openai_key="")
        with pytest.raises(ConfigError, match="openai_api_key"):
            validate_config(config)

    def test_missing_gemini_embedding_key_raises_config_error(self) -> None:
        config = self._make_config(embedding_provider="gemini", openai_key="", gemini_embed_key="")
        with pytest.raises(ConfigError, match="gemini_api_key"):
            validate_config(config)

    def test_local_embedding_provider_needs_no_api_key(self) -> None:
        config = self._make_config(embedding_provider="local", openai_key="")
        validate_config(config)  # should not raise
