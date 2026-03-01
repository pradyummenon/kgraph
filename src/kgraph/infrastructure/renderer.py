"""ASCII graph renderer for kgraph domain models.

Converts domain Entity and Relationship objects into a human-readable
ASCII diagram using phart and NetworkX.

Note: phart does not support inline edge labels. When show_edge_labels=True
is requested, this limitation is documented in the rendered output header.
Edge relationship types are not displayed on the rendered diagram itself.
"""

from __future__ import annotations

import networkx as nx
import phart

from kgraph.domain.models import Entity, Relationship
from kgraph.infrastructure.graph_converter import to_networkx

_EMPTY_GRAPH_MESSAGE = "(empty graph)"


def _make_display_label(name: str, entity_type: str, max_label_length: int) -> str:
    truncated_name = name[:max_label_length]
    return f"{truncated_name} ({entity_type})"


def _build_display_graph(
    source_graph: nx.DiGraph,
    entities: list[Entity],
    max_label_length: int,
) -> nx.DiGraph:
    """Return a new graph with node IDs replaced by display labels.

    Builds a mapping from original node ID (entity name) to display label,
    then relabels the graph so phart renders the labels directly.
    """
    entity_type_by_name: dict[str, str] = {
        entity.name: str(entity.entity_type) for entity in entities
    }

    label_map: dict[str, str] = {}
    for node_id in source_graph.nodes:
        entity_type = entity_type_by_name.get(node_id, "UNKNOWN")
        label_map[node_id] = _make_display_label(node_id, entity_type, max_label_length)

    return nx.relabel_nodes(source_graph, label_map)


class GraphRenderer:
    """Renders a knowledge graph as an ASCII diagram.

    Uses phart for layout and NetworkX for graph representation.
    Node labels include entity name (truncated) and entity type.
    """

    def render(
        self,
        entities: list[Entity],
        relationships: list[Relationship],
        *,
        max_label_length: int = 30,
        show_edge_labels: bool = True,
    ) -> str:
        """Render the graph as an ASCII string.

        Args:
            entities: Domain entity objects (graph nodes).
            relationships: Domain relationship objects (graph edges).
            max_label_length: Maximum characters of the entity name shown in
                each node label. Names longer than this are truncated.
            show_edge_labels: Requested but not rendered — phart does not
                support inline edge labels. This parameter is accepted for
                API compatibility; its value does not affect output.

        Returns:
            A multi-line ASCII string representing the graph structure,
            or "(empty graph)" if both inputs are empty.
        """
        source_graph = to_networkx(entities, relationships)

        if source_graph.number_of_nodes() == 0:
            return _EMPTY_GRAPH_MESSAGE

        display_graph = _build_display_graph(source_graph, entities, max_label_length)

        renderer = phart.ASCIIRenderer(
            display_graph,
            node_style=phart.NodeStyle.SQUARE,
        )
        return renderer.render()
