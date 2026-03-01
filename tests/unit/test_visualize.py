"""Unit tests for VisualizeUseCase — entity-centered and overview modes."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock

from rich.console import Console

from kgraph.application.use_cases import VisualizeUseCase
from kgraph.domain.models import Entity, EntityType, Relationship


def _make_console() -> tuple[Console, StringIO]:
    buf = StringIO()
    return Console(file=buf, force_terminal=False), buf


def _make_entity(name: str, entity_type: EntityType = EntityType.TECHNOLOGY) -> Entity:
    return Entity(
        name=name,
        entity_type=entity_type,
        description=f"Description of {name}",
        source="test.md",
    )


def _make_relationship(source: str, target: str, rel_type: str = "RELATES_TO") -> Relationship:
    return Relationship(
        source=source,
        target=target,
        relationship_type=rel_type,
        description=f"{source} {rel_type} {target}",
    )


class TestEntityCenteredMode:
    async def test_calls_fulltext_search_and_expand_neighborhood(
        self, mock_graph: AsyncMock
    ) -> None:
        root = _make_entity("Python")
        neighbor = _make_entity("Django")
        rel = _make_relationship("Django", "Python", "BUILT_WITH")
        mock_graph.fulltext_search.return_value = [root]
        mock_graph.expand_neighborhood.return_value = ([root, neighbor], [rel])

        console, _ = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=2)

        mock_graph.fulltext_search.assert_called_once_with("Python", limit=1)
        mock_graph.expand_neighborhood.assert_called_once_with(["Python"], 2)

    async def test_entity_centered_output_contains_entity_names(
        self, mock_graph: AsyncMock
    ) -> None:
        root = _make_entity("Python")
        neighbor = _make_entity("Django")
        rel = _make_relationship("Django", "Python", "BUILT_WITH")
        mock_graph.fulltext_search.return_value = [root]
        mock_graph.expand_neighborhood.return_value = ([root, neighbor], [rel])

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=2)

        result = buf.getvalue()
        assert "Python" in result
        assert "Django" in result

    async def test_entity_not_found_shows_error_message(self, mock_graph: AsyncMock) -> None:
        mock_graph.fulltext_search.return_value = []

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Nonexistent", hops=2)

        result = buf.getvalue()
        assert "No entity found" in result
        mock_graph.expand_neighborhood.assert_not_called()

    async def test_hops_passed_to_expand_neighborhood(self, mock_graph: AsyncMock) -> None:
        root = _make_entity("Python")
        mock_graph.fulltext_search.return_value = [root]
        mock_graph.expand_neighborhood.return_value = ([root], [])

        console, _ = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python", hops=3)

        mock_graph.expand_neighborhood.assert_called_once_with(["Python"], 3)


class TestOverviewMode:
    async def test_calls_get_top_entities_when_no_entity_name(self, mock_graph: AsyncMock) -> None:
        entities = [_make_entity("Python"), _make_entity("Django")]
        relationships = [_make_relationship("Django", "Python")]
        mock_graph.get_top_entities.return_value = (entities, relationships)

        console, _ = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name=None, max_nodes=50)

        mock_graph.get_top_entities.assert_called_once_with(50)
        mock_graph.fulltext_search.assert_not_called()

    async def test_max_nodes_passed_to_get_top_entities(self, mock_graph: AsyncMock) -> None:
        mock_graph.get_top_entities.return_value = ([], [])

        console, _ = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name=None, max_nodes=25)

        mock_graph.get_top_entities.assert_called_once_with(25)

    async def test_overview_output_contains_entity_names(self, mock_graph: AsyncMock) -> None:
        entities = [_make_entity("Python"), _make_entity("Flask")]
        relationships = [_make_relationship("Flask", "Python")]
        mock_graph.get_top_entities.return_value = (entities, relationships)

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute()

        result = buf.getvalue()
        assert "Python" in result
        assert "Flask" in result

    async def test_empty_graph_shows_helpful_message(self, mock_graph: AsyncMock) -> None:
        mock_graph.get_top_entities.return_value = ([], [])

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute()

        result = buf.getvalue()
        assert "(empty graph)" in result


class TestEntityTypeFilter:
    async def test_type_filter_excludes_non_matching_entities(self, mock_graph: AsyncMock) -> None:
        python = _make_entity("Python", EntityType.TECHNOLOGY)
        guido = _make_entity("Guido", EntityType.PERSON)
        rel = _make_relationship("Guido", "Python", "CREATED")
        mock_graph.get_top_entities.return_value = ([python, guido], [rel])

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_types={"TECHNOLOGY"})

        result = buf.getvalue()
        assert "Python" in result
        assert "Guido" not in result

    async def test_type_filter_removes_cross_type_relationships(
        self, mock_graph: AsyncMock
    ) -> None:
        python = _make_entity("Python", EntityType.TECHNOLOGY)
        guido = _make_entity("Guido", EntityType.PERSON)
        rel = _make_relationship("Guido", "Python", "CREATED")
        mock_graph.get_top_entities.return_value = ([python, guido], [rel])

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_types={"TECHNOLOGY"})

        result = buf.getvalue()
        assert "CREATED" not in result

    async def test_no_type_filter_includes_all_entities(self, mock_graph: AsyncMock) -> None:
        python = _make_entity("Python", EntityType.TECHNOLOGY)
        guido = _make_entity("Guido", EntityType.PERSON)
        rel = _make_relationship("Guido", "Python", "CREATED")
        mock_graph.get_top_entities.return_value = ([python, guido], [rel])

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_types=None)

        result = buf.getvalue()
        assert "Python" in result
        assert "Guido" in result


class TestOutputToFile:
    async def test_output_path_writes_content_to_file(
        self, mock_graph: AsyncMock, tmp_path: Path
    ) -> None:
        entities = [_make_entity("Python"), _make_entity("Django")]
        relationships = [_make_relationship("Django", "Python")]
        mock_graph.get_top_entities.return_value = (entities, relationships)

        output_file = tmp_path / "graph.txt"
        console, _ = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(output_path=output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert len(content) > 0

    async def test_output_path_confirms_write_in_console(
        self, mock_graph: AsyncMock, tmp_path: Path
    ) -> None:
        mock_graph.get_top_entities.return_value = ([], [])

        output_file = tmp_path / "graph.txt"
        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(output_path=output_file)

        result = buf.getvalue()
        assert "graph.txt" in result

    async def test_no_output_path_prints_to_console(self, mock_graph: AsyncMock) -> None:
        entities = [_make_entity("Python")]
        mock_graph.get_top_entities.return_value = (entities, [])

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(output_path=None)

        result = buf.getvalue()
        assert "Python" in result


class TestSummaryPanel:
    async def test_summary_shows_entity_count(self, mock_graph: AsyncMock) -> None:
        entities = [_make_entity("Python"), _make_entity("Django")]
        relationships = [_make_relationship("Django", "Python")]
        mock_graph.get_top_entities.return_value = (entities, relationships)

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute()

        result = buf.getvalue()
        assert "Entities:" in result
        assert "Relationships:" in result

    async def test_summary_shows_overview_mode_label(self, mock_graph: AsyncMock) -> None:
        mock_graph.get_top_entities.return_value = ([], [])

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name=None)

        result = buf.getvalue()
        assert "overview" in result

    async def test_summary_shows_entity_name_in_entity_centered_mode(
        self, mock_graph: AsyncMock
    ) -> None:
        root = _make_entity("Python")
        mock_graph.fulltext_search.return_value = [root]
        mock_graph.expand_neighborhood.return_value = ([root], [])

        console, buf = _make_console()
        use_case = VisualizeUseCase(graph=mock_graph, console=console)
        await use_case.execute(entity_name="Python")

        result = buf.getvalue()
        assert "Python" in result
        assert "entity:" in result
