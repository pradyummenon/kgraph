"""Embedding generation for kgraph.

Supports OpenAI embeddings (default), Google Gemini, and local
sentence-transformers. Provider is configurable via ~/.kgraph/config.toml.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import openai
from google import genai
from google.genai import types as genai_types

if TYPE_CHECKING:
    pass


class OpenAIEmbedder:
    """Generate embeddings using OpenAI's API."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dim: int = 1536,
    ) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dim

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [tuple(item.embedding) for item in response.data]


class GeminiEmbedder:
    """Generate embeddings using Google Gemini's API."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-004",
        dim: int = 768,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dimensions = dim

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        # Gemini limits to 100 texts per batch
        all_embeddings: list[tuple[float, ...]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = await self._client.aio.models.embed_content(
                model=self._model,
                contents=batch,
                config=genai_types.EmbedContentConfig(
                    output_dimensionality=self._dimensions,
                ),
            )
            all_embeddings.extend(tuple(e.values) for e in result.embeddings)
        return all_embeddings


class LocalEmbedder:
    """Generate embeddings using local sentence-transformers model.

    Requires the `local` optional dependency:
        pip install kgraph[local]
    """

    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            msg = (
                "Local embeddings require sentence-transformers. "
                "Install with: pip install kgraph[local]"
            )
            raise ImportError(msg) from e

        self._model = SentenceTransformer(model_name)
        self._dimensions = self._model.get_sentence_embedding_dimension()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Generate embeddings locally.

        Note: sentence-transformers is synchronous, but we wrap it
        in an async interface for consistency.
        """
        if not texts:
            return []

        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return [tuple(embedding.tolist()) for embedding in embeddings]
