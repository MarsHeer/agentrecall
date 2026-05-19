import httpx
from dataclasses import dataclass


@dataclass
class MemoryResult:
    id: str
    content: str
    score: float
    memory_type: str
    priority: str


class AgentMemoryClient:
    """Lightweight client for AgentMemory API."""

    def __init__(self, base_url: str = "http://localhost:8700", agent_id: str = "default"):
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self._client = httpx.Client(timeout=30)

    def save(self, content: str, tags: list[str] = []) -> dict:
        resp = self._client.post(f"{self.base_url}/v1/memories", json={
            "agent_id": self.agent_id,
            "content": content,
            "tags": tags,
        })
        resp.raise_for_status()
        return resp.json()

    def recall(self, query: str, limit: int = 5) -> list[MemoryResult]:
        resp = self._client.get(
            f"{self.base_url}/v1/memories/{self.agent_id}/recall",
            params={"q": query, "limit": limit}
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            MemoryResult(
                id=r["id"], content=r["content"],
                score=r["score"], memory_type=r["memory_type"],
                priority=r["priority"]
            )
            for r in data
        ]

    def count(self) -> int:
        resp = self._client.get(f"{self.base_url}/v1/memories/{self.agent_id}/count")
        resp.raise_for_status()
        return resp.json()["count"]

    def delete(self, memory_id: str) -> bool:
        resp = self._client.delete(f"{self.base_url}/v1/memories/{self.agent_id}/{memory_id}")
        resp.raise_for_status()
        return resp.json().get("deleted", False)

    def health(self) -> dict:
        resp = self._client.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
