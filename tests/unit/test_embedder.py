"""Unit tests for OpenAIEmbedder, GeminiEmbedder, and LocalEmbedder."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kgraph.domain.errors import EmbeddingError, RateLimitError


class TestOpenAIEmbedder:
    async def test_returns_correct_number_of_vectors(self) -> None:
        with patch("kgraph.infrastructure.embedder.openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client

            embedding_data = [MagicMock(embedding=[0.1] * 1536) for _ in range(3)]
            mock_response = MagicMock()
            mock_response.data = embedding_data
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            from kgraph.infrastructure.embedder import OpenAIEmbedder

            embedder = OpenAIEmbedder(api_key="test-key")
            results = await embedder.embed(["text one", "text two", "text three"])

        assert len(results) == 3

    async def test_vector_has_correct_dimensions(self) -> None:
        with patch("kgraph.infrastructure.embedder.openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client

            embedding_data = [MagicMock(embedding=[0.5] * 1536)]
            mock_response = MagicMock()
            mock_response.data = embedding_data
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            from kgraph.infrastructure.embedder import OpenAIEmbedder

            embedder = OpenAIEmbedder(api_key="test-key")
            results = await embedder.embed(["hello"])

        assert len(results[0]) == 1536

    async def test_empty_input_returns_empty_output_without_api_call(self) -> None:
        with patch("kgraph.infrastructure.embedder.openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client

            from kgraph.infrastructure.embedder import OpenAIEmbedder

            embedder = OpenAIEmbedder(api_key="test-key")
            results = await embedder.embed([])

        assert results == []
        mock_client.embeddings.create.assert_not_called()

    async def test_api_failure_raises_embedding_error(self) -> None:
        import openai

        with patch("kgraph.infrastructure.embedder.openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.embeddings.create = AsyncMock(
                side_effect=openai.APIError(
                    message="server error",
                    request=MagicMock(),
                    body=None,
                )
            )

            from kgraph.infrastructure.embedder import OpenAIEmbedder

            embedder = OpenAIEmbedder(api_key="test-key")
            with pytest.raises(EmbeddingError, match="OpenAI API error"):
                await embedder.embed(["hello"])

    async def test_rate_limit_raises_rate_limit_error(self) -> None:
        import openai

        with patch("kgraph.infrastructure.embedder.openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.embeddings.create = AsyncMock(
                side_effect=openai.RateLimitError(
                    message="rate limited",
                    response=MagicMock(headers={}, status_code=429),
                    body=None,
                )
            )

            from kgraph.infrastructure.embedder import OpenAIEmbedder

            embedder = OpenAIEmbedder(api_key="test-key")
            with pytest.raises(RateLimitError):
                await embedder.embed(["hello"])

    def test_dimensions_property_returns_configured_dim(self) -> None:
        with patch("kgraph.infrastructure.embedder.openai.AsyncOpenAI"):
            from kgraph.infrastructure.embedder import OpenAIEmbedder

            embedder = OpenAIEmbedder(api_key="test-key", dim=512)
            assert embedder.dimensions == 512


class TestGeminiEmbedder:
    def _make_embed_response(self, vectors: list[list[float]]) -> MagicMock:
        mock_result = MagicMock()
        mock_result.embeddings = [MagicMock(values=v) for v in vectors]
        return mock_result

    async def test_returns_correct_number_of_vectors(self) -> None:
        with patch("kgraph.infrastructure.embedder.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            response = self._make_embed_response([[0.1] * 768, [0.2] * 768])
            mock_client.aio.models.embed_content = AsyncMock(return_value=response)

            from kgraph.infrastructure.embedder import GeminiEmbedder

            embedder = GeminiEmbedder(api_key="test-key")
            results = await embedder.embed(["text one", "text two"])

        assert len(results) == 2

    async def test_vector_has_correct_dimensions(self) -> None:
        with patch("kgraph.infrastructure.embedder.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            response = self._make_embed_response([[0.5] * 768])
            mock_client.aio.models.embed_content = AsyncMock(return_value=response)

            from kgraph.infrastructure.embedder import GeminiEmbedder

            embedder = GeminiEmbedder(api_key="test-key")
            results = await embedder.embed(["hello"])

        assert len(results[0]) == 768

    async def test_empty_input_returns_empty_output_without_api_call(self) -> None:
        with patch("kgraph.infrastructure.embedder.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from kgraph.infrastructure.embedder import GeminiEmbedder

            embedder = GeminiEmbedder(api_key="test-key")
            results = await embedder.embed([])

        assert results == []
        mock_client.aio.models.embed_content.assert_not_called()

    async def test_api_failure_raises_embedding_error(self) -> None:
        with patch("kgraph.infrastructure.embedder.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.aio.models.embed_content = AsyncMock(side_effect=Exception("server error"))

            from kgraph.infrastructure.embedder import GeminiEmbedder

            embedder = GeminiEmbedder(api_key="test-key")
            with pytest.raises(EmbeddingError, match="Gemini embedding API error"):
                await embedder.embed(["hello"])

    async def test_rate_limit_raises_rate_limit_error(self) -> None:
        with patch("kgraph.infrastructure.embedder.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.aio.models.embed_content = AsyncMock(
                side_effect=Exception("429 quota exceeded")
            )

            from kgraph.infrastructure.embedder import GeminiEmbedder

            embedder = GeminiEmbedder(api_key="test-key")
            with pytest.raises(RateLimitError):
                await embedder.embed(["hello"])

    def test_dimensions_property_returns_configured_dim(self) -> None:
        with patch("kgraph.infrastructure.embedder.genai.Client"):
            from kgraph.infrastructure.embedder import GeminiEmbedder

            embedder = GeminiEmbedder(api_key="test-key", dim=512)
            assert embedder.dimensions == 512


class TestLocalEmbedder:
    def _make_embedder_with_mock_model(self, dimensions: int = 384) -> object:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = dimensions
        fake_st_module = MagicMock()
        fake_st_module.SentenceTransformer.return_value = mock_model
        with patch.dict("sys.modules", {"sentence_transformers": fake_st_module}):
            from kgraph.infrastructure.embedder import LocalEmbedder

            return LocalEmbedder()

    async def test_uses_asyncio_to_thread_for_encoding(self) -> None:
        embedder = self._make_embedder_with_mock_model()

        fake_vector = MagicMock()
        fake_vector.tolist.return_value = [0.1] * 384

        with patch(
            "kgraph.infrastructure.embedder.asyncio.to_thread",
            new_callable=AsyncMock,
        ) as mock_to_thread:
            mock_to_thread.return_value = [fake_vector]
            results = await embedder.embed(["hello world"])

        mock_to_thread.assert_called_once()
        assert len(results) == 1

    async def test_empty_input_returns_empty_output(self) -> None:
        embedder = self._make_embedder_with_mock_model()
        results = await embedder.embed([])
        assert results == []

    async def test_encoding_failure_raises_embedding_error(self) -> None:
        embedder = self._make_embedder_with_mock_model()

        with patch(
            "kgraph.infrastructure.embedder.asyncio.to_thread",
            new_callable=AsyncMock,
        ) as mock_to_thread:
            mock_to_thread.side_effect = RuntimeError("CUDA out of memory")
            with pytest.raises(EmbeddingError, match="Local embedding failed"):
                await embedder.embed(["hello"])
