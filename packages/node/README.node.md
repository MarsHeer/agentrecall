# agentrecall

Plug-and-play persistent memory for AI agents. TypeScript/Node.js SDK.

## Install

```bash
npm install agentrecall
```

## Quick Start

```typescript
import { MemoryStore } from "agentrecall";

const store = new MemoryStore();

// Your agent stores what it learns
await store.remember("User prefers dark mode", { agent: "assistant" });

// Next session — it still knows
const memories = await store.recall("What theme should I use?", {
  agent: "assistant",
});
```

## Features

- **Semantic Recall** — hybrid scoring with embeddings (optional)
- **Auto-Classification** — memories tagged as preferences, corrections, facts, temporal
- **Confidence Decay** — memories fade unless reinforced
- **Skip/Penalty** — mark irrelevant memories to reduce recall score
- **SQLite** — zero config, works offline, single file

## With Embeddings

Pass an embedding function for semantic search:

```typescript
import { MemoryStore } from "agentrecall";

const store = new MemoryStore({
  embed: async (text) => {
    // Use OpenAI, Cohere, or any embedding API
    const res = await fetch("https://api.openai.com/v1/embeddings", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ model: "text-embedding-3-small", input: text }),
    });
    const data = await res.json();
    return data.data[0].embedding;
  },
});
```

Without embeddings, recall uses confidence + recency scoring.

## API

### `new MemoryStore(options?)`

- `dbPath?: string` — custom SQLite path (default: `~/.agentrecall/memories.db`)
- `embed?: (text: string) => Promise<number[]>` — embedding function

### `store.remember(content, options?)`

Store a memory. Returns the created `Memory`.

- `agent?: string` — agent identifier (default: `"default"`)
- `category?: string` — auto-classified if omitted
- `importance?: string` — `"high"`, `"medium"`, `"low"`
- `metadata?: Record<string, unknown>` — custom metadata

### `store.recall(query, options?)`

Find relevant memories. Returns `RecallResult[]` with scores.

- `agent?: string` — filter by agent
- `category?: string` — filter by category
- `limit?: number` — max results (default: 5)
- `min_score?: number` — minimum score threshold

### `store.skip(id)` / `store.unskip(id)`

Mark/unmark a memory as skipped (reduces recall score).

### `store.delete(id)`

Delete a memory permanently.

### `store.count(agent?)`

Count memories, optionally filtered by agent.

### `store.wipe(options?)`

Delete memories. Filter by `agent` and/or `category`.

## License

MIT
