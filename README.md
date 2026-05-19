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

## Features

- **Semantic Recall** — hybrid scoring with embeddings (optional)
- **Auto-Classification** — memories tagged as preferences, corrections, facts, temporal
- **Confidence Decay** — memories fade unless reinforced
- **Skip/Penalty** — mark irrelevant memories to reduce recall score
- **SQLite** — zero config, works offline, single file
- **Privacy First** — runs locally, no data leaves your machine

## Pricing

| Tier | Price | What you get |
|------|-------|--------------|
| **Open Source** | Free | Full SDK, unlimited memories, local SQLite |
| **Cloud** | $3/agent/mo | Managed hosting, dashboard, sync (coming soon) |

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
