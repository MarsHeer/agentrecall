# AgentMemory

Plug-and-play memory for AI agents. Classify, store, compress, and retrieve memories with automatic relevance scoring.

## Features

- **Smart Classification** — Automatically categorizes memories (user facts, preferences, corrections, temporal)
- **Semantic Search** — Hybrid RAG retrieval with sentence-transformers embeddings
- **Auto-Compression** — Groups related memories and creates summaries
- **Memory Lifecycle** — TTL expiration and confidence decay for outdated memories
- **Zero Config** — Works out of the box with SQLite + local embeddings
- **REST API** — FastAPI server for any language/framework
- **Python SDK** — `pip install agentrecall` and go

## Quick Start

### As a Python Library

```python
from agentrecall import MemoryStore

# Create a store (SQLite + local embeddings)
store = MemoryStore("my_agent.db")

# Save memories (auto-classified)
store.save("agent", "User lives in Marbella, Spain")
store.save("agent", "I prefer concise responses")
store.save("agent", "Don't pretend to be me")

# Recall relevant memories
results = store.recall("agent", "where does the user live?")
print(results[0].memory.content)  # "User lives in Marbella, Spain"
print(results[0].score)  # 0.85
```

### As a REST API

```bash
pip install agentrecall
agentrecall
# Server starts on http://localhost:8700
```

```bash
# Save a memory
curl -X POST http://localhost:8700/v1/memories \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent", "content": "User lives in Marbella"}'

# Recall memories
curl "http://localhost:8700/v1/memories/agent/recall?q=where+does+user+live"
```

### With the Python Client

```python
from agentrecall.client import AgentMemoryClient

with AgentMemoryClient(agent_id="agent") as client:
    client.save("User has a dog named Poppy")
    results = client.recall("what pet does the user have?")
    print(results[0].content)  # "User has a dog named Poppy"
```

## Memory Types

| Type | Description | Auto-TTL | Priority |
|------|-------------|----------|----------|
| `user_fact` | Permanent facts about users | No | Medium |
| `preference` | User preferences and habits | No | High |
| `correction` | "Don't do X" corrections | No | High |
| `temporary` | Time-bound info | 7 days | Medium |
| `skip` | Task outputs, not stored | - | Low |

## How It Works

1. **Classify** — Every memory is automatically categorized using pattern matching (or optional LLM)
2. **Embed** — Local sentence-transformers creates 384-dim vectors for semantic search
3. **Store** — SQLite with embedding blobs, confidence scores, and TTL metadata
4. **Recall** — Hybrid scoring: semantic similarity × confidence × priority × type penalty
5. **Compress** — Old related memories are automatically grouped and summarized
6. **Decay** — Confidence decreases over time; memories below threshold are auto-deleted

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Agent      │────▶│  MemoryStore │────▶│   SQLite    │
│   (user)     │     │  (classify,  │     │  (hot       │
│              │     │   embed,     │     │   storage)  │
│              │     │   score)     │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │ sentence-   │
                    │ transformers│
                    │ (local)     │
                    └─────────────┘
```

## Configuration

```python
from agentrecall import MemoryStore, AgentMemoryConfig

config = AgentMemoryConfig(
    db_path="custom.db",
    embedding_model="all-MiniLM-L6-v2",  # or any sentence-transformers model
    max_context_tokens=500,
    decay_rate=0.01,          # confidence lost per day
    min_confidence=0.1,       # auto-delete below this
)

store = MemoryStore(config=config)
```

## Cost

- **Embeddings**: Free (local, ~20ms per text on CPU)
- **Storage**: SQLite (no external DB needed)
- **Classification**: Rule-based by default, optional LLM (~$0.0001/classification)
- **Total**: ~$0/month for typical agent usage

## License

MIT
