"""Tests for the NetworkX graph converter."""

from kgraph.domain.models import Entity, EntityType, Relationship
from kgraph.infrastructure.graph_converter import to_networkx


class TestToNetworkx:
    """Tests for the to_networkx conversion function."""

    def test_entities_become_nodes_with_correct_attributes(self) -> None:
        entities = [
            Entity(
                name="Python",
                entity_type=EntityType.TECHNOLOGY,
                description="Programming language",
                source="test.md",
            )
        ]
        graph = to_networkx(entities, [])

        assert "Python" in graph.nodes
        assert graph.nodes["Python"]["entity_type"] == "TECHNOLOGY"
        assert graph.nodes["Python"]["description"] == "Programming language"

    def test_relationships_become_edges_with_correct_attributes(self) -> None:
        entities = [
            Entity(
                name="Django",
                entity_type=EntityType.TECHNOLOGY,
                description="Web framework",
                source="test.md",
            ),
            Entity(
                name="Python",
                entity_type=EntityType.TECHNOLOGY,
                description="Programming language",
                source="test.md",
            ),
        ]
        relationships = [
            Relationship(
                source="Django",
                target="Python",
                relationship_type="BUILT_WITH",
                description="Django is built with Python",
            )
        ]
        graph = to_networkx(entities, relationships)

        assert graph.has_edge("Django", "Python")
        edge_data = graph.edges["Django", "Python"]
        assert edge_data["relationship_type"] == "BUILT_WITH"
        assert edge_data["description"] == "Django is built with Python"

    def test_empty_inputs_return_empty_digraph(self) -> None:
        graph = to_networkx([], [])

        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_duplicate_entity_names_last_write_wins(self) -> None:
        entities = [
            Entity(
                name="Python",
                entity_type=EntityType.TECHNOLOGY,
                description="First description",
                source="a.md",
            ),
            Entity(
                name="Python",
                entity_type=EntityType.CONCEPT,
                description="Second description",
                source="b.md",
            ),
        ]
        graph = to_networkx(entities, [])

        assert graph.number_of_nodes() == 1
        assert graph.nodes["Python"]["description"] == "Second description"
        assert graph.nodes["Python"]["entity_type"] == "CONCEPT"

    def test_relationships_referencing_missing_entities_still_creates_edges(self) -> None:
        relationships = [
            Relationship(
                source="Ghost",
                target="Phantom",
                relationship_type="HAUNTS",
                description="Ghost haunts Phantom",
            )
        ]
        graph = to_networkx([], relationships)

        assert graph.has_edge("Ghost", "Phantom")
        assert "Ghost" in graph.nodes
        assert "Phantom" in graph.nodes
