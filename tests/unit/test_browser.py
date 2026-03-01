"""Unit tests for the GraphBrowser TUI and GraphState search extensions.

TUI tests use textual's AppTest/pilot harness for automated interaction.
GraphState tests cover the new filtered_entities and relationships_for APIs.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kgraph.application.graph_state import GraphState
from kgraph.domain.models import Entity, EntityType, Relationship
from kgraph.interfaces.browser import GraphBrowser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_graph(entities=None, relationships=None):
    """Return a mock graph repository that returns the provided data."""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    mock.get_top_entities = AsyncMock(return_value=(entities or [], relationships or []))
    mock.fulltext_search = AsyncMock(return_value=[])
    mock.expand_neighborhood = AsyncMock(return_value=([], []))
    return mock


# ---------------------------------------------------------------------------
# GraphState — filtered_entities
# ---------------------------------------------------------------------------


@pytest.fixture
def person_entity() -> Entity:
    return Entity(
        name="Marie Curie",
        entity_type=EntityType.PERSON,
        description="Polish-French physicist",
        source="test.md",
    )


@pytest.fixture
def org_entity() -> Entity:
    return Entity(
        name="University of Paris",
        entity_type=EntityType.ORGANIZATION,
        description="French university",
        source="test.md",
    )


@pytest.fixture
def tech_entity() -> Entity:
    return Entity(
        name="X-Ray Machine",
        entity_type=EntityType.TECHNOLOGY,
        description="Medical imaging device",
        source="test.md",
    )


@pytest.fixture
def works_at_rel() -> Relationship:
    return Relationship(
        source="Marie Curie",
        target="University of Paris",
        relationship_type="WORKS_AT",
        description="Marie Curie worked at University of Paris",
    )


@pytest.fixture
def invented_rel() -> Relationship:
    return Relationship(
        source="Marie Curie",
        target="X-Ray Machine",
        relationship_type="INVENTED",
        description="Marie Curie contributed to X-Ray development",
    )


def test_filtered_entities_returns_all_when_no_search_filter(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])

    assert len(state.filtered_entities) == 2


def test_filtered_entities_applies_name_search(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])
    state.search_filter = "marie"

    result = state.filtered_entities
    assert len(result) == 1
    assert result[0].name == "Marie Curie"


def test_filtered_entities_applies_description_search(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])
    state.search_filter = "french university"

    result = state.filtered_entities
    assert len(result) == 1
    assert result[0].name == "University of Paris"


def test_filtered_entities_is_case_insensitive(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])
    state.search_filter = "CURIE"

    result = state.filtered_entities
    assert len(result) == 1
    assert result[0].name == "Marie Curie"


def test_filtered_entities_returns_empty_when_no_match(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])
    state.search_filter = "zzz_no_match"

    assert state.filtered_entities == []


def test_filtered_entities_respects_type_filter_before_search(
    person_entity, org_entity, tech_entity
):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity, tech_entity], [])
    state.type_filters = {"PERSON"}
    state.search_filter = "curie"

    result = state.filtered_entities
    assert len(result) == 1
    assert result[0].name == "Marie Curie"


def test_filtered_entities_type_and_search_both_applied(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])
    state.type_filters = {"ORGANIZATION"}
    state.search_filter = "curie"

    assert state.filtered_entities == []


# ---------------------------------------------------------------------------
# GraphState — relationships_for
# ---------------------------------------------------------------------------


def test_relationships_for_returns_edges_where_entity_is_source(
    person_entity, org_entity, tech_entity, works_at_rel, invented_rel
):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity, tech_entity], [works_at_rel, invented_rel])

    result = state.relationships_for("Marie Curie")
    assert len(result) == 2
    rel_types = {r.relationship_type for r in result}
    assert rel_types == {"WORKS_AT", "INVENTED"}


def test_relationships_for_returns_edges_where_entity_is_target(
    person_entity, org_entity, works_at_rel
):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [works_at_rel])

    result = state.relationships_for("University of Paris")
    assert len(result) == 1
    assert result[0].relationship_type == "WORKS_AT"


def test_relationships_for_returns_empty_when_entity_not_involved(
    person_entity, org_entity, works_at_rel
):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [works_at_rel])

    result = state.relationships_for("Nonexistent Entity")
    assert result == []


def test_relationships_for_respects_visible_relationships(
    person_entity, org_entity, tech_entity, works_at_rel, invented_rel
):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity, tech_entity], [works_at_rel, invented_rel])
    state.type_filters = {"PERSON", "ORGANIZATION"}

    result = state.relationships_for("Marie Curie")
    assert len(result) == 1
    assert result[0].relationship_type == "WORKS_AT"


# ---------------------------------------------------------------------------
# TUI — app launch and key bindings
# ---------------------------------------------------------------------------


async def test_app_launches_without_error():
    mock_graph = _make_mock_graph()
    app = GraphBrowser(graph=mock_graph)
    async with app.run_test() as pilot:
        assert app.is_running
        _ = pilot  # pilot used for context management


async def test_quit_key_exits_app():
    mock_graph = _make_mock_graph()
    app = GraphBrowser(graph=mock_graph)
    async with app.run_test() as pilot:
        await pilot.press("q")


async def test_search_input_focused_on_slash():
    mock_graph = _make_mock_graph()
    app = GraphBrowser(graph=mock_graph)
    async with app.run_test() as pilot:
        await pilot.press("/")
        search_input = app.query_one("#search-input")
        assert search_input.has_focus


async def test_app_composes_all_required_widgets():
    mock_graph = _make_mock_graph()
    app = GraphBrowser(graph=mock_graph)
    async with app.run_test():
        assert app.query_one("#search-input") is not None
        assert app.query_one("#entity-tree") is not None
        assert app.query_one("#details-panel") is not None
        assert app.query_one("#graph-view") is not None
        assert app.query_one("#relationships-table") is not None


async def test_relationships_table_has_four_columns():
    mock_graph = _make_mock_graph()
    app = GraphBrowser(graph=mock_graph)
    async with app.run_test():
        table = app.query_one("#relationships-table")
        assert len(table.columns) == 4
