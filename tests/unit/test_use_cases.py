"""Unit tests for IngestUseCase, QueryUseCase, and StatsUseCase."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from rich.console import Console

from kgraph.application.use_cases import IngestUseCase, QueryUseCase, StatsUseCase
from kgraph.config import KgraphConfig, LLMConfig
from kgraph.domain.models import Entity, EntityType, ExtractionResult, RetrievalResult


def _make_console() -> tuple[Console, StringIO]:
    buf = StringIO()
    return Console(file=buf, force_terminal=False), buf


def _make_entity(name: str = "Python") -> Entity:
    return Entity(
        name=name,
        entity_type=EntityType.TECHNOLOGY,
        description="A programming language",
        source="test.md [chunk 1/1]",
    )


def _make_extraction_result(entities: list[Entity] | None = None) -> ExtractionResult:
    from kgraph.domain.models import Chunk

    chunk = Chunk(text="test", source_file="test.md", chunk_index=0, total_chunks=1)
    return ExtractionResult(
        entities=entities or [_make_entity()],
        relationships=[],
        source_chunk=chunk,
    )


class TestIngestUseCase:
    async def test_writes_entities_and_relationships_to_graph(
        self, mock_graph: AsyncMock, mock_extractor: AsyncMock, mock_embedder: AsyncMock
    ) -> None:
        mock_extractor.extract = AsyncMock(return_value=_make_extraction_result())
        mock_embedder.embed = AsyncMock(return_value=[(0.1,) * 1536])
        mock_graph.ingest_entities = AsyncMock(return_value=1)
        mock_graph.ingest_relationships = AsyncMock(return_value=0)

        console, _buf = _make_console()
        use_case = IngestUseCase(
            extractor=mock_extractor,
            embedder=mock_embedder,
            graph=mock_graph,
            console=console,
        )

        with (
            patch("kgraph.application.use_cases.read_documents") as mock_read,
            patch("kgraph.application.use_cases.chunk_text") as mock_chunk,
        ):
            from kgraph.domain.models import Chunk

            mock_read.return_value = [("test.md", "some text")]
            mock_chunk.return_value = [
                Chunk(text="some text", source_file="test.md", chunk_index=0, total_chunks=1)
            ]
            await use_case.execute(Path("/fake/path"))

        mock_graph.ingest_entities.assert_called_once()
        mock_graph.ingest_relationships.assert_called_once()

    async def test_displays_ingestion_summary(
        self, mock_graph: AsyncMock, mock_extractor: AsyncMock, mock_embedder: AsyncMock
    ) -> None:
        mock_extractor.extract = AsyncMock(return_value=_make_extraction_result())
        mock_embedder.embed = AsyncMock(return_value=[(0.1,) * 1536])
        mock_graph.ingest_entities = AsyncMock(return_value=1)
        mock_graph.ingest_relationships = AsyncMock(return_value=0)

        console, buf = _make_console()
        use_case = IngestUseCase(
            extractor=mock_extractor,
            embedder=mock_embedder,
            graph=mock_graph,
            console=console,
        )

        with (
            patch("kgraph.application.use_cases.read_documents") as mock_read,
            patch("kgraph.application.use_cases.chunk_text") as mock_chunk,
        ):
            from kgraph.domain.models import Chunk

            mock_read.return_value = [("test.md", "some text")]
            mock_chunk.return_value = [
                Chunk(text="some text", source_file="test.md", chunk_index=0, total_chunks=1)
            ]
            await use_case.execute(Path("/fake/path"))

        output = buf.getvalue()
        assert "Ingestion Summary" in output

    async def test_calls_embedder_with_entity_texts(
        self, mock_graph: AsyncMock, mock_extractor: AsyncMock, mock_embedder: AsyncMock
    ) -> None:
        entity = _make_entity("Django")
        mock_extractor.extract = AsyncMock(return_value=_make_extraction_result([entity]))
        mock_embedder.embed = AsyncMock(return_value=[(0.2,) * 1536])
        mock_graph.ingest_entities = AsyncMock(return_value=1)
        mock_graph.ingest_relationships = AsyncMock(return_value=0)

        console, _ = _make_console()
        use_case = IngestUseCase(
            extractor=mock_extractor,
            embedder=mock_embedder,
            graph=mock_graph,
            console=console,
        )

        with (
            patch("kgraph.application.use_cases.read_documents") as mock_read,
            patch("kgraph.application.use_cases.chunk_text") as mock_chunk,
        ):
            from kgraph.domain.models import Chunk

            mock_read.return_value = [("test.md", "text")]
            mock_chunk.return_value = [
                Chunk(text="text", source_file="test.md", chunk_index=0, total_chunks=1)
            ]
            await use_case.execute(Path("/fake/path"))

        mock_embedder.embed.assert_called_once()
        texts_passed = mock_embedder.embed.call_args[0][0]
        assert any("Django" in t for t in texts_passed)


class TestQueryUseCase:
    def _make_retrieval_result(self) -> RetrievalResult:
        return RetrievalResult(
            entities=[_make_entity()],
            relationships=[],
            context_text="Python (TECHNOLOGY) — A programming language",
        )

    def _make_anthropic_config(self) -> KgraphConfig:
        return KgraphConfig(llm=LLMConfig(provider="anthropic", anthropic_api_key="key"))

    def _make_gemini_config(self) -> KgraphConfig:
        return KgraphConfig(llm=LLMConfig(provider="gemini", gemini_api_key="key"))

    async def test_displays_answer_panel(
        self, mock_graph: AsyncMock, mock_embedder: AsyncMock
    ) -> None:
        mock_embedder.embed = AsyncMock(return_value=[(0.1,) * 1536])
        retrieval = self._make_retrieval_result()

        console, buf = _make_console()
        use_case = QueryUseCase(
            embedder=mock_embedder,
            graph=mock_graph,
            config=self._make_anthropic_config(),
            console=console,
        )

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Python is a versatile language.")]

        with patch("kgraph.application.use_cases.HybridRetriever") as mock_retriever_cls:
            mock_retriever = AsyncMock()
            mock_retriever.retrieve = AsyncMock(return_value=retrieval)
            mock_retriever_cls.return_value = mock_retriever

            with patch("kgraph.application.use_cases.anthropic.AsyncAnthropic") as mock_cls:
                mock_client = AsyncMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create = AsyncMock(return_value=mock_response)
                await use_case.execute(question="What is Python?")

        output = buf.getvalue()
        assert "Answer" in output

    async def test_uses_gemini_when_configured(
        self, mock_graph: AsyncMock, mock_embedder: AsyncMock
    ) -> None:
        mock_embedder.embed = AsyncMock(return_value=[(0.1,) * 768])
        retrieval = self._make_retrieval_result()

        console, buf = _make_console()
        use_case = QueryUseCase(
            embedder=mock_embedder,
            graph=mock_graph,
            config=self._make_gemini_config(),
            console=console,
        )

        mock_response = MagicMock()
        mock_response.text = "Python is a language."

        with patch("kgraph.application.use_cases.HybridRetriever") as mock_retriever_cls:
            mock_retriever = AsyncMock()
            mock_retriever.retrieve = AsyncMock(return_value=retrieval)
            mock_retriever_cls.return_value = mock_retriever

            with patch("google.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client_cls.return_value = mock_client
                mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
                await use_case.execute(question="What is Python?")

        output = buf.getvalue()
        assert "Answer" in output

    async def test_show_raw_prints_context_panel(
        self, mock_graph: AsyncMock, mock_embedder: AsyncMock
    ) -> None:
        mock_embedder.embed = AsyncMock(return_value=[(0.1,) * 1536])
        retrieval = self._make_retrieval_result()

        console, buf = _make_console()
        use_case = QueryUseCase(
            embedder=mock_embedder,
            graph=mock_graph,
            config=self._make_anthropic_config(),
            console=console,
        )

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="An answer.")]

        with patch("kgraph.application.use_cases.HybridRetriever") as mock_retriever_cls:
            mock_retriever = AsyncMock()
            mock_retriever.retrieve = AsyncMock(return_value=retrieval)
            mock_retriever_cls.return_value = mock_retriever

            with patch("kgraph.application.use_cases.anthropic.AsyncAnthropic") as mock_cls:
                mock_client = AsyncMock()
                mock_cls.return_value = mock_client
                mock_client.messages.create = AsyncMock(return_value=mock_response)
                await use_case.execute(question="What is Python?", show_raw=True)

        output = buf.getvalue()
        assert "Raw Context" in output


class TestStatsUseCase:
    async def test_displays_statistics_table(self, mock_graph: AsyncMock) -> None:
        mock_graph.get_stats = AsyncMock(return_value={"nodes": 42, "relationships": 100})

        console, buf = _make_console()
        use_case = StatsUseCase(graph=mock_graph, console=console)
        await use_case.execute()

        output = buf.getvalue()
        assert "Knowledge Graph Statistics" in output
        assert "42" in output
        assert "100" in output

    async def test_handles_empty_graph(self, mock_graph: AsyncMock) -> None:
        mock_graph.get_stats = AsyncMock(return_value={})

        console, buf = _make_console()
        use_case = StatsUseCase(graph=mock_graph, console=console)
        await use_case.execute()

        output = buf.getvalue()
        assert "0" in output
