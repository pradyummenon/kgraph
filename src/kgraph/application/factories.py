"""Factory functions for constructing infrastructure adapters from config.

Each factory reads from KgraphConfig and returns a concrete adapter that
satisfies the corresponding domain protocol. Callers receive the protocol
interface — they never depend on the concrete type.
"""

from __future__ import annotations

from kgraph.config import KgraphConfig
from kgraph.domain.errors import ConfigError
from kgraph.domain.services import EmbeddingGenerator, EntityExtractor, GraphRepository
from kgraph.infrastructure.embedder import GeminiEmbedder, LocalEmbedder, OpenAIEmbedder
from kgraph.infrastructure.extractor import ClaudeExtractor, GeminiExtractor
from kgraph.infrastructure.graph import Neo4jGraph


def create_extractor(config: KgraphConfig) -> EntityExtractor:
    """Create an entity extractor based on the configured LLM provider."""
    if config.llm.provider == "anthropic":
        return ClaudeExtractor(
            api_key=config.llm.anthropic_api_key,
            model=config.llm.model,
        )
    if config.llm.provider == "gemini":
        return GeminiExtractor(
            api_key=config.llm.gemini_api_key,
            model=config.llm.model,
        )
    raise ConfigError(f"Unknown LLM provider: {config.llm.provider}")


def create_embedder(config: KgraphConfig) -> EmbeddingGenerator:
    """Create an embedding generator based on the configured provider."""
    if config.embedding.provider == "openai":
        return OpenAIEmbedder(
            api_key=config.embedding.openai_api_key,
            model=config.embedding.openai_model,
            dim=config.embedding.dimensions,
        )
    if config.embedding.provider == "gemini":
        return GeminiEmbedder(
            api_key=config.embedding.gemini_api_key,
            model=config.embedding.gemini_model,
            dim=config.embedding.dimensions,
        )
    if config.embedding.provider == "local":
        return LocalEmbedder(model_name=config.embedding.local_model)
    raise ConfigError(f"Unknown embedding provider: {config.embedding.provider}")


def create_graph(config: KgraphConfig) -> GraphRepository:
    """Create a graph repository for the configured Neo4j instance."""
    return Neo4jGraph(
        uri=config.neo4j.uri,
        username=config.neo4j.username,
        password=config.neo4j.password,
    )
