from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="AgentMemory", version="0.1.0")

# Lazy-loaded stores
_stores = {}

def get_store(agent_id: str):
    if agent_id not in _stores:
        from agentrecall.memory import MemoryStore
        _stores[agent_id] = MemoryStore(f"agentrecall_{agent_id}.db")
    return _stores[agent_id]


class SaveRequest(BaseModel):
    agent_id: str
    content: str
    tags: list[str] = []


class SaveResponse(BaseModel):
    id: str
    agent_id: str
    content: str
    memory_type: str
    priority: str


class RecallResult(BaseModel):
    id: str
    content: str
    score: float
    memory_type: str
    priority: str


@app.post("/v1/memories", response_model=SaveResponse)
def save_memory(req: SaveRequest):
    store = get_store(req.agent_id)
    memory = store.save(req.agent_id, req.content, req.tags)
    if memory is None:
        return SaveResponse(
            id="skipped", agent_id=req.agent_id, content=req.content,
            memory_type="skip", priority="low"
        )
    return SaveResponse(
        id=memory.id, agent_id=memory.agent_id,
        content=memory.content, memory_type=memory.memory_type.value,
        priority=memory.priority.value
    )


@app.get("/v1/memories/{agent_id}/recall", response_model=list[RecallResult])
def recall_memories(agent_id: str, q: str, limit: int = 5):
    store = get_store(agent_id)
    results = store.recall(agent_id, q, limit)
    return [
        RecallResult(
            id=r.memory.id, content=r.memory.content,
            score=round(r.score, 4), memory_type=r.memory.memory_type.value,
            priority=r.memory.priority.value
        )
        for r in results
    ]


@app.get("/v1/memories/{agent_id}/count")
def count_memories(agent_id: str):
    store = get_store(agent_id)
    return {"agent_id": agent_id, "count": store.count(agent_id)}


@app.delete("/v1/memories/{agent_id}/{memory_id}")
def delete_memory(agent_id: str, memory_id: str):
    store = get_store(agent_id)
    store.delete(memory_id)
    return {"deleted": True, "id": memory_id}


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8700)
