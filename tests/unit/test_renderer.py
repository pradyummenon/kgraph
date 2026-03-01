"""Tests for the ASCII graph renderer."""

import pytest

from kgraph.domain.models import Entity, EntityType, Relationship
from kgraph.infrastructure.renderer import _EMPTY_GRAPH_MESSAGE, GraphRenderer


@pytest.fixture
def renderer() -> GraphRenderer:
    return GraphRenderer()


@pytest.fixture
def tech_entities() -> list[Entity]:
    return [
        Entity(
            name="Django",
            entity_type=EntityType.TECHNOLOGY,
            description="Python web framework",
            source="test.md",
        ),
        Entity(
            name="Python",
            entity_type=EntityType.TECHNOLOGY,
            description="Programming language",
            source="test.md",
        ),
    ]


@pytest.fixture
def tech_relationships() -> list[Relationship]:
    return [
        Relationship(
            source="Django",
            target="Python",
            relationship_type="BUILT_WITH",
            description="Django is built with Python",
        )
    ]


class TestGraphRenderer:
    """Tests for GraphRenderer.render()."""

    def test_render_output_contains_all_entity_names(
        self,
        renderer: GraphRenderer,
        tech_entities: list[Entity],
        tech_relationships: list[Relationship],
    ) -> None:
        output = renderer.render(tech_entities, tech_relationships)

        assert "Django" in output
        assert "Python" in output

    def test_max_label_length_truncates_long_names(
        self,
        renderer: GraphRenderer,
    ) -> None:
        entities = [
            Entity(
                name="A very long entity name that should be truncated",
                entity_type=EntityType.CONCEPT,
                description="Something",
                source="test.md",
            )
        ]
        output = renderer.render(entities, [], max_label_length=10)

        assert "A very lon" in output
        assert "A very long entity name that should be truncated" not in output

    def test_show_edge_labels_false_renders_without_error(
        self,
        renderer: GraphRenderer,
        tech_entities: list[Entity],
        tech_relationships: list[Relationship],
    ) -> None:
        output = renderer.render(
            tech_entities,
            tech_relationships,
            show_edge_labels=False,
        )

        assert isinstance(output, str)
        assert len(output) > 0

    def test_show_edge_labels_true_renders_without_error(
        self,
        renderer: GraphRenderer,
        tech_entities: list[Entity],
        tech_relationships: list[Relationship],
    ) -> None:
        output = renderer.render(
            tech_entities,
            tech_relationships,
            show_edge_labels=True,
        )

        assert isinstance(output, str)
        assert len(output) > 0

    def test_empty_graph_returns_empty_message(
        self,
        renderer: GraphRenderer,
    ) -> None:
        output = renderer.render([], [])

        assert output == _EMPTY_GRAPH_MESSAGE

    def test_single_disconnected_node_renders_without_error(
        self,
        renderer: GraphRenderer,
    ) -> None:
        entities = [
            Entity(
                name="Solitude",
                entity_type=EntityType.CONCEPT,
                description="Alone node",
                source="test.md",
            )
        ]
        output = renderer.render(entities, [])

        assert isinstance(output, str)
        assert "Solitude" in output

    def test_small_known_graph_renders_without_error(
        self,
        renderer: GraphRenderer,
        tech_entities: list[Entity],
        tech_relationships: list[Relationship],
    ) -> None:
        output = renderer.render(tech_entities, tech_relationships)

        assert isinstance(output, str)
        assert len(output.strip()) > 0
