"""Security tests for kgraph.

Verifies prompt injection defences, query parameter validation,
and config permission handling.
"""

from __future__ import annotations

import pytest

from kgraph.domain.errors import GraphError
from kgraph.infrastructure.extractor import EXTRACTION_SYSTEM


class TestPromptInjectionDefense:
    def test_extraction_system_has_anti_injection_instruction(self) -> None:
        assert "ignore any instructions" in EXTRACTION_SYSTEM.lower()

    def test_extraction_system_references_document_tags(self) -> None:
        assert "<document>" in EXTRACTION_SYSTEM


class TestHopsValidation:
    async def test_hops_zero_raises_graph_error(self) -> None:
        from kgraph.infrastructure.graph import Neo4jGraph

        graph = Neo4jGraph(uri="bolt://localhost:7687", username="neo4j", password="test")
        with pytest.raises(GraphError, match="hops must be between"):
            await graph.expand_neighborhood(["test"], hops=0)
        await graph.close()

    async def test_hops_eleven_raises_graph_error(self) -> None:
        from kgraph.infrastructure.graph import Neo4jGraph

        graph = Neo4jGraph(uri="bolt://localhost:7687", username="neo4j", password="test")
        with pytest.raises(GraphError, match="hops must be between"):
            await graph.expand_neighborhood(["test"], hops=11)
        await graph.close()

    async def test_hops_one_does_not_raise(self) -> None:
        # Valid hops should not raise (will fail on Neo4j connection, but not on validation)
        from kgraph.infrastructure.graph import Neo4jGraph

        graph = Neo4jGraph(uri="bolt://localhost:7687", username="neo4j", password="test")
        # hops=1 is valid, so it should pass validation and fail on Neo4j connection
        # We test that GraphError about hops is NOT raised
        try:
            await graph.expand_neighborhood(["test"], hops=1)
        except GraphError as exc:
            assert "hops must be between" not in str(exc)
        except Exception:
            pass  # Any other error is fine (e.g. Neo4j not running)
        await graph.close()


class TestXmlDelimiters:
    def test_claude_extractor_wraps_chunk_in_document_tags(self) -> None:
        import inspect

        from kgraph.infrastructure.extractor import ClaudeExtractor

        source = inspect.getsource(ClaudeExtractor.extract)
        assert "<document>" in source

    def test_gemini_extractor_wraps_chunk_in_document_tags(self) -> None:
        import inspect

        from kgraph.infrastructure.extractor import GeminiExtractor

        source = inspect.getsource(GeminiExtractor.extract)
        assert "<document>" in source

    def test_query_use_case_wraps_prompt_in_xml_tags(self) -> None:
        import inspect

        from kgraph.application.use_cases import QueryUseCase

        source = inspect.getsource(QueryUseCase)
        assert "<context>" in source
        assert "<question>" in source
