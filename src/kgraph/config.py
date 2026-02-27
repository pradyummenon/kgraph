"""Configuration management for kgraph.

Stores config in ~/.kgraph/config.toml with Neo4j connection details,
API keys, and embedding preferences.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

CONFIG_DIR = Path.home() / ".kgraph"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j connection configuration."""

    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "kgraph-password"


@dataclass(frozen=True)
class LLMConfig:
    """LLM configuration for extraction and answer generation."""

    provider: str = "anthropic"  # "anthropic" or "gemini"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding configuration."""

    provider: str = "openai"  # "openai", "gemini", or "local"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    openai_model: str = "text-embedding-3-small"
    gemini_model: str = "gemini-embedding-001"
    local_model: str = "BAAI/bge-base-en-v1.5"
    dimensions: int = 1536  # 1536 for openai, 768 for local/gemini


@dataclass(frozen=True)
class KgraphConfig:
    """Root configuration object."""

    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)


def load_config() -> KgraphConfig:
    """Load configuration from ~/.kgraph/config.toml.

    Returns:
        KgraphConfig with values from file, or defaults if file doesn't exist.

    Raises:
        FileNotFoundError: If config file doesn't exist (run `kgraph init` first).
    """
    if not CONFIG_FILE.exists():
        msg = (
            f"Config file not found at {CONFIG_FILE}. "
            "Run `kgraph init` to set up your configuration."
        )
        raise FileNotFoundError(msg)

    with CONFIG_FILE.open("rb") as f:
        data: dict[str, Any] = tomllib.load(f)

    return KgraphConfig(
        neo4j=Neo4jConfig(**data.get("neo4j", {})),
        llm=LLMConfig(**data.get("llm", {})),
        embedding=EmbeddingConfig(**data.get("embedding", {})),
    )


def save_config(config: KgraphConfig) -> None:
    """Save configuration to ~/.kgraph/config.toml."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "neo4j": {
            "uri": config.neo4j.uri,
            "username": config.neo4j.username,
            "password": config.neo4j.password,
        },
        "llm": {
            "provider": config.llm.provider,
            "anthropic_api_key": config.llm.anthropic_api_key,
            "gemini_api_key": config.llm.gemini_api_key,
            "model": config.llm.model,
            "max_tokens": config.llm.max_tokens,
        },
        "embedding": {
            "provider": config.embedding.provider,
            "openai_api_key": config.embedding.openai_api_key,
            "gemini_api_key": config.embedding.gemini_api_key,
            "openai_model": config.embedding.openai_model,
            "gemini_model": config.embedding.gemini_model,
            "local_model": config.embedding.local_model,
            "dimensions": config.embedding.dimensions,
        },
    }

    with CONFIG_FILE.open("wb") as f:
        tomli_w.dump(data, f)
