"""Neo4j graph database adapter for kgraph.

Handles all Neo4j operations: connection, index creation,
entity/relationship ingestion, and retrieval queries.
"""

from __future__ import annotations

from typing import Any

from neo4j import AsyncGraphDatabase

from kgraph.domain.models import Entity, Relationship


class Neo4jGraph:
    """Neo4j adapter implementing the GraphRepository protocol."""

    def __init__(self, uri: str, username: str, password: str) -> None:
        self._driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

    async def close(self) -> None:
        """Close the database connection."""
        await self._driver.close()

    async def verify_connection(self) -> bool:
        """Test the Neo4j connection. Returns True if successful."""
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def ensure_indexes(self, vector_dimensions: int = 1536) -> None:
        """Create required indexes and constraints.

        Args:
            vector_dimensions: Dimensionality of embedding vectors.
        """
        async with self._driver.session() as session:
            # Uniqueness constraint on entity name
            await session.run(
                "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.name IS UNIQUE"
            )

            # Vector index for similarity search
            await session.run(
                "CREATE VECTOR INDEX entity_embedding IF NOT EXISTS "
                "FOR (e:Entity) ON (e.embedding) "
                "OPTIONS {indexConfig: {"
                f"  `vector.dimensions`: {vector_dimensions},"
                "  `vector.similarity_function`: 'cosine'"
                "}}"
            )

            # Full-text index for name/description search
            await session.run(
                "CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS "
                "FOR (e:Entity) ON EACH [e.name, e.description]"
            )

    async def ingest_entities(self, entities: list[Entity], batch_size: int = 10_000) -> int:
        """Batch ingest entities using UNWIND + MERGE.

        Returns:
            Count of entities written.
        """
        if not entities:
            return 0

        count = 0
        for i in range(0, len(entities), batch_size):
            batch = entities[i : i + batch_size]
            params = [
                {
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "description": e.description,
                    "source": e.source,
                    "embedding": e.embedding,
                }
                for e in batch
            ]

            async with self._driver.session() as session:
                result = await session.run(
                    """
                    UNWIND $entities AS e
                    MERGE (n:Entity {name: e.name})
                    ON CREATE SET
                        n.entity_type = e.entity_type,
                        n.description = e.description,
                        n.source = e.source,
                        n.embedding = e.embedding
                    ON MATCH SET
                        n.description = CASE
                            WHEN size(e.description) > size(n.description)
                            THEN e.description ELSE n.description END,
                        n.embedding = CASE
                            WHEN n.embedding IS NULL THEN e.embedding
                            ELSE n.embedding END
                    RETURN count(n) AS written
                    """,
                    entities=params,
                )
                record = await result.single()
                count += record["written"] if record else 0

        return count

    async def ingest_relationships(
        self, relationships: list[Relationship], batch_size: int = 10_000
    ) -> int:
        """Batch ingest relationships using UNWIND + MERGE.

        Returns:
            Count of relationships written.
        """
        if not relationships:
            return 0

        count = 0
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i : i + batch_size]
            params = [
                {
                    "source": r.source,
                    "target": r.target,
                    "rel_type": r.relationship_type,
                    "description": r.description,
                }
                for r in batch
            ]

            async with self._driver.session() as session:
                result = await session.run(
                    """
                    UNWIND $rels AS r
                    MATCH (s:Entity {name: r.source})
                    MATCH (t:Entity {name: r.target})
                    MERGE (s)-[rel:RELATES_TO {type: r.rel_type}]->(t)
                    SET rel.description = r.description,
                        rel.relationship_type = r.rel_type
                    RETURN count(rel) AS written
                    """,
                    rels=params,
                )
                record = await result.single()
                count += record["written"] if record else 0

        return count

    async def vector_search(
        self, embedding: list[float], top_k: int = 20
    ) -> list[tuple[Entity, float]]:
        """Find similar entities by vector similarity.

        Args:
            embedding: Query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of (Entity, score) tuples sorted by similarity.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                CALL db.index.vector.queryNodes('entity_embedding', $top_k, $embedding)
                YIELD node, score
                RETURN node.name AS name,
                       node.entity_type AS entity_type,
                       node.description AS description,
                       node.source AS source,
                       score
                """,
                top_k=top_k,
                embedding=embedding,
            )
            records = [record async for record in result]

        return [
            (
                Entity(
                    name=r["name"],
                    entity_type=r["entity_type"],
                    description=r["description"],
                    source=r["source"] or "",
                ),
                r["score"],
            )
            for r in records
        ]

    async def expand_neighborhood(
        self, entity_names: list[str], hops: int = 2
    ) -> tuple[list[Entity], list[Relationship]]:
        """Expand entity neighborhoods by graph traversal.

        Args:
            entity_names: Starting entity names.
            hops: Number of hops to traverse.

        Returns:
            Tuple of (entities, relationships) in the expanded neighborhood.
        """
        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH (start:Entity)
                WHERE start.name IN $names
                CALL apoc.path.subgraphAll(start, {{maxLevel: {hops}}})
                YIELD nodes, relationships
                UNWIND nodes AS n
                WITH COLLECT(DISTINCT n) AS all_nodes,
                     COLLECT(DISTINCT relationships) AS all_rels_nested
                UNWIND all_nodes AS node
                WITH node, all_rels_nested
                UNWIND all_rels_nested AS rels
                UNWIND rels AS rel
                RETURN
                    COLLECT(DISTINCT {{
                        name: node.name,
                        entity_type: node.entity_type,
                        description: node.description,
                        source: node.source
                    }}) AS entities,
                    COLLECT(DISTINCT {{
                        source: startNode(rel).name,
                        target: endNode(rel).name,
                        rel_type: rel.relationship_type,
                        description: rel.description
                    }}) AS relationships
                """,
                names=entity_names,
            )
            record = await result.single()

        if not record:
            return [], []

        entities = [
            Entity(
                name=e["name"],
                entity_type=e["entity_type"],
                description=e["description"] or "",
                source=e["source"] or "",
            )
            for e in record["entities"]
        ]

        relationships = [
            Relationship(
                source=r["source"],
                target=r["target"],
                relationship_type=r["rel_type"] or "RELATES_TO",
                description=r["description"] or "",
            )
            for r in record["relationships"]
        ]

        return entities, relationships

    async def fulltext_search(self, query: str, limit: int = 10) -> list[Entity]:
        """Search entities by name/description using full-text index."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                CALL db.index.fulltext.queryNodes('entity_fulltext', $query)
                YIELD node, score
                RETURN node.name AS name,
                       node.entity_type AS entity_type,
                       node.description AS description,
                       node.source AS source
                LIMIT $limit
                """,
                query=query,
                limit=limit,
            )
            records = [record async for record in result]

        return [
            Entity(
                name=r["name"],
                entity_type=r["entity_type"],
                description=r["description"] or "",
                source=r["source"] or "",
            )
            for r in records
        ]

    async def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (n:Entity)
                WITH count(n) AS node_count
                MATCH ()-[r]->()
                WITH node_count, count(r) AS rel_count
                RETURN node_count, rel_count
                """
            )
            record = await result.single()

        if not record:
            return {"nodes": 0, "relationships": 0}

        return {
            "nodes": record["node_count"],
            "relationships": record["rel_count"],
        }
