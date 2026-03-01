"""Interactive TUI knowledge graph browser.

Provides a keyboard-driven interface for exploring the graph:
- Entity tree in the sidebar with live search
- ASCII graph view in the main panel
- Relationship table filtered to the selected entity
- Expand-on-demand neighborhood loading
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static, Tree


class GraphBrowser(App):
    """Interactive knowledge graph browser."""

    CSS_PATH = "browser.tcss"
    TITLE = "kgraph browser"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("/", "focus_search", "Search"),
        Binding("e", "expand_entity", "Expand"),
        Binding("f", "toggle_filters", "Filters"),
        Binding("r", "refresh", "Refresh"),
        Binding("tab", "focus_next", "Next Panel"),
    ]

    def __init__(self, graph, start_entity=None, hops=2):
        super().__init__()
        self._graph = graph
        self._start_entity = start_entity
        self._hops = hops
        from kgraph.application.graph_state import GraphState

        self._state = GraphState()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Input(placeholder="Search entities...", id="search-input")
                yield Tree("Entities", id="entity-tree")
                yield Static("Select an entity to view details", id="details-panel")
            with Vertical(id="main-panel"):
                yield Static("Loading graph...", id="graph-view")
                yield DataTable(id="relationships-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#relationships-table", DataTable)
        table.add_columns("Source", "Type", "Target", "Description")
        self.run_worker(self._load_initial_data())

    async def _load_initial_data(self) -> None:
        """Load initial graph data."""
        if self._start_entity:
            matches = await self._graph.fulltext_search(self._start_entity, limit=1)
            if matches:
                root = matches[0]
                entities, rels = await self._graph.expand_neighborhood([root.name], self._hops)
                self._state.add_neighborhood(entities, rels)
                self._state.selected_entity = root.name
        else:
            entities, rels = await self._graph.get_top_entities(limit=50)
            self._state.add_neighborhood(entities, rels)

        self._refresh_tree()
        self._refresh_graph_view()

    def _refresh_tree(self) -> None:
        tree = self.query_one("#entity-tree", Tree)
        tree.clear()
        for entity in sorted(self._state.visible_entities, key=lambda e: e.name):
            tree.root.add_leaf(f"{entity.name} ({entity.entity_type})", data=entity.name)
        tree.root.expand()

    def _refresh_graph_view(self) -> None:
        from kgraph.infrastructure.renderer import GraphRenderer

        renderer = GraphRenderer()
        output = renderer.render(self._state.visible_entities, self._state.visible_relationships)
        view = self.query_one("#graph-view", Static)
        view.update(output)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data:
            self._state.selected_entity = event.node.data
            self._refresh_details()
            self._refresh_relationships()

    def _refresh_details(self) -> None:
        entity = self._state.entities.get(self._state.selected_entity or "")
        panel = self.query_one("#details-panel", Static)
        if entity:
            panel.update(
                f"Name: {entity.name}\n"
                f"Type: {entity.entity_type}\n"
                f"Description: {entity.description}\n"
                f"Source: {entity.source}"
            )

    def _refresh_relationships(self) -> None:
        table = self.query_one("#relationships-table", DataTable)
        table.clear()
        name = self._state.selected_entity
        if not name:
            return
        for rel in self._state.visible_relationships:
            if rel.source == name or rel.target == name:
                table.add_row(rel.source, rel.relationship_type, rel.target, rel.description)

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_expand_entity(self) -> None:
        if self._state.selected_entity:
            self.run_worker(self._expand_selected())

    async def _expand_selected(self) -> None:
        name = self._state.selected_entity
        if not name or name in self._state.expanded_entities:
            return
        entities, rels = await self._graph.expand_neighborhood([name], 1)
        self._state.add_neighborhood(entities, rels)
        self._state.expanded_entities.add(name)
        self._refresh_tree()
        self._refresh_graph_view()

    def action_toggle_filters(self) -> None:
        pass

    def action_refresh(self) -> None:
        from kgraph.application.graph_state import GraphState

        self._state = GraphState()
        self.run_worker(self._load_initial_data())
