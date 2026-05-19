# AgentRecall — Unified API Spec

Both Python and Node.js SDKs MUST implement this exact API surface.
This is the contract. Deviations are bugs.

## Constructor

```python
# Python
store = MemoryStore(db_path="agentrecall.db")  # optional
```
```typescript
// Node.js
const store = new MemoryStore({ dbPath: "~/.agentrecall/memories.db" });  // optional
```

## Core Methods

### `remember(content, options?) -> Memory`

Store a memory. Auto-classifies if category not provided.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| content | string | required | The memory text |
| agent | string | "default" | Agent identifier |
| category | string | auto-classified | preference, correction, temporal, factual, general |
| importance | string | "medium" | "high", "medium", "low" |
| metadata | dict/object | {} | Custom key-value pairs |

Returns: `Memory` object.

### `recall(query, options?) -> RecallResult[]`

Find relevant memories. Hybrid scoring: semantic similarity × confidence × importance × recency.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| query | string | required | Search query |
| agent | string | "default" | Filter by agent |
| category | string | none | Filter by category |
| limit | int | 5 | Max results |
| min_score | float | 0.0 | Minimum score threshold |

Returns: list/array of `RecallResult` (Memory + score).

### `get(id) -> Memory | None`

Get a single memory by ID. Returns null/None if not found.

### `update(id, content) -> void`

Update a memory's content.

### `delete(id) -> void`

Delete a memory permanently.

### `skip(id) -> void`

Mark a memory as skipped (reduces recall score by 80%).

### `unskip(id) -> void`

Unmark a skipped memory.

### `count(agent?) -> int`

Count memories, optionally filtered by agent.

### `wipe(options?) -> void`

Delete memories. Filter by agent and/or category. If no filters, delete ALL.

### `close() -> void`

Close database connection. Python: also support `with` statement.

## Data Model

### Memory

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| id | int | auto | Auto-increment primary key |
| content | string | required | The memory text |
| category | string | auto | preference, correction, temporal, factual, general |
| agent | string | "default" | Agent identifier |
| importance | string | "medium" | high, medium, low |
| confidence | float | 1.0 | Decays over time |
| skipped | bool | false | penalized in recall |
| access_count | int | 0 | Incremented on recall |
| created_at | ISO string | now | Creation timestamp |
| updated_at | ISO string | now | Last update timestamp |
| metadata | dict/object | {} | Custom data |
| embedding | float[] | null | Persisted in SQLite as BLOB |
| ai_processed | bool | false | Whether AI has processed this memory |
| summary | string | "" | AI-generated summary of the memory |
| keywords | string[] | [] | Extracted keywords |
| entities | list | [] | Entities extracted (populated on graph endpoints) |
| relationships | list | [] | Relationships extracted (populated on graph endpoints) |

### RecallResult

Extends Memory with:
| Field | Type | Notes |
|-------|------|-------|
| score | float | Composite relevance score |

## Classification Rules (MUST be identical)

Categories and their trigger patterns:

**correction**: actually, in fact, correction, wrong, not quite, instead, should be, meant to, I meant, don't, never, stop

**preference**: prefer, like, love, hate, favorite, best, worst, always, never use, do not use, use instead, switch to, my style, I want, keep it

**temporal**: yesterday, today, tomorrow, last week/month/year, next week/month/year, ago, recently, deadline, reminder, schedule, YYYY-MM-DD dates

**factual**: is, are, was, were, has, have, had, located, found, based, lives

**general**: fallback for anything unclassified

## Scoring Algorithm (MUST be identical)

```
score = similarity × confidence × importance_weight × recency × skip_penalty
```

Where:
- `similarity` = cosine similarity of embeddings (1.0 if no embeddings)
- `confidence` = memory.confidence (starts at 1.0, decays)
- `importance_weight` = high: 1.3, medium: 1.0, low: 0.7
- `recency` = 1 / (1 + days_since_creation × 0.05)
- `skip_penalty` = skipped: 0.2, not skipped: 1.0

## Confidence Decay

Run periodically (or on each recall). Formula:
```
new_confidence = confidence × (1 - decay_rate)
```
Default `decay_rate` = 0.01 per day.
Memories below `min_confidence` (default 0.1) are auto-deleted.

## Graph Memory API (Cloud Pro)

All graph endpoints require Bearer authentication and are scoped by `agent_id`.
These endpoints are available on Cloud Pro plans with Neo4j-backed graph storage.

### `GET /v1/graph/entities`

List all entities in the knowledge graph for an agent.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| agent_id | int | required | Agent ID |
| type | string | none | Filter by entity type |
| limit | int | 50 | Max results |

Returns: `[{name, type, memory_count, first_seen, last_seen}]`

**Example:**
```
GET /v1/graph/entities?agent_id=1&type=Person&limit=20
Authorization: Bearer sk_...
```

### `GET /v1/graph/entities/{entity_name}/neighbors`

Get neighboring entities connected to a specific entity.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| entity_name | string | required | Name of the entity (in URL path) |
| agent_id | int | required | Agent ID |
| depth | int | 1 | Traversal depth (1-5) |

Returns: `{entity: {name, type, memory_count, first_seen, last_seen}, neighbors: [{name, type, relationship_type, strength, distance}]}`

**Example:**
```
GET /v1/graph/entities/Alice/neighbors?agent_id=1&depth=2
Authorization: Bearer sk_...
```

### `GET /v1/graph/relationships`

List relationships between entities in the graph.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| agent_id | int | required | Agent ID |
| source | string | none | Filter by source entity name |
| target | string | none | Filter by target entity name |
| limit | int | 50 | Max results |

Returns: `[{source, target, relation_type, memory_ids, strength}]`

**Example:**
```
GET /v1/graph/relationships?agent_id=1&source=Alice&limit=20
Authorization: Bearer sk_...
```

### `GET /v1/graph/paths`

Find the shortest path between two entities in the graph.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| agent_id | int | required | Agent ID |
| from | string | required | Source entity name |
| to | string | required | Target entity name |
| max_depth | int | 5 | Maximum path length |

Returns: `{path: [{entity: {name, type}, relationship: {relationship_type}}], length: int}`

**Example:**
```
GET /v1/graph/paths?agent_id=1&from=Alice&to=Bob&max_depth=5
Authorization: Bearer sk_...
```

### `GET /v1/graph/stats`

Get statistics about the knowledge graph for an agent.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| agent_id | int | required | Agent ID |

Returns: `{total_entities, total_relationships, total_memories_in_graph, entity_types: {type: count}, top_entities: [{name, connections}]}`

**Example:**
```
GET /v1/graph/stats?agent_id=1
Authorization: Bearer sk_...
```

### `GET /v1/graph/context`

Retrieve graph context relevant to a natural language query. Finds related entities, their memories, and connected entities.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| agent_id | int | required | Agent ID |
| query | string | required | Natural language query |
| limit | int | 10 | Max results |

Returns: `{results: [{entity: {name, type, ...}, memories: [{summary, memory_id}], connected_entities: [{name, type, relationship}]}]}`

**Example:**
```
GET /v1/graph/context?agent_id=1&query=What+does+Alice+think+about+Bob&limit=5
Authorization: Bearer sk_...
```

## SQLite Schema (MUST be identical)

```sql
CREATE TABLE memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'general',
  agent TEXT NOT NULL DEFAULT 'default',
  importance TEXT NOT NULL DEFAULT 'medium',
  confidence REAL NOT NULL DEFAULT 1.0,
  skipped INTEGER NOT NULL DEFAULT 0,
  access_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  metadata TEXT NOT NULL DEFAULT '{}',
  embedding BLOB
);

CREATE INDEX idx_memories_agent ON memories(agent);
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_skipped ON memories(skipped);
```

Note: Python stores embedding as JSON array in BLOB. Node.js stores as Buffer.
Both must be able to read the other's format.

## Error Handling

- Invalid IDs: return None/null (get), no-op (delete, skip, update)
- Empty content: raise ValueError / throw Error
- Closed store: raise RuntimeError / throw Error
- Embedding function failure: fall back to confidence+recency scoring, log warning
