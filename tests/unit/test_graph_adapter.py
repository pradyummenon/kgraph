"""Unit tests for the Neo4jGraph infrastructure adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kgraph.domain.errors import GraphError, ServiceUnavailableError
from kgraph.domain.models import Entity, EntityType, Relationship


def _make_entity(name: str = "Marie Curie", embedding: tuple[float, ...] = ()) -> Entity:
    return Entity(
        name=name,
        entity_type=EntityType.PERSON,
        description="A scientist",
        source="test.md",
        embedding=embedding,
    )


def _make_relationship(source: str = "A", target: str = "B") -> Relationship:
    return Relationship(source=source, target=target, relationship_type="KNOWS", description="test")


def _mock_driver() -> MagicMock:
    driver = MagicMock()
    driver.close = AsyncMock()
    driver.verify_connectivity = AsyncMock()
    return driver


def _make_neo4j_graph(driver: MagicMock) -> object:
    with patch("kgraph.infrastructure.graph.AsyncGraphDatabase.driver", return_value=driver):
        from kgraph.infrastructure.graph import Neo4jGraph

        return Neo4jGraph(uri="bolt://localhost:7687", username="neo4j", password="test")


class TestAsyncContextManager:
    async def test_aenter_returns_graph_instance(self) -> None:
        driver = _mock_driver()
        graph = _make_neo4j_graph(driver)
        result = await graph.__aenter__()
        assert result is graph

    async def test_aexit_closes_driver(self) -> None:
        driver = _mock_driver()
        graph = _make_neo4j_graph(driver)
        await graph.__aexit__(None, None, None)
        driver.close.assert_called_once()

    async def test_async_context_manager_closes_on_exit(self) -> None:
        driver = _mock_driver()
        with patch("kgraph.infrastructure.graph.AsyncGraphDatabase.driver", return_value=driver):
            from kgraph.infrastructure.graph import Neo4jGraph

            async with Neo4jGraph(uri="bolt://localhost:7687", username="neo4j", password="test"):
                pass

        driver.close.assert_called_once()


class TestVerifyConnection:
    async def test_returns_true_when_connectivity_succeeds(self) -> None:
        driver = _mock_driver()
        driver.verify_connectivity = AsyncMock(return_value=None)
        graph = _make_neo4j_graph(driver)

        result = await graph.verify_connection()
        assert result is True

    async def test_returns_false_when_connectivity_fails(self) -> None:
        driver = _mock_driver()
        driver.verify_connectivity = AsyncMock(side_effect=Exception("connection refused"))
        graph = _make_neo4j_graph(driver)

        result = await graph.verify_connection()
        assert result is False


class TestIngestEntities:
    def _make_session_mock(self, written: int = 1) -> MagicMock:
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value={"written": written})
        session.run = AsyncMock(return_value=result)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    async def test_empty_list_returns_zero_without_session(self) -> None:
        driver = _mock_driver()
        graph = _make_neo4j_graph(driver)
        count = await graph.ingest_entities([])
        assert count == 0
        driver.session.assert_not_called()

    async def test_calls_merge_cypher_with_correct_params(self) -> None:
        driver = _mock_driver()
        session = self._make_session_mock(written=1)
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        entity = _make_entity(name="Test Entity", embedding=(0.1, 0.2, 0.3))
        count = await graph.ingest_entities([entity])

        assert count == 1
        session.run.assert_called_once()
        call_kwargs = session.run.call_args
        assert "MERGE" in call_kwargs.args[0]
        params = call_kwargs.kwargs["entities"]
        assert params[0]["name"] == "Test Entity"

    async def test_neo4j_retryable_error_raises_service_unavailable(self) -> None:
        from neo4j.exceptions import ServiceUnavailable
        from tenacity import wait_none

        driver = _mock_driver()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        session.run = AsyncMock(side_effect=ServiceUnavailable("connection lost"))
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        graph.ingest_entities.retry.wait = wait_none()
        entity = _make_entity(embedding=(0.1,))
        with pytest.raises(ServiceUnavailableError):
            await graph.ingest_entities([entity])

    async def test_neo4j_fatal_error_raises_graph_error(self) -> None:
        from neo4j.exceptions import DatabaseError

        driver = _mock_driver()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        session.run = AsyncMock(side_effect=DatabaseError("constraint violation"))
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        entity = _make_entity(embedding=(0.1,))
        with pytest.raises(GraphError, match="Neo4j error during entity ingest"):
            await graph.ingest_entities([entity])


class TestIngestRelationships:
    def _make_session_mock(self, written: int = 1) -> MagicMock:
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value={"written": written})
        session.run = AsyncMock(return_value=result)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    async def test_empty_list_returns_zero_without_session(self) -> None:
        driver = _mock_driver()
        graph = _make_neo4j_graph(driver)
        count = await graph.ingest_relationships([])
        assert count == 0
        driver.session.assert_not_called()

    async def test_calls_merge_cypher_with_correct_params(self) -> None:
        driver = _mock_driver()
        session = self._make_session_mock(written=2)
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        rels = [_make_relationship("A", "B"), _make_relationship("C", "D")]
        count = await graph.ingest_relationships(rels)

        assert count == 2
        session.run.assert_called_once()
        call_kwargs = session.run.call_args
        assert "MERGE" in call_kwargs.args[0]


class TestVectorSearch:
    async def test_returns_entity_score_pairs(self) -> None:
        driver = _mock_driver()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        raw_records = [
            {
                "name": "Marie Curie",
                "entity_type": "PERSON",
                "description": "Physicist",
                "source": "test.md",
                "score": 0.95,
            }
        ]

        async def async_iter():
            for r in raw_records:
                yield r

        mock_result.__aiter__ = lambda self: async_iter()
        session.run = AsyncMock(return_value=mock_result)
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        results = await graph.vector_search(embedding=[0.1, 0.2], top_k=5)

        assert len(results) == 1
        entity, score = results[0]
        assert entity.name == "Marie Curie"
        assert score == 0.95

    async def test_empty_result_returns_empty_list(self) -> None:
        driver = _mock_driver()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()

        async def empty_iter():
            return
            yield

        mock_result.__aiter__ = lambda self: empty_iter()
        session.run = AsyncMock(return_value=mock_result)
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        results = await graph.vector_search(embedding=[0.1], top_k=5)

        assert results == []


class TestExpandNeighborhood:
    async def test_hops_zero_raises_graph_error(self) -> None:
        driver = _mock_driver()
        graph = _make_neo4j_graph(driver)
        with pytest.raises(GraphError, match="hops must be between"):
            await graph.expand_neighborhood(["test"], hops=0)

    async def test_hops_eleven_raises_graph_error(self) -> None:
        driver = _mock_driver()
        graph = _make_neo4j_graph(driver)
        with pytest.raises(GraphError, match="hops must be between"):
            await graph.expand_neighborhood(["test"], hops=11)

    async def test_valid_hops_returns_entities_and_relationships(self) -> None:
        driver = _mock_driver()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        record = {
            "entities": [
                {
                    "name": "Python",
                    "entity_type": "TECHNOLOGY",
                    "description": "A language",
                    "source": "test.md",
                }
            ],
            "relationships": [
                {
                    "source": "Django",
                    "target": "Python",
                    "rel_type": "BUILT_WITH",
                    "description": "built on Python",
                }
            ],
        }
        mock_result.single = AsyncMock(return_value=record)
        session.run = AsyncMock(return_value=mock_result)
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        entities, relationships = await graph.expand_neighborhood(["Python"], hops=2)

        assert len(entities) == 1
        assert entities[0].name == "Python"
        assert len(relationships) == 1
        assert relationships[0].relationship_type == "BUILT_WITH"

    async def test_no_record_returns_empty_lists(self) -> None:
        driver = _mock_driver()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=mock_result)
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        entities, relationships = await graph.expand_neighborhood(["unknown"], hops=1)

        assert entities == []
        assert relationships == []


class TestFulltextSearch:
    async def test_returns_matching_entities(self) -> None:
        driver = _mock_driver()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        raw_records = [
            {
                "name": "Marie Curie",
                "entity_type": "PERSON",
                "description": "Physicist",
                "source": "test.md",
            }
        ]

        async def async_iter():
            for r in raw_records:
                yield r

        mock_result.__aiter__ = lambda self: async_iter()
        session.run = AsyncMock(return_value=mock_result)
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        results = await graph.fulltext_search("Marie Curie", limit=5)

        assert len(results) == 1
        assert results[0].name == "Marie Curie"

    async def test_no_matches_returns_empty_list(self) -> None:
        driver = _mock_driver()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()

        async def empty_iter():
            return
            yield

        mock_result.__aiter__ = lambda self: empty_iter()
        session.run = AsyncMock(return_value=mock_result)
        driver.session = MagicMock(return_value=session)

        graph = _make_neo4j_graph(driver)
        results = await graph.fulltext_search("nothing", limit=5)

        assert results == []
