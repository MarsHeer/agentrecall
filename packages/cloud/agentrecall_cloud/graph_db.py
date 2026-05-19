"""Neo4j graph database connection and operations.

Provides async Neo4j driver management with graceful degradation.
If Neo4j is not configured or unavailable, all graph operations silently skip
and log warnings instead of crashing.
"""

import logging
from typing import Optional, Any
from datetime import datetime, timezone

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError, ClientError

from agentrecall_cloud.config import config

logger = logging.getLogger(__name__)

_driver: Optional[AsyncDriver] = None
_initialized = False
_available = False


async def init_graph_db() -> None:
    """Initialize the Neo4j async driver and create constraints.

    Gracefully skips if Neo4j is not configured or unavailable.
    """
    global _driver, _initialized, _available

    if _initialized:
        return

    if not config.neo4j_uri or not config.neo4j_password:
        logger.warning(
            "Neo4j not configured (NEO4J_URI or NEO4J_PASSWORD empty). "
            "Graph features disabled."
        )
        _initialized = True
        return

    try:
        _driver = AsyncGraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
            connection_timeout=5,
            max_transaction_retry_time=5,
        )
        # Verify connectivity
        await _driver.verify_connectivity()

        # Create constraints
        async with _driver.session() as session:
            await session.run(
                "CREATE CONSTRAINT entity_name_agent IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE (e.name, e.agent_id) IS UNIQUE"
            )
            await session.run(
                "CREATE CONSTRAINT memory_id_agent IF NOT EXISTS "
                "FOR (m:Memory) REQUIRE (m.memory_id, m.agent_id) IS UNIQUE"
            )

        _available = True
        _initialized = True
        logger.info("Neo4j graph database initialized successfully")

    except (ServiceUnavailable, AuthError, ClientError, Exception) as e:
        logger.warning(
            "Neo4j connection failed: %s. Graph features disabled.", e
        )
        _driver = None
        _available = True  # Mark as initialized but unavailable
        _initialized = True


async def close_graph_db() -> None:
    """Close the Neo4j driver."""
    global _driver, _initialized, _available
    if _driver:
        try:
            await _driver.close()
        except Exception:
            pass
        _driver = None
    _initialized = False
    _available = False
    logger.info("Neo4j driver closed")


def is_available() -> bool:
    """Check if Neo4j is configured and available."""
    return _driver is not None and _available


def get_session() -> Optional[AsyncSession]:
    """Get a Neo4j async session if available, else None."""
    if _driver is None:
        return None
    return _driver.session()


async def sync_memory_to_graph(
    memory_id: int,
    content: str,
    agent_id: str,
    entities: list[dict],
    relationships: list[dict],
    summary: str = "",
) -> None:
    """Write entities and relationships from a memory to the Neo4j graph.

    All nodes are scoped by agent_id. Silently skips if Neo4j is unavailable.
    """
    if _driver is None:
        return

    now = datetime.now(timezone.utc).isoformat()
    driver = _driver

    try:
        async with driver.session() as s:
            # Create the Memory node
            content_summary = summary or content[:200]
            await s.run(
                """
                MERGE (mem:Memory {memory_id: $memory_id, agent_id: $agent_id})
                SET mem.content_summary = $content_summary,
                    mem.created_at = $created_at
                """,
                memory_id=memory_id,
                agent_id=agent_id,
                content_summary=content_summary,
                created_at=now,
            )

            # Create Entity nodes and EXTRACTED_FROM relationships
            for ent in entities:
                name = ent.get("name", "").strip()
                ent_type = ent.get("type", "concept").strip()
                if not name:
                    continue
                await s.run(
                    """
                    MERGE (e:Entity {name: $name, agent_id: $agent_id})
                    ON CREATE SET e.type = $ent_type,
                                  e.first_seen = $now,
                                  e.last_seen = $now
                    ON MATCH SET e.last_seen = $now
                    """,
                    name=name,
                    agent_id=agent_id,
                    ent_type=ent_type,
                    now=now,
                )
                # Link entity to memory
                await s.run(
                    """
                    MATCH (e:Entity {name: $name, agent_id: $agent_id})
                    MATCH (m:Memory {memory_id: $memory_id, agent_id: $agent_id})
                    MERGE (e)-[r:EXTRACTED_FROM]->(m)
                    """,
                    name=name,
                    agent_id=agent_id,
                    memory_id=memory_id,
                )

            # Create relationships between entities
            for rel in relationships:
                source = rel.get("source", "").strip()
                target = rel.get("target", "").strip()
                rel_type_raw = rel.get("type", rel.get("relation_type", "RELATED_TO"))
                rel_type = rel_type_raw.strip().upper().replace(" ", "_")
                if not source or not target:
                    continue

                # Sanitize relationship type for Neo4j (must be valid identifier)
                rel_type = "".join(c if c.isalnum() or c == "_" else "_" for c in rel_type)
                if not rel_type:
                    rel_type = "RELATED_TO"

                await s.run(
                    f"""
                    MERGE (s:Entity {{name: $source, agent_id: $agent_id}})
                    MERGE (t:Entity {{name: $target, agent_id: $agent_id}})
                    MERGE (s)-[r:{rel_type}]->(t)
                    SET r.memory_ids = CASE
                        WHEN r.memory_ids IS NULL THEN [$memory_id]
                        ELSE CASE WHEN $memory_id IN r.memory_ids THEN r.memory_ids
                             ELSE r.memory_ids + $memory_id END
                    END,
                    r.strength = CASE
                        WHEN r.strength IS NULL THEN 1.0
                        ELSE r.strength + 1.0
                    END
                    """,
                    source=source,
                    target=target,
                    agent_id=agent_id,
                    memory_id=memory_id,
                )

            logger.debug(
                "Synced memory %d to graph: %d entities, %d relationships",
                memory_id,
                len(entities),
                len(relationships),
            )

    except Exception as e:
        logger.warning("Failed to sync memory %d to graph: %s", memory_id, e)


# ─── Graph Query Functions ────────────────────────────────────────────


async def get_entities(
    agent_id: str,
    entity_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List all entities for an agent, optionally filtered by type."""
    if _driver is None:
        return []
    driver = _driver

    try:
        async with driver.session() as s:
            if entity_type:
                result = await s.run(
                    """
                    MATCH (e:Entity {agent_id: $agent_id})
                    WHERE e.type = $entity_type
                    OPTIONAL MATCH (e)-[:EXTRACTED_FROM]->(m:Memory)
                    RETURN e.name AS name, e.type AS type,
                           e.first_seen AS first_seen, e.last_seen AS last_seen,
                           COUNT(DISTINCT m) AS memory_count
                    ORDER BY memory_count DESC
                    LIMIT $limit
                    """,
                    agent_id=agent_id,
                    entity_type=entity_type,
                    limit=limit,
                )
            else:
                result = await s.run(
                    """
                    MATCH (e:Entity {agent_id: $agent_id})
                    OPTIONAL MATCH (e)-[:EXTRACTED_FROM]->(m:Memory)
                    RETURN e.name AS name, e.type AS type,
                           e.first_seen AS first_seen, e.last_seen AS last_seen,
                           COUNT(DISTINCT m) AS memory_count
                    ORDER BY memory_count DESC
                    LIMIT $limit
                    """,
                    agent_id=agent_id,
                    limit=limit,
                )
            records = await result.data()
            return [
                {
                    "name": r["name"],
                    "type": r["type"],
                    "memory_count": r["memory_count"],
                    "first_seen": r["first_seen"],
                    "last_seen": r["last_seen"],
                }
                for r in records
            ]
    except Exception as e:
        logger.warning("Graph query failed (get_entities): %s", e)
        return []


async def get_entity_neighbors(
    agent_id: str,
    entity_name: str,
    depth: int = 1,
) -> dict:
    """Find entities connected to a given entity (BFS up to depth)."""
    if _driver is None:
        return {"entity": None, "neighbors": []}
    driver = _driver

    try:
        async with driver.session() as s:
            # First, get the entity itself
            entity_result = await s.run(
                """
                MATCH (e:Entity {name: $name, agent_id: $agent_id})
                OPTIONAL MATCH (e)-[:EXTRACTED_FROM]->(m:Memory)
                RETURN e.name AS name, e.type AS type,
                       e.first_seen AS first_seen, e.last_seen AS last_seen,
                       COUNT(DISTINCT m) AS memory_count
                """,
                name=entity_name,
                agent_id=agent_id,
            )
            entity_record = await entity_result.single()
            if not entity_record:
                return {"entity": None, "neighbors": []}

            entity_info = {
                "name": entity_record["name"],
                "type": entity_record["type"],
                "memory_count": entity_record["memory_count"],
                "first_seen": entity_record["first_seen"],
                "last_seen": entity_record["last_seen"],
            }

            # BFS traversal for neighbors
            depth = max(1, min(depth, 5))
            neighbor_result = await s.run(
                """
                MATCH (e:Entity {name: $name, agent_id: $agent_id})
                CALL {
                    WITH e
                    MATCH path = (e)-[r*1..$depth]-(neighbor:Entity)
                    WHERE neighbor.agent_id = $agent_id
                    WITH neighbor, relationships(path) AS rels,
                         length(path) AS dist
                    UNWIND rels AS rel
                    RETURN DISTINCT
                        neighbor.name AS name,
                        neighbor.type AS type,
                        type(rels[0]) AS relationship_type,
                        1.0 / dist AS strength,
                        dist AS distance
                }
                RETURN name, type, relationship_type, strength, distance
                ORDER BY distance, strength DESC
                """,
                name=entity_name,
                agent_id=agent_id,
                depth=depth,
            )
            records = await neighbor_result.data()

            neighbors = []
            for r in records:
                neighbors.append({
                    "name": r["name"],
                    "type": r["type"],
                    "relationship_type": r["relationship_type"],
                    "strength": r["strength"],
                    "distance": r["distance"],
                })

            return {"entity": entity_info, "neighbors": neighbors}

    except Exception as e:
        logger.warning("Graph query failed (get_entity_neighbors): %s", e)
        return {"entity": None, "neighbors": []}


async def get_relationships(
    agent_id: str,
    source: Optional[str] = None,
    target: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List relationships, optionally filtered by source/target."""
    if _driver is None:
        return []
    driver = _driver

    try:
        async with driver.session() as s:
            # We need to query all relationship types dynamically
            # First get all relationship types for this agent
            type_result = await s.run(
                """
                MATCH (s:Entity {agent_id: $agent_id})-[r]->(t:Entity {agent_id: $agent_id})
                WHERE NOT type(r) IN ['EXTRACTED_FROM']
                RETURN DISTINCT type(r) AS rel_type
                """,
                agent_id=agent_id,
            )
            rel_types = [r["rel_type"] for r in await type_result.data()]

            if not rel_types:
                return []

            # Build a UNION query for each relationship type
            # to handle dynamic type names
            all_rels = []
            for rel_type in rel_types:
                # Sanitize: only allow alphanumeric and underscore
                safe_type = "".join(
                    c if c.isalnum() or c == "_" else "_"
                    for c in rel_type
                )
                if not safe_type:
                    continue

                conditions = ["s.agent_id = $agent_id", "t.agent_id = $agent_id"]
                params: dict[str, Any] = {"agent_id": agent_id, "limit": limit}

                if source:
                    conditions.append("s.name = $source")
                    params["source"] = source
                if target:
                    conditions.append("t.name = $target")
                    params["target"] = target

                where = " AND ".join(conditions)
                query = f"""
                    MATCH (s:Entity)-[r:{safe_type}]->(t:Entity)
                    WHERE {where}
                    RETURN s.name AS source, t.name AS target,
                           '{safe_type}' AS relation_type,
                           r.memory_ids AS memory_ids,
                           r.strength AS strength
                    LIMIT $limit
                """
                result = await s.run(query, **params)  # type: ignore[arg-type]
                records = await result.data()
                for r in records:
                    all_rels.append({
                        "source": r["source"],
                        "target": r["target"],
                        "relation_type": r["relation_type"],
                        "memory_ids": r.get("memory_ids", []),
                        "strength": r.get("strength", 1.0),
                    })

            # Sort by strength descending and apply limit
            all_rels.sort(key=lambda x: x["strength"], reverse=True)
            return all_rels[:limit]

    except Exception as e:
        logger.warning("Graph query failed (get_relationships): %s", e)
        return []


async def find_shortest_path(
    agent_id: str,
    from_entity: str,
    to_entity: str,
    max_depth: int = 5,
) -> dict:
    """Find shortest path between two entities."""
    if _driver is None:
        return {"path": [], "length": 0}
    driver = _driver

    max_depth = max(1, min(max_depth, 10))

    try:
        async with driver.session() as s:
            result = await s.run(
                """
                MATCH (start:Entity {name: $from_name, agent_id: $agent_id})
                MATCH (end:Entity {name: $to_name, agent_id: $agent_id})
                MATCH path = shortestPath(
                    (start)-[*1..$max_depth]-(end)
                )
                RETURN [n IN nodes(path) | {
                    name: n.name,
                    type: n.type
                }] AS entities,
                [r IN relationships(path) | {
                    relationship_type: type(r)
                }] AS relationships,
                length(path) AS path_length
                """,
                from_name=from_entity,
                to_name=to_entity,
                agent_id=agent_id,
                max_depth=max_depth,
            )
            record = await result.single()
            if not record:
                return {"path": [], "length": 0}

            path_items = []
            entities = record["entities"]
            relationships = record["relationships"]
            for i, ent in enumerate(entities):
                item = {"entity": ent}
                if i < len(relationships):
                    item["relationship"] = relationships[i]
                path_items.append(item)

            return {
                "path": path_items,
                "length": record["path_length"],
            }

    except Exception as e:
        logger.warning("Graph query failed (find_shortest_path): %s", e)
        return {"path": [], "length": 0}


async def get_graph_stats(agent_id: str) -> dict:
    """Get graph statistics for an agent."""
    if _driver is None:
        return {
            "total_entities": 0,
            "total_relationships": 0,
            "total_memories_in_graph": 0,
            "entity_types": {},
            "top_entities": [],
        }
    driver = _driver

    try:
        async with driver.session() as s:
            # Count entities
            ent_result = await s.run(
                """
                MATCH (e:Entity {agent_id: $agent_id})
                RETURN count(e) AS total
                """,
                agent_id=agent_id,
            )
            ent_record = await ent_result.single()
            total_entities = ent_record["total"] if ent_record else 0

            # Count relationships (non-EXTRACTED_FROM)
            rel_result = await s.run(
                """
                MATCH (s:Entity {agent_id: $agent_id})-[r]->(t:Entity {agent_id: $agent_id})
                WHERE NOT type(r) = 'EXTRACTED_FROM'
                RETURN count(r) AS total
                """,
                agent_id=agent_id,
            )
            rel_record = await rel_result.single()
            total_relationships = rel_record["total"] if rel_record else 0

            # Count memories in graph
            mem_result = await s.run(
                """
                MATCH (m:Memory {agent_id: $agent_id})
                RETURN count(m) AS total
                """,
                agent_id=agent_id,
            )
            mem_record = await mem_result.single()
            total_memories = mem_record["total"] if mem_record else 0

            # Entity type distribution
            type_result = await s.run(
                """
                MATCH (e:Entity {agent_id: $agent_id})
                RETURN e.type AS type, count(e) AS cnt
                ORDER BY cnt DESC
                """,
                agent_id=agent_id,
            )
            type_records = await type_result.data()
            entity_types = {r["type"]: r["cnt"] for r in type_records}

            # Top entities by connections
            top_result = await s.run(
                """
                MATCH (e:Entity {agent_id: $agent_id})
                OPTIONAL MATCH (e)-[r]-(other:Entity {agent_id: $agent_id})
                WHERE NOT type(r) = 'EXTRACTED_FROM'
                RETURN e.name AS name, count(DISTINCT other) AS connections
                ORDER BY connections DESC
                LIMIT 10
                """,
                agent_id=agent_id,
            )
            top_records = await top_result.data()
            top_entities = [
                {"name": r["name"], "connections": r["connections"]}
                for r in top_records
            ]

            return {
                "total_entities": total_entities,
                "total_relationships": total_relationships,
                "total_memories_in_graph": total_memories,
                "entity_types": entity_types,
                "top_entities": top_entities,
            }

    except Exception as e:
        logger.warning("Graph query failed (get_graph_stats): %s", e)
        return {
            "total_entities": 0,
            "total_relationships": 0,
            "total_memories_in_graph": 0,
            "entity_types": {},
            "top_entities": [],
        }


async def get_graph_context(
    agent_id: str,
    query: str,
    limit: int = 10,
) -> list[dict]:
    """Smart context retrieval: find relevant entities and connected memories.

    Extracts entity-like keywords from the query, traverses the graph to find
    matching entities and their connected memories.
    """
    if _driver is None:
        return []
    driver = _driver

    # Simple keyword extraction from query
    stop_words = {
        "the", "a", "an", "is", "was", "are", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "need", "dare", "ought", "used", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between",
        "and", "but", "or", "nor", "not", "so", "yet", "both",
        "what", "which", "who", "whom", "this", "that", "these",
        "those", "i", "me", "my", "we", "our", "you", "your",
        "he", "him", "his", "she", "her", "it", "its", "they",
        "them", "their", "about", "how", "when", "where", "why",
        "if", "then", "else", "just", "also", "too", "very",
    }

    words = [
        w.strip().lower()
        for w in query.split()
        if len(w.strip()) > 2 and w.strip().lower() not in stop_words
    ]

    if not words:
        return []

    try:
        async with driver.session() as s:
            # Find entities matching any word in the query (case-insensitive)
            # and their connected memories
            result = await s.run(
                """
                MATCH (e:Entity {agent_id: $agent_id})
                WHERE ANY(word IN $words WHERE toLower(e.name) CONTAINS word)
                OPTIONAL MATCH (e)-[:EXTRACTED_FROM]->(m:Memory)
                OPTIONAL MATCH (e)-[r]-(connected:Entity {agent_id: $agent_id})
                WHERE NOT type(r) = 'EXTRACTED_FROM'
                WITH e, COLLECT(DISTINCT m) AS memories,
                     COLLECT(DISTINCT {
                         name: connected.name,
                         type: connected.type,
                         relationship: type(r)
                     }) AS connected_entities
                RETURN e.name AS name, e.type AS type,
                       e.first_seen AS first_seen, e.last_seen AS last_seen,
                       [mem IN memories | {
                           memory_id: mem.memory_id,
                           summary: mem.content_summary
                       }] AS memories,
                       connected_entities
                LIMIT $limit
                """,
                agent_id=agent_id,
                words=words,
                limit=limit,
            )
            records = await result.data()

            return [
                {
                    "entity": {
                        "name": r["name"],
                        "type": r["type"],
                        "first_seen": r["first_seen"],
                        "last_seen": r["last_seen"],
                    },
                    "memories": r.get("memories", []),
                    "connected_entities": r.get("connected_entities", []),
                }
                for r in records
            ]

    except Exception as e:
        logger.warning("Graph query failed (get_graph_context): %s", e)
        return []
