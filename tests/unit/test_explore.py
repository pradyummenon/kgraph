"""Unit tests for ExploreUseCase — recursive tree, filters, and summary panel."""

from __future__ import annotations

from io import StringIO
from unittest.mock import AsyncMock

import pytest
from rich.console import Console

from kgraph.application.use_cases import ExploreUseCase
from kgraph.domain.models import Entity, EntityType, Relationship


class TestBuildTree:
    @pytest.mark.asyncio
    async def test_single_hop_shows_direct_neighbors(
        self,
        multi_hop_entities: list[Entity],
        multi_hop_relationships: list[Relationship],
        mock_graph: AsyncMock,
    ) -> None:
        python_entity = Entity(
            name="Python",
            entity_type=EntityType.TECHNOLOGY,
            description="Programming language",
            source="test.md",
        )
        mock_graph.fulltext_search.return_value = [python_entity]
        mock_graph.expand_neighborhood.return_value = (
            multi_hop_entities,
            multi_hop_relationships,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=1)

        result = output.getvalue()
        assert "Python" in result
        assert "Django" in result

    @pytest.mark.asyncio
    async def test_no_entity_found_shows_error(self, mock_graph: AsyncMock) -> None:
        mock_graph.fulltext_search.return_value = []

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Nonexistent", hops=1)

        assert "No entity found" in output.getvalue()

    @pytest.mark.asyncio
    async def test_cycle_detection_prevents_infinite_recursion(self, mock_graph: AsyncMock) -> None:
        entities = [
            Entity(
                name="A",
                entity_type=EntityType.CONCEPT,
                description="Node A",
                source="test.md",
            ),
            Entity(
                name="B",
                entity_type=EntityType.CONCEPT,
                description="Node B",
                source="test.md",
            ),
        ]
        rels = [
            Relationship(source="A", target="B", relationship_type="LINKS", description="A to B"),
            Relationship(source="B", target="A", relationship_type="LINKS", description="B to A"),
        ]
        mock_graph.fulltext_search.return_value = [entities[0]]
        mock_graph.expand_neighborhood.return_value = (entities, rels)

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="A", hops=5)  # must not hang or recurse infinitely

        assert "A" in output.getvalue()

    @pytest.mark.asyncio
    async def test_outgoing_edges_labeled_with_arrow(self, mock_graph: AsyncMock) -> None:
        root = Entity(
            name="Django",
            entity_type=EntityType.TECHNOLOGY,
            description="Web framework",
            source="test.md",
        )
        target = Entity(
            name="Python",
            entity_type=EntityType.TECHNOLOGY,
            description="Language",
            source="test.md",
        )
        rel = Relationship(
            source="Django",
            target="Python",
            relationship_type="BUILT_WITH",
            description="",
        )
        mock_graph.fulltext_search.return_value = [root]
        mock_graph.expand_neighborhood.return_value = ([root, target], [rel])

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Django", hops=1)

        result = output.getvalue()
        assert "BUILT_WITH" in result
        assert "Python" in result

    @pytest.mark.asyncio
    async def test_incoming_edges_shown(self, mock_graph: AsyncMock) -> None:
        root = Entity(
            name="Python",
            entity_type=EntityType.TECHNOLOGY,
            description="Language",
            source="test.md",
        )
        source_entity = Entity(
            name="Django",
            entity_type=EntityType.TECHNOLOGY,
            description="Framework",
            source="test.md",
        )
        rel = Relationship(
            source="Django",
            target="Python",
            relationship_type="BUILT_WITH",
            description="",
        )
        mock_graph.fulltext_search.return_value = [root]
        mock_graph.expand_neighborhood.return_value = ([root, source_entity], [rel])

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=1)

        result = output.getvalue()
        assert "Django" in result


class TestEntityTypeFilter:
    @pytest.mark.asyncio
    async def test_type_filter_excludes_non_matching_entities(
        self,
        multi_hop_entities: list[Entity],
        multi_hop_relationships: list[Relationship],
        mock_graph: AsyncMock,
    ) -> None:
        mock_graph.fulltext_search.return_value = [multi_hop_entities[0]]  # Python
        mock_graph.expand_neighborhood.return_value = (
            multi_hop_entities,
            multi_hop_relationships,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=2, type_filters={"TECHNOLOGY"})

        result = output.getvalue()
        assert "Python" in result
        assert "Guido" not in result

    @pytest.mark.asyncio
    async def test_rel_filter_excludes_non_matching_relationships(
        self,
        multi_hop_entities: list[Entity],
        multi_hop_relationships: list[Relationship],
        mock_graph: AsyncMock,
    ) -> None:
        mock_graph.fulltext_search.return_value = [multi_hop_entities[0]]  # Python
        mock_graph.expand_neighborhood.return_value = (
            multi_hop_entities,
            multi_hop_relationships,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=2, rel_filters={"BUILT_WITH"})

        result = output.getvalue()
        assert "BUILT_WITH" in result
        assert "CREATED" not in result


class TestSummaryPanel:
    @pytest.mark.asyncio
    async def test_summary_panel_shows_counts(
        self,
        multi_hop_entities: list[Entity],
        multi_hop_relationships: list[Relationship],
        mock_graph: AsyncMock,
    ) -> None:
        mock_graph.fulltext_search.return_value = [multi_hop_entities[0]]
        mock_graph.expand_neighborhood.return_value = (
            multi_hop_entities,
            multi_hop_relationships,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=2)

        result = output.getvalue()
        assert "Neighborhood Summary" in result

    @pytest.mark.asyncio
    async def test_summary_panel_shows_entity_count(
        self,
        multi_hop_entities: list[Entity],
        multi_hop_relationships: list[Relationship],
        mock_graph: AsyncMock,
    ) -> None:
        mock_graph.fulltext_search.return_value = [multi_hop_entities[0]]
        mock_graph.expand_neighborhood.return_value = (
            multi_hop_entities,
            multi_hop_relationships,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=2)

        result = output.getvalue()
        assert "Entities:" in result
        assert "Relationships:" in result

    @pytest.mark.asyncio
    async def test_summary_panel_shows_root_name(
        self,
        multi_hop_entities: list[Entity],
        multi_hop_relationships: list[Relationship],
        mock_graph: AsyncMock,
    ) -> None:
        mock_graph.fulltext_search.return_value = [multi_hop_entities[0]]
        mock_graph.expand_neighborhood.return_value = (
            multi_hop_entities,
            multi_hop_relationships,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        use_case = ExploreUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=2)

        result = output.getvalue()
        assert "Python" in result
        assert "Root:" in result
