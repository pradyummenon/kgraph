"""Unit tests for GraphState.

Covers entity/relationship merging, deduplication, filter visibility,
and selection/expansion tracking.
"""

from __future__ import annotations

import pytest

from kgraph.application.graph_state import GraphState
from kgraph.domain.models import Entity, EntityType, Relationship


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


def test_add_neighborhood_merges_new_entities(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity], [])
    state.add_neighborhood([org_entity], [])

    assert "Marie Curie" in state.entities
    assert "University of Paris" in state.entities
    assert len(state.entities) == 2


def test_add_neighborhood_overwrites_existing_entity_on_same_name(person_entity):
    state = GraphState()
    state.add_neighborhood([person_entity], [])

    updated = Entity(
        name="Marie Curie",
        entity_type=EntityType.PERSON,
        description="Updated description",
        source="new.md",
    )
    state.add_neighborhood([updated], [])

    assert state.entities["Marie Curie"].description == "Updated description"
    assert len(state.entities) == 1


def test_add_neighborhood_deduplicates_relationships(person_entity, org_entity, works_at_rel):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [works_at_rel])
    state.add_neighborhood([person_entity, org_entity], [works_at_rel])

    assert len(state.relationships) == 1


def test_add_neighborhood_adds_distinct_relationships(
    person_entity, org_entity, tech_entity, works_at_rel, invented_rel
):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity, tech_entity], [works_at_rel, invented_rel])

    assert len(state.relationships) == 2


def test_visible_entities_returns_all_when_no_filters(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])

    visible = state.visible_entities
    assert len(visible) == 2


def test_visible_entities_respects_type_filters(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])
    state.type_filters = {"PERSON"}

    visible = state.visible_entities
    assert len(visible) == 1
    assert visible[0].name == "Marie Curie"


def test_visible_entities_empty_when_filter_matches_nothing(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])
    state.type_filters = {"LOCATION"}

    assert state.visible_entities == []


def test_visible_relationships_only_between_visible_entities(
    person_entity, org_entity, tech_entity, works_at_rel, invented_rel
):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity, tech_entity], [works_at_rel, invented_rel])
    state.type_filters = {"PERSON", "ORGANIZATION"}

    visible_rels = state.visible_relationships
    assert len(visible_rels) == 1
    assert visible_rels[0].relationship_type == "WORKS_AT"


def test_visible_relationships_returns_all_when_no_filters(
    person_entity, org_entity, tech_entity, works_at_rel, invented_rel
):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity, tech_entity], [works_at_rel, invented_rel])

    assert len(state.visible_relationships) == 2


def test_entity_types_returns_all_unique_types(person_entity, org_entity, tech_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity, tech_entity], [])

    types = state.entity_types
    assert types == {"PERSON", "ORGANIZATION", "TECHNOLOGY"}


def test_entity_types_empty_when_no_entities():
    state = GraphState()
    assert state.entity_types == set()


def test_selected_entity_tracks_correctly(person_entity):
    state = GraphState()
    state.add_neighborhood([person_entity], [])

    assert state.selected_entity is None
    state.selected_entity = "Marie Curie"
    assert state.selected_entity == "Marie Curie"


def test_expanded_entities_tracks_additions(person_entity, org_entity):
    state = GraphState()
    state.add_neighborhood([person_entity, org_entity], [])

    assert len(state.expanded_entities) == 0
    state.expanded_entities.add("Marie Curie")
    assert "Marie Curie" in state.expanded_entities
    state.expanded_entities.add("University of Paris")
    assert len(state.expanded_entities) == 2
