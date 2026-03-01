"""NetworkX graph converter for kgraph domain models.

Converts domain Entity and Relationship objects into a NetworkX DiGraph
for use with visualization tools and graph algorithms.
"""

from __future__ import annotations

import networkx as nx

from kgraph.domain.models import Entity, Relationship


def to_networkx(entities: list[Entity], relationships: list[Relationship]) -> nx.DiGraph:
    """Convert domain entities and relationships to a NetworkX directed graph.

    Node IDs are entity names. Nodes carry `entity_type` and `description`
    as attributes. Edges carry `relationship_type` and `description` as attributes.

    Duplicate entity names are handled with last-write-wins semantics.
    Relationships referencing entities absent from the entities list are added
    as edges; NetworkX implicitly creates the missing nodes.

    Args:
        entities: Domain entity objects to add as nodes.
        relationships: Domain relationship objects to add as edges.

    Returns:
        A directed NetworkX graph populated with nodes and edges.
    """
    graph = nx.DiGraph()

    for entity in entities:
        graph.add_node(
            entity.name,
            entity_type=str(entity.entity_type),
            description=entity.description,
        )

    for relationship in relationships:
        graph.add_edge(
            relationship.source,
            relationship.target,
            relationship_type=relationship.relationship_type,
            description=relationship.description,
        )

    return graph
