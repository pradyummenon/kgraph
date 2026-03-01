"""Mutable state manager for the TUI graph browser.

Holds the current in-memory view of the graph: which entities have been
loaded, which relationships exist between them, what filters are active,
and which entity is currently selected.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kgraph.domain.models import Entity, Relationship


@dataclass
class GraphState:
    """Mutable view of the knowledge graph for TUI rendering.

    All mutation goes through add_neighborhood so deduplication logic
    is centralised and consistent across all code paths.
    """

    entities: dict[str, Entity] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)
    selected_entity: str | None = None
    expanded_entities: set[str] = field(default_factory=set)
    type_filters: set[str] = field(default_factory=set)
    search_filter: str = ""

    def add_neighborhood(self, entities: list[Entity], relationships: list[Relationship]) -> None:
        """Merge entities and relationships into state, deduplicating."""
        for entity in entities:
            self.entities[entity.name] = entity

        existing = {(r.source, r.target, r.relationship_type) for r in self.relationships}
        for rel in relationships:
            key = (rel.source, rel.target, rel.relationship_type)
            if key not in existing:
                self.relationships.append(rel)
                existing.add(key)

    @property
    def visible_entities(self) -> list[Entity]:
        """Entities filtered by type_filters. Empty filters = all visible."""
        if not self.type_filters:
            return list(self.entities.values())
        return [
            e for e in self.entities.values() if str(e.entity_type).upper() in self.type_filters
        ]

    @property
    def visible_relationships(self) -> list[Relationship]:
        """Only relationships between visible entities."""
        visible_names = {e.name for e in self.visible_entities}
        return [
            r for r in self.relationships if r.source in visible_names and r.target in visible_names
        ]

    @property
    def filtered_entities(self) -> list[Entity]:
        """Apply both type filters and search filter."""
        entities = self.visible_entities
        if not self.search_filter:
            return entities
        query = self.search_filter.lower()
        return [e for e in entities if query in e.name.lower() or query in e.description.lower()]

    def relationships_for(self, entity_name: str) -> list[Relationship]:
        """Return visible relationships where entity_name is source or target."""
        return [
            r
            for r in self.visible_relationships
            if r.source == entity_name or r.target == entity_name
        ]

    @property
    def entity_types(self) -> set[str]:
        """All unique entity types present in the state."""
        return {str(e.entity_type) for e in self.entities.values()}
