"""Hybrid retrieval for kgraph.

Combines vector search with graph traversal to build rich context
for answering natural language questions. No LLM at retrieval time.
"""

from __future__ import annotations

from kgraph.domain.models import Entity, Relationship, RetrievalResult
from kgraph.infrastructure.graph import Neo4jGraph


class HybridRetriever:
    """Retrieves relevant context using vector search + graph expansion."""

    def __init__(self, graph: Neo4jGraph) -> None:
        self._graph = graph

    async def retrieve(
        self,
        query_embedding: list[float],
        top_k: int = 20,
        hops: int = 2,
    ) -> RetrievalResult:
        """Execute hybrid retrieval pipeline.

        1. Vector search for top-K similar entities
        2. Expand neighborhoods via graph traversal
        3. Deduplicate and format context

        Args:
            query_embedding: Embedding of the user's question.
            top_k: Number of initial vector matches.
            hops: Graph traversal depth.

        Returns:
            RetrievalResult with entities, relationships, and formatted context.
        """
        # Step 1: Vector search
        vector_results = await self._graph.vector_search(query_embedding, top_k)

        if not vector_results:
            return RetrievalResult(
                entities=[],
                relationships=[],
                context_text="No relevant entities found in the knowledge graph.",
            )

        seed_entities = [entity for entity, _score in vector_results]
        scores = {entity.name: score for entity, score in vector_results}

        # Step 2: Graph expansion
        entity_names = [e.name for e in seed_entities]
        expanded_entities, expanded_rels = await self._graph.expand_neighborhood(
            entity_names, hops
        )

        # Step 3: Deduplicate
        all_entities = _deduplicate_entities(seed_entities + expanded_entities)
        all_rels = _deduplicate_relationships(expanded_rels)

        # Step 4: Format context
        context = _format_context(all_entities, all_rels)

        return RetrievalResult(
            entities=all_entities,
            relationships=all_rels,
            context_text=context,
            vector_scores=scores,
        )


def _deduplicate_entities(entities: list[Entity]) -> list[Entity]:
    """Deduplicate by name, keeping the one with the longest description."""
    seen: dict[str, Entity] = {}
    for e in entities:
        key = e.name.lower()
        if key not in seen or len(e.description) > len(seen[key].description):
            seen[key] = e
    return list(seen.values())


def _deduplicate_relationships(relationships: list[Relationship]) -> list[Relationship]:
    """Deduplicate by (source, target, type)."""
    seen: dict[tuple[str, str, str], Relationship] = {}
    for r in relationships:
        key = (r.source.lower(), r.target.lower(), r.relationship_type)
        if key not in seen:
            seen[key] = r
    return list(seen.values())


def _format_context(entities: list[Entity], relationships: list[Relationship]) -> str:
    """Format entities and relationships as structured text for LLM context."""
    lines = []

    # Group relationships by source entity
    rel_by_source: dict[str, list[Relationship]] = {}
    for r in relationships:
        rel_by_source.setdefault(r.source, []).append(r)

    for entity in entities:
        lines.append(f"Entity: {entity.name} ({entity.entity_type}) — {entity.description}")

        for rel in rel_by_source.get(entity.name, []):
            lines.append(f"  → {rel.relationship_type} → {rel.target} — {rel.description}")

        lines.append("")

    return "\n".join(lines)
