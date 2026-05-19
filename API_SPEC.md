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
