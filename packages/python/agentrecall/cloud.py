"""Cloud adapter — routes MemoryStore operations to the Agent Recall cloud API."""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from agentrecall.config import AgentMemoryConfig
from agentrecall.models import Memory, RecallResult

logger = logging.getLogger(__name__)


class CloudClient:
    """Drop-in replacement for MemoryStore that talks to the cloud API.

    Implements the same public interface: remember, recall, get, update,
    delete, count, wipe, close, skip, unskip, plus context-manager support.
    """

    def __init__(self, config: AgentMemoryConfig):
        self.config = config
        self._base_url = config.cloud_url.rstrip("/")
        self._closed = False
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=30.0,
        )

    # -- Context manager ------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        self._closed = True
        self._http.close()

    def _check_closed(self):
        if self._closed:
            raise RuntimeError("CloudClient is closed")

    # -- Helpers --------------------------------------------------------

    def _to_memory(self, data: dict) -> Memory:
        """Convert a cloud API JSON dict to a Memory model."""
        return Memory(
            id=data.get("id"),
            content=data.get("content", ""),
            category=data.get("category", "general"),
            agent=data.get("agent", "default"),
            importance=data.get("importance", "medium"),
            confidence=data.get("confidence", 1.0),
            skipped=data.get("skipped", False),
            access_count=data.get("access_count", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata") or {},
            embedding=data.get("embedding"),
            ai_processed=data.get("ai_processed", False),
            summary=data.get("summary", ""),
            keywords=data.get("keywords", []),
            entities=data.get("entities", []),
            relationships=data.get("relationships", []),
        )

    def _to_recall(self, data: dict) -> RecallResult:
        """Convert a cloud API JSON dict to a RecallResult."""
        return RecallResult(
            id=data.get("id"),
            content=data.get("content", ""),
            category=data.get("category", "general"),
            agent=data.get("agent", "default"),
            importance=data.get("importance", "medium"),
            confidence=data.get("confidence", 1.0),
            skipped=data.get("skipped", False),
            access_count=data.get("access_count", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata") or {},
            embedding=data.get("embedding"),
            ai_processed=data.get("ai_processed", False),
            summary=data.get("summary", ""),
            keywords=data.get("keywords", []),
            entities=data.get("entities", []),
            relationships=data.get("relationships", []),
            score=data.get("score", 0.0),
        )

    def _resolve_agent_id(self, agent: str) -> int:
        """Look up or create an agent by name, return its numeric id."""
        resp = self._http.get("/v1/agents")
        resp.raise_for_status()
        for a in resp.json():
            if a.get("name") == agent:
                return a["id"]
        # Create agent
        resp2 = self._http.post("/v1/agents", json={"name": agent})
        resp2.raise_for_status()
        return resp2.json()["id"]

    # -- Core methods ---------------------------------------------------

    def remember(
        self,
        content: str,
        *,
        agent: str = "default",
        category: str = None,
        importance: str = "medium",
        metadata: dict = None,
    ) -> Memory:
        self._check_closed()
        if not content or not content.strip():
            raise ValueError("Content must not be empty")

        agent_id = self._resolve_agent_id(agent)
        body = {
            "content": content.strip(),
            "agent_id": agent_id,
            "importance": importance,
            "metadata": metadata or {},
        }
        if category:
            body["category"] = category

        resp = self._http.post("/v1/memories", json=body)
        resp.raise_for_status()
        return self._to_memory(resp.json())

    def recall(
        self,
        query: str,
        *,
        agent: str = "default",
        category: str = None,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[RecallResult]:
        self._check_closed()
        if not query or not query.strip():
            raise ValueError("Query must not be empty")

        agent_id = self._resolve_agent_id(agent)
        params: dict = {"query": query, "agent_id": agent_id, "limit": limit}
        if category:
            params["category"] = category

        resp = self._http.get("/v1/memories/recall", params=params)
        resp.raise_for_status()
        results = [self._to_recall(item) for item in resp.json()]
        if min_score > 0:
            results = [r for r in results if r.score >= min_score]
        return results

    def get(self, id: int) -> Optional[Memory]:
        self._check_closed()
        resp = self._http.get(f"/v1/memories/{id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._to_memory(resp.json())

    def update(self, id: int, content: str) -> None:
        self._check_closed()
        if not content or not content.strip():
            raise ValueError("Content must not be empty")
        resp = self._http.put(f"/v1/memories/{id}", json={"content": content.strip()})
        if resp.status_code == 404:
            return  # no-op for invalid IDs
        resp.raise_for_status()

    def delete(self, id: int) -> None:
        self._check_closed()
        resp = self._http.delete(f"/v1/memories/{id}")
        if resp.status_code == 404:
            return  # already gone
        resp.raise_for_status()

    def skip(self, id: int) -> None:
        self._check_closed()
        resp = self._http.post(f"/v1/memories/{id}/skip")
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    def unskip(self, id: int) -> None:
        self._check_closed()
        resp = self._http.delete(f"/v1/memories/{id}/skip")
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    def count(self, agent: str = None) -> int:
        self._check_closed()
        if agent:
            agent_id = self._resolve_agent_id(agent)
            resp = self._http.get(f"/v1/agents/{agent_id}/count")
            resp.raise_for_status()
            return resp.json().get("count", 0)
        # No agent filter — sum all agents
        resp = self._http.get("/v1/agents")
        resp.raise_for_status()
        total = 0
        for a in resp.json():
            r2 = self._http.get(f"/v1/agents/{a['id']}/count")
            r2.raise_for_status()
            total += r2.json().get("count", 0)
        return total

    def wipe(self, agent: str = None, category: str = None) -> None:
        self._check_closed()
        if agent:
            agent_id = self._resolve_agent_id(agent)
            resp = self._http.get(f"/v1/agents/{agent_id}/count")
            resp.raise_for_status()
            count = resp.json().get("count", 0)
            if count == 0:
                return
            # Recall all and delete
            results = self.recall("*", agent=agent, limit=count)
            for r in results:
                self.delete(r.id)
        else:
            resp = self._http.get("/v1/agents")
            resp.raise_for_status()
            for a in resp.json():
                self.wipe(agent=a["name"], category=category)

    # -- Graph methods (Cloud Pro) ----------------------------------------

    def graph_entities(
        self,
        agent: str = "default",
        type: str = None,
        limit: int = 50,
    ) -> list[dict]:
        """List all entities in the knowledge graph for an agent."""
        self._check_closed()
        agent_id = self._resolve_agent_id(agent)
        params: dict = {"agent_id": agent_id, "limit": limit}
        if type:
            params["type"] = type
        resp = self._http.get("/v1/graph/entities", params=params)
        resp.raise_for_status()
        return resp.json()

    def graph_entity_neighbors(
        self,
        entity_name: str,
        agent: str = "default",
        depth: int = 1,
    ) -> dict:
        """Get neighboring entities connected to a specific entity."""
        self._check_closed()
        agent_id = self._resolve_agent_id(agent)
        params: dict = {"agent_id": agent_id, "depth": depth}
        resp = self._http.get(
            f"/v1/graph/entities/{entity_name}/neighbors", params=params
        )
        resp.raise_for_status()
        return resp.json()

    def graph_relationships(
        self,
        agent: str = "default",
        source: str = None,
        target: str = None,
        limit: int = 50,
    ) -> list[dict]:
        """List relationships between entities in the graph."""
        self._check_closed()
        agent_id = self._resolve_agent_id(agent)
        params: dict = {"agent_id": agent_id, "limit": limit}
        if source:
            params["source"] = source
        if target:
            params["target"] = target
        resp = self._http.get("/v1/graph/relationships", params=params)
        resp.raise_for_status()
        return resp.json()

    def graph_paths(
        self,
        from_entity: str,
        to_entity: str,
        agent: str = "default",
        max_depth: int = 5,
    ) -> dict:
        """Find the shortest path between two entities in the graph."""
        self._check_closed()
        agent_id = self._resolve_agent_id(agent)
        params: dict = {
            "agent_id": agent_id,
            "from": from_entity,
            "to": to_entity,
            "max_depth": max_depth,
        }
        resp = self._http.get("/v1/graph/paths", params=params)
        resp.raise_for_status()
        return resp.json()

    def graph_stats(self, agent: str = "default") -> dict:
        """Get statistics about the knowledge graph for an agent."""
        self._check_closed()
        agent_id = self._resolve_agent_id(agent)
        params: dict = {"agent_id": agent_id}
        resp = self._http.get("/v1/graph/stats", params=params)
        resp.raise_for_status()
        return resp.json()

    def graph_context(
        self,
        query: str,
        agent: str = "default",
        limit: int = 10,
    ) -> dict:
        """Retrieve graph context relevant to a natural language query."""
        self._check_closed()
        agent_id = self._resolve_agent_id(agent)
        params: dict = {"agent_id": agent_id, "query": query, "limit": limit}
        resp = self._http.get("/v1/graph/context", params=params)
        resp.raise_for_status()
        return resp.json()
