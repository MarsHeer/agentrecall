# AgentRecall

Plug-and-play persistent memory for AI agents. Open source, zero config.

**Python** · **Node.js** · Local-first · Semantic search · Auto-compression · Confidence decay

## Packages

| Package | Install | Description |
|---------|---------|-------------|
| [Python SDK](https://pypi.org/project/agentrecall-sdk/) | `pip install agentrecall-sdk` | Full-featured memory store with embeddings support |
| [Node.js SDK](https://www.npmjs.com/package/agentrecall-ai-sdk) | `npm install agentrecall-ai-sdk` | TypeScript-first with SQLite and optional embeddings |

## Quick Start

**Python:**
```python
from agentrecall import MemoryStore

store = MemoryStore()
store.remember("User prefers dark mode", agent="assistant")
memories = store.recall("What theme should I use?", agent="assistant")
```

**Node.js:**
```typescript
import { MemoryStore } from "agentrecall";

const store = new MemoryStore();
await store.remember("User prefers dark mode", { agent: "assistant" });
const memories = await store.recall("What theme should I use?", { agent: "assistant" });
```

## Graph Memory (Cloud Pro)

AgentRecall Cloud Pro includes a Neo4j-backed knowledge graph that automatically
extracts entities and relationships from your memories.

**Python:**
```python
from agentrecall import CloudClient

client = CloudClient(config)
# Store a memory — entities auto-extracted
client.remember("Alice works at Acme Corp in San Francisco", agent="assistant")

# Query the graph
stats = client.graph_stats("assistant")
print(f"{stats['total_entities']} entities in graph")

# Find connected entities
neighbors = client.graph_entity_neighbors("Alice", "assistant")
print(f"Alice is connected to {len(neighbors['neighbors'])} entities")

# Smart context retrieval
context = client.graph_context("assistant", "Where does Alice work?")
```

**Node.js:**
```typescript
import { CloudClient } from "agentrecall";

const client = new CloudClient(url, apiKey);
// Store — entities auto-extracted
await client.remember("Alice works at Acme Corp in San Francisco", { agent: "assistant" });

// Graph queries
const stats = await client.graphStats("assistant");
const neighbors = await client.graphEntityNeighbors("Alice", "assistant");
const context = await client.graphContext("assistant", "Where does Alice work?");
```

## Features

- **Semantic Recall** — hybrid scoring with embeddings (optional)
- **Auto-Classification** — memories tagged as preferences, corrections, facts, temporal
- **Confidence Decay** — memories fade unless reinforced
- **Skip/Penalty** — mark irrelevant memories to reduce recall score
- **SQLite** — zero config, works offline, single file
- **Graph Memory** — Neo4j-powered entity/relationship graph for semantic connections (Cloud Pro)
- **Privacy First** — runs locally, no data leaves your machine

## Pricing

| Tier | Price | What you get |
|------|-------|--------------|
| **Open Source** | Free | Full SDK, unlimited memories, local SQLite |
| **Cloud** | $3/agent/mo | Managed hosting, dashboard, graph memory, AI processing |

## Contributing

1. Fork the repo
2. Pick a package (`packages/python` or `packages/node`)
3. Make your changes
4. Run tests:
   - Python: `cd packages/python && python -m pytest tests/`
   - Node.js: `cd packages/node && npm test`
5. Open a PR

## License

MIT
