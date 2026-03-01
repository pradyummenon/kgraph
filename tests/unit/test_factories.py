"""Unit tests for application factory functions."""

import pytest

from kgraph.application.factories import create_embedder, create_extractor, create_graph
from kgraph.config import EmbeddingConfig, KgraphConfig, LLMConfig, Neo4jConfig
from kgraph.domain.errors import ConfigError
from kgraph.infrastructure.embedder import GeminiEmbedder, LocalEmbedder, OpenAIEmbedder
from kgraph.infrastructure.extractor import ClaudeExtractor, GeminiExtractor
from kgraph.infrastructure.graph import Neo4jGraph


class TestCreateExtractor:
    def test_anthropic_returns_claude_extractor(self) -> None:
        config = KgraphConfig(llm=LLMConfig(provider="anthropic", anthropic_api_key="key"))
        result = create_extractor(config)
        assert isinstance(result, ClaudeExtractor)

    def test_gemini_returns_gemini_extractor(self) -> None:
        config = KgraphConfig(llm=LLMConfig(provider="gemini", gemini_api_key="key"))
        result = create_extractor(config)
        assert isinstance(result, GeminiExtractor)

    def test_unknown_provider_raises_config_error(self) -> None:
        config = KgraphConfig(
            llm=LLMConfig(provider="anthropic", anthropic_api_key="key", model="m")
        )
        # Bypass the Literal type check by patching provider value
        object.__setattr__(config.llm, "__class__", config.llm.__class__)
        bad_config = KgraphConfig.__new__(KgraphConfig)
        object.__setattr__(bad_config, "llm", config.llm)
        object.__setattr__(bad_config, "embedding", config.embedding)
        object.__setattr__(bad_config, "neo4j", config.neo4j)
        object.__setattr__(bad_config, "config_version", 1)

        import dataclasses

        bad_llm = dataclasses.replace(config.llm)
        object.__setattr__(bad_llm, "provider", "unknown")
        object.__setattr__(bad_config, "llm", bad_llm)

        with pytest.raises(ConfigError, match="Unknown LLM provider"):
            create_extractor(bad_config)


class TestCreateEmbedder:
    def test_openai_returns_openai_embedder(self) -> None:
        config = KgraphConfig(embedding=EmbeddingConfig(provider="openai", openai_api_key="key"))
        result = create_embedder(config)
        assert isinstance(result, OpenAIEmbedder)

    def test_gemini_returns_gemini_embedder(self) -> None:
        config = KgraphConfig(embedding=EmbeddingConfig(provider="gemini", gemini_api_key="key"))
        result = create_embedder(config)
        assert isinstance(result, GeminiEmbedder)

    def test_local_returns_local_embedder(self) -> None:
        pytest.importorskip("sentence_transformers")
        config = KgraphConfig(embedding=EmbeddingConfig(provider="local"))
        result = create_embedder(config)
        assert isinstance(result, LocalEmbedder)

    def test_unknown_provider_raises_config_error(self) -> None:
        import dataclasses

        config = KgraphConfig(embedding=EmbeddingConfig(provider="openai", openai_api_key="key"))
        bad_embedding = dataclasses.replace(config.embedding)
        object.__setattr__(bad_embedding, "provider", "unknown")
        bad_config = dataclasses.replace(config, embedding=bad_embedding)

        with pytest.raises(ConfigError, match="Unknown embedding provider"):
            create_embedder(bad_config)


class TestCreateGraph:
    def test_creates_neo4j_graph(self) -> None:
        config = KgraphConfig(neo4j=Neo4jConfig(uri="bolt://localhost:7687"))
        result = create_graph(config)
        assert isinstance(result, Neo4jGraph)
