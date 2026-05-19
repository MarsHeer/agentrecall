# AgentRecall SDK

Plug-and-play persistent memory for AI agents.

## Install

```bash
pip install agentrecall-sdk
```

## Quick Start

```python
from agentrecall import MemoryStore

store = MemoryStore()

# Store memories
store.remember("User prefers dark mode", agent="assistant")
store.remember("User lives in Marbella, Spain", agent="assistant")

# Recall relevant memories
memories = store.recall("What theme should I use?", agent="assistant")
for m in memories:
    print(f"[{m.score:.2f}] {m.content}")
```

## Cloud Mode

Connect to AgentRecall Cloud API for managed hosting:

```python
from agentrecall import CloudClient, AgentMemoryConfig

config = AgentMemoryConfig(
    cloud_url="https://api.agentrecall.cloud",
    api_key="your-api-key"
)
client = CloudClient(config)

client.remember("User prefers dark mode", agent="assistant")
memories = client.recall("What theme should I use?", agent="assistant")
```

## Graph Memory (Cloud Pro)

```python
client = CloudClient(config)

# Store — entities auto-extracted to Neo4j graph
client.remember("Alice works at Acme Corp in San Francisco", agent="assistant")

# Query the graph
stats = client.graph_stats("assistant")
neighbors = client.graph_entity_neighbors("Alice", "assistant")
context = client.graph_context("assistant", "Where does Alice work?")
```

## API Reference

### MemoryStore (local)

| Method | Description |
|--------|-------------|
| `remember(content, agent, category, importance, metadata)` | Store a memory |
| `recall(query, agent, category, limit, min_score)` | Find relevant memories |
| `get(id)` | Get memory by ID |
| `update(id, content)` | Update memory content |
| `delete(id)` | Delete a memory |
| `skip(id)` / `unskip(id)` | Penalize/unpenalize a memory |
| `count(agent)` | Count memories |
| `wipe(agent, category)` | Delete memories |

### CloudClient (cloud)

Same methods as MemoryStore plus:

| Method | Description |
|--------|-------------|
| `graph_entities(agent, type, limit)` | List graph entities |
| `graph_entity_neighbors(name, agent, depth)` | Find connected entities |
| `graph_relationships(agent, source, target, limit)` | List relationships |
| `graph_paths(agent, from, to, max_depth)` | Find shortest path |
| `graph_stats(agent)` | Graph statistics |
| `graph_context(agent, query, limit)` | Smart context retrieval |

## License

MIT
