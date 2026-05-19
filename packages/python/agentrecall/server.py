import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="AgentMemory", version="0.1.0")

# Lazy-loaded stores
_stores = {}


def _sanitize_filename(name: str) -> str:
    """Sanitize agent_id for safe use in filenames (security fix)."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)


def get_store(agent_id: str):
    if agent_id not in _stores:
        from agentrecall.memory import MemoryStore
        safe_name = _sanitize_filename(agent_id)
        _stores[agent_id] = MemoryStore(f"agentrecall_{safe_name}.db")
    return _stores[agent_id]


class SaveRequest(BaseModel):
    agent_id: str
    content: str
    tags: list[str] = []


class SaveResponse(BaseModel):
    id: int
    agent: str
    content: str
    category: str
    importance: str


class RecallResultResponse(BaseModel):
    id: int
    content: str
    score: float
    category: str
    importance: str


@app.post("/v1/memories", response_model=SaveResponse)
def save_memory(req: SaveRequest):
    store = get_store(req.agent_id)
    memory = store.remember(req.content, agent=req.agent_id)
    return SaveResponse(
        id=memory.id, agent=memory.agent,
        content=memory.content, category=memory.category,
        importance=memory.importance,
    )


@app.get("/v1/memories/{agent_id}/recall", response_model=list[RecallResultResponse])
def recall_memories(agent_id: str, q: str, limit: int = 5):
    store = get_store(agent_id)
    results = store.recall(q, agent=agent_id, limit=limit)
    return [
        RecallResultResponse(
            id=r.memory.id, content=r.memory.content,
            score=round(r.score, 4), category=r.memory.category,
            importance=r.memory.importance,
        )
        for r in results
    ]


@app.get("/v1/memories/{agent_id}/count")
def count_memories(agent_id: str):
    store = get_store(agent_id)
    return {"agent_id": agent_id, "count": store.count(agent_id)}


@app.delete("/v1/memories/{agent_id}/{memory_id}")
def delete_memory(agent_id: str, memory_id: int):
    store = get_store(agent_id)
    store.delete(memory_id)
    return {"deleted": True, "id": memory_id}


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8700)
