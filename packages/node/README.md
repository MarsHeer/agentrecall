# agentrecall — Node.js SDK

Plug-and-play persistent memory for AI agents. SQLite-backed with optional semantic search via embeddings.

## Installation

```bash
npm install agentrecall-ai-sdk
```

## Quick Start

```typescript
import { MemoryStore } from "agentrecall-ai-sdk";

const store = new MemoryStore({ dbPath: "~/.agentrecall/memories.db" });

// Store a memory
await store.remember("User prefers dark mode", { agent: "my-app" });

// Recall memories
const results = await store.recall("UI preferences", { agent: "my-app" });

store.close();
```

## Constructor

```typescript
new MemoryStore(options?: MemoryStoreOptions)
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| dbPath | string | `~/.agentrecall/memories.db` | Path to SQLite database file |
| embed | EmbeddingFunction | null | Async function `(text: string) => Promise<number[]>` for semantic search |
| decay_rate | number | 0.01 | Confidence decay rate per recall (0–1) |
| min_confidence | number | 0.1 | Memories below this confidence are auto-deleted |

## Core Methods

### `remember(content, options?) → Promise<Memory>`

Store a memory. Auto-classifies if category not provided.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| content | string | required | The memory text (non-empty) |
| agent | string | "default" | Agent identifier |
| category | string | auto-classified | preference, correction, temporal, factual, general |
| importance | string | "medium" | "high", "medium", "low" |
| metadata | object | {} | Custom key-value pairs |

### `recall(query, options?) → Promise<RecallResult[]>`

Find relevant memories. Runs confidence decay before scoring. Hybrid scoring: `similarity × confidence × importance_weight × recency × skip_penalty`.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| query | string | required | Search query (non-empty) |
| agent | string | "default" | Filter by agent |
| category | string | none | Filter by category |
| limit | number | 5 | Max results |
| min_score | number | 0.0 | Minimum score threshold |

### `get(id) → Memory | undefined`

Get a single memory by ID. Returns `undefined` if not found.

### `update(id, content) → void`

Update a memory's content. Content must be non-empty.

### `delete(id) → void`

Delete a memory permanently.

### `skip(id) → void`

Mark a memory as skipped (reduces recall score by 80%).

### `unskip(id) → void`

Unmark a skipped memory.

### `count(agent?) → number`

Count memories, optionally filtered by agent.

### `wipe(options?) → void`

Delete memories. Filter by agent and/or category. If no filters, delete ALL.

### `close() → void`

Close database connection.

## Data Model

### Memory

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| id | number | auto | Auto-increment primary key |
| content | string | required | The memory text |
| category | string | auto | preference, correction, temporal, factual, general |
| agent | string | "default" | Agent identifier |
| importance | string | "medium" | high, medium, low |
| confidence | number | 1.0 | Decays over time |
| skipped | boolean | false | Penalized in recall |
| access_count | number | 0 | Incremented on recall |
| created_at | string | now | Creation timestamp (ISO) |
| updated_at | string | now | Last update timestamp (ISO) |
| metadata | object | {} | Custom data |
| embedding | number[] \| null | null | Persisted in SQLite as BLOB |

### RecallResult

Extends Memory with:

| Field | Type | Description |
|-------|------|-------------|
| score | number | Composite relevance score |

## Classification Rules

| Category | Trigger Patterns |
|----------|-----------------|
| correction | actually, in fact, correction, wrong, not quite, instead, should be, meant to, I meant, don't, never, stop |
| preference | prefer, like, love, hate, favorite, best, worst, always, never use, do not use, use instead, switch to, my style, I want, keep it |
| temporal | yesterday, today, tomorrow, last week/month/year, next week/month/year, ago, recently, deadline, reminder, schedule, YYYY-MM-DD dates |
| factual | is, are, was, were, has, have, had, located, found, based, lives |
| general | Fallback for anything unclassified |

## Scoring Algorithm

```
score = similarity × confidence × importance_weight × recency × skip_penalty
```

- **similarity**: Cosine similarity of embeddings (1.0 if no embeddings, 0 if either vector is missing)
- **confidence**: Memory confidence (starts at 1.0, decays per recall)
- **importance_weight**: high: 1.3, medium: 1.0, low: 0.7
- **recency**: `1 / (1 + days_since_creation × 0.05)`
- **skip_penalty**: skipped: 0.2, not skipped: 1.0

## Confidence Decay

On each `recall()`, all memories are decayed:

```
new_confidence = confidence × (1 - decay_rate)
```

- Default `decay_rate` = 0.01 per recall
- Memories below `min_confidence` (default 0.1) are auto-deleted

## Error Handling

- Empty content → throws `Error("Content cannot be empty")`
- Operations on closed store → throws `Error("Store is closed")`
- Invalid IDs → returns `undefined` (get) or no-op (delete, skip, update)
- Embedding function failure → falls back to confidence+recency scoring, logs warning
