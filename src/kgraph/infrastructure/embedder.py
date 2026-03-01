"""Embedding generation for kgraph.

Supports OpenAI embeddings (default), Google Gemini, and local
sentence-transformers. Provider is configurable via ~/.kgraph/config.toml.
"""

from __future__ import annotations

import asyncio

import openai
from google import genai
from google.genai import types as genai_types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from kgraph.domain.errors import EmbeddingError, RateLimitError
from kgraph.infrastructure.logging import get_logger

_log = get_logger(__name__)


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

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: On unrecoverable API failures.
            RateLimitError: On rate limit responses (retried automatically).
        """
        if not texts:
            return []

        _log.debug("embedder.openai.start", text_count=len(texts), model=self._model)
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
        except openai.RateLimitError as exc:
            _log.warning("embedder.openai.rate_limit")
            raise RateLimitError("OpenAI rate limit exceeded") from exc
        except openai.APIError as exc:
            raise EmbeddingError(f"OpenAI API error: {exc}") from exc

        _log.debug("embedder.openai.done", text_count=len(texts))
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

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: On unrecoverable API failures.
            RateLimitError: On rate limit responses (retried automatically).
        """
        if not texts:
            return []

        _log.debug("embedder.gemini.start", text_count=len(texts), model=self._model)
        # Gemini limits to 100 texts per batch
        all_embeddings: list[tuple[float, ...]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                result = await self._client.aio.models.embed_content(
                    model=self._model,
                    contents=batch,
                    config=genai_types.EmbedContentConfig(
                        output_dimensionality=self._dimensions,
                    ),
                )
            except Exception as exc:
                error_str = str(exc).lower()
                if "rate" in error_str or "quota" in error_str or "429" in error_str:
                    _log.warning("embedder.gemini.rate_limit")
                    raise RateLimitError("Gemini rate limit exceeded") from exc
                raise EmbeddingError(f"Gemini embedding API error: {exc}") from exc
            all_embeddings.extend(tuple(e.values) for e in result.embeddings)

        _log.debug("embedder.gemini.done", text_count=len(texts))
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

        Raises:
            EmbeddingError: If the model fails to encode the texts.
        """
        if not texts:
            return []

        _log.debug("embedder.local.start", text_count=len(texts))
        try:
            embeddings = await asyncio.to_thread(
                self._model.encode, texts, normalize_embeddings=True
            )
        except Exception as exc:
            raise EmbeddingError(f"Local embedding failed: {exc}") from exc

        _log.debug("embedder.local.done", text_count=len(texts))
        return [tuple(embedding.tolist()) for embedding in embeddings]
