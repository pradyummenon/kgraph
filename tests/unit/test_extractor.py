"""Unit tests for ClaudeExtractor and GeminiExtractor."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kgraph.domain.errors import ExtractionError, RateLimitError
from kgraph.domain.models import Chunk, EntityType


def _make_chunk(text: str = "Marie Curie worked at the University of Paris.") -> Chunk:
    return Chunk(text=text, source_file="test.md", chunk_index=0, total_chunks=1)


def _make_tool_use_block(entities: list[dict], relationships: list[dict]) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = "extract_knowledge"
    block.input = {"entities": entities, "relationships": relationships}
    return block


class TestClaudeExtractor:
    async def test_parses_tool_use_response_into_entities_and_relationships(self) -> None:
        with patch("kgraph.infrastructure.extractor.anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client

            tool_block = _make_tool_use_block(
                entities=[
                    {
                        "name": "Marie Curie",
                        "entity_type": "PERSON",
                        "description": "Polish-French physicist",
                    }
                ],
                relationships=[
                    {
                        "source": "Marie Curie",
                        "target": "University of Paris",
                        "relationship_type": "WORKS_AT",
                        "description": "worked there",
                    }
                ],
            )
            mock_response = MagicMock()
            mock_response.content = [tool_block]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            from kgraph.infrastructure.extractor import ClaudeExtractor

            extractor = ClaudeExtractor(api_key="test-key")
            result = await extractor.extract(_make_chunk())

        assert len(result.entities) == 1
        assert result.entities[0].name == "Marie Curie"
        assert result.entities[0].entity_type == EntityType.PERSON
        assert len(result.relationships) == 1
        assert result.relationships[0].relationship_type == "WORKS_AT"

    async def test_api_failure_raises_extraction_error(self) -> None:
        import anthropic

        with patch("kgraph.infrastructure.extractor.anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create = AsyncMock(
                side_effect=anthropic.APIError(
                    message="server error",
                    request=MagicMock(),
                    body=None,
                )
            )

            from kgraph.infrastructure.extractor import ClaudeExtractor

            extractor = ClaudeExtractor(api_key="test-key")
            with pytest.raises(ExtractionError, match="Anthropic API error"):
                await extractor.extract(_make_chunk())

    async def test_rate_limit_raises_rate_limit_error(self) -> None:
        import anthropic

        with patch("kgraph.infrastructure.extractor.anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create = AsyncMock(
                side_effect=anthropic.RateLimitError(
                    message="rate limited",
                    response=MagicMock(headers={}, status_code=429),
                    body=None,
                )
            )

            from kgraph.infrastructure.extractor import ClaudeExtractor

            extractor = ClaudeExtractor(api_key="test-key")
            with pytest.raises(RateLimitError):
                await extractor.extract(_make_chunk())

    async def test_prompt_wraps_chunk_text_in_document_tags(self) -> None:
        with patch("kgraph.infrastructure.extractor.anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client

            tool_block = _make_tool_use_block(entities=[], relationships=[])
            mock_response = MagicMock()
            mock_response.content = [tool_block]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            from kgraph.infrastructure.extractor import ClaudeExtractor

            extractor = ClaudeExtractor(api_key="test-key")
            chunk = _make_chunk(text="some content")
            await extractor.extract(chunk)

            call_kwargs = mock_client.messages.create.call_args
            messages = call_kwargs.kwargs["messages"]
            user_content = messages[0]["content"]
            assert "<document>" in user_content
            assert "some content" in user_content

    async def test_empty_extraction_returns_empty_result(self) -> None:
        with patch("kgraph.infrastructure.extractor.anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value = mock_client

            tool_block = _make_tool_use_block(entities=[], relationships=[])
            mock_response = MagicMock()
            mock_response.content = [tool_block]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            from kgraph.infrastructure.extractor import ClaudeExtractor

            extractor = ClaudeExtractor(api_key="test-key")
            result = await extractor.extract(_make_chunk())

        assert result.entities == []
        assert result.relationships == []


class TestGeminiExtractor:
    def _make_json_response(self, entities: list[dict], relationships: list[dict]) -> MagicMock:
        mock_response = MagicMock()
        mock_response.text = json.dumps({"entities": entities, "relationships": relationships})
        return mock_response

    async def test_parses_json_response_into_entities_and_relationships(self) -> None:
        with patch("kgraph.infrastructure.extractor.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            json_response = self._make_json_response(
                entities=[
                    {
                        "name": "Python",
                        "entity_type": "TECHNOLOGY",
                        "description": "Programming language",
                    }
                ],
                relationships=[],
            )
            mock_client.aio.models.generate_content = AsyncMock(return_value=json_response)

            from kgraph.infrastructure.extractor import GeminiExtractor

            extractor = GeminiExtractor(api_key="test-key")
            result = await extractor.extract(_make_chunk())

        assert len(result.entities) == 1
        assert result.entities[0].name == "Python"
        assert result.entities[0].entity_type == EntityType.TECHNOLOGY

    async def test_api_failure_raises_extraction_error(self) -> None:
        with patch("kgraph.infrastructure.extractor.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(
                side_effect=Exception("server error")
            )

            from kgraph.infrastructure.extractor import GeminiExtractor

            extractor = GeminiExtractor(api_key="test-key")
            with pytest.raises(ExtractionError, match="Gemini API error"):
                await extractor.extract(_make_chunk())

    async def test_rate_limit_exception_raises_rate_limit_error(self) -> None:
        with patch("kgraph.infrastructure.extractor.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(
                side_effect=Exception("429 rate limit exceeded")
            )

            from kgraph.infrastructure.extractor import GeminiExtractor

            extractor = GeminiExtractor(api_key="test-key")
            with pytest.raises(RateLimitError):
                await extractor.extract(_make_chunk())

    async def test_prompt_wraps_chunk_text_in_document_tags(self) -> None:
        with patch("kgraph.infrastructure.extractor.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            json_response = self._make_json_response(entities=[], relationships=[])
            mock_client.aio.models.generate_content = AsyncMock(return_value=json_response)

            from kgraph.infrastructure.extractor import GeminiExtractor

            extractor = GeminiExtractor(api_key="test-key")
            chunk = _make_chunk(text="some content")
            await extractor.extract(chunk)

            call_kwargs = mock_client.aio.models.generate_content.call_args
            contents = call_kwargs.kwargs["contents"]
            assert "<document>" in contents
            assert "some content" in contents

    async def test_empty_extraction_returns_empty_result(self) -> None:
        with patch("kgraph.infrastructure.extractor.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            json_response = self._make_json_response(entities=[], relationships=[])
            mock_client.aio.models.generate_content = AsyncMock(return_value=json_response)

            from kgraph.infrastructure.extractor import GeminiExtractor

            extractor = GeminiExtractor(api_key="test-key")
            result = await extractor.extract(_make_chunk())

        assert result.entities == []
        assert result.relationships == []

    async def test_malformed_json_returns_empty_result(self) -> None:
        with patch("kgraph.infrastructure.extractor.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            bad_response = MagicMock()
            bad_response.text = "this is not json"
            mock_client.aio.models.generate_content = AsyncMock(return_value=bad_response)

            from kgraph.infrastructure.extractor import GeminiExtractor

            extractor = GeminiExtractor(api_key="test-key")
            result = await extractor.extract(_make_chunk())

        assert result.entities == []
        assert result.relationships == []

    async def test_source_reference_is_attached_to_entities(self) -> None:
        with patch("kgraph.infrastructure.extractor.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            json_response = self._make_json_response(
                entities=[
                    {
                        "name": "Django",
                        "entity_type": "TECHNOLOGY",
                        "description": "Web framework",
                    }
                ],
                relationships=[],
            )
            mock_client.aio.models.generate_content = AsyncMock(return_value=json_response)

            from kgraph.infrastructure.extractor import GeminiExtractor

            extractor = GeminiExtractor(api_key="test-key")
            chunk = Chunk(text="text", source_file="docs.md", chunk_index=2, total_chunks=5)
            result = await extractor.extract(chunk)

        assert result.entities[0].source == "docs.md [chunk 3/5]"
