import numpy as np
from datetime import datetime
from agentrecall.storage import SQLiteStorage
from agentrecall.embeddings import EmbeddingEngine
from agentrecall.classifier import MemoryClassifier
from agentrecall.models import Memory, MemoryType, RecallResult
from agentrecall.config import AgentMemoryConfig


class MemoryStore:
    def __init__(self, db_path: str = "agentrecall.db", config: AgentMemoryConfig | None = None):
        self.config = config or AgentMemoryConfig()
        self.storage = SQLiteStorage(db_path)
        self.embeddings = EmbeddingEngine(self.config.embedding_model)
        self.classifier = MemoryClassifier(use_llm=False)
        self._embedding_cache: dict[str, list[float]] = {}

    def save(self, agent_id: str, content: str, tags: list[str] = []) -> Memory | None:
        """Save a memory. Returns None if classified as SKIP."""
        classification = self.classifier.classify(content)

        if classification["memory_type"] == MemoryType.SKIP:
            return None

        memory = Memory(
            agent_id=agent_id,
            content=content,
            memory_type=classification["memory_type"],
            priority=classification["priority"],
            tags=tags + classification.get("tags", []),
            ttl_seconds=classification.get("ttl_seconds"),
        )

        if memory.ttl_seconds:
            from datetime import timedelta
            memory.expires_at = datetime.utcnow() + timedelta(seconds=memory.ttl_seconds)

        memory = self.storage.store(memory)

        # Store embedding in cache and DB
        embedding = self.embeddings.embed(content)
        self._embedding_cache[memory.id] = embedding
        self.storage.store_embedding(memory.id, embedding)

        return memory

    def recall(self, agent_id: str, query: str, limit: int = 5) -> list[RecallResult]:
        """Recall memories relevant to a query using hybrid RAG."""
        # Get all memories for this agent
        all_memories = self.storage.list_all(agent_id)

        if not all_memories:
            return []

        # Filter expired
        now = datetime.utcnow()
        valid = [m for m in all_memories if not m.expires_at or m.expires_at > now]

        if not valid:
            return []

        # Compute query embedding
        query_vec = self.embeddings.embed(query)

        # Score each memory
        results = []
        for memory in valid:
            # Get cached or stored embedding
            if memory.id in self._embedding_cache:
                mem_vec = self._embedding_cache[memory.id]
            else:
                mem_vec = self.storage.get_embedding(memory.id)
                if mem_vec is None:
                    mem_vec = self.embeddings.embed(memory.content)
                    self.storage.store_embedding(memory.id, mem_vec)
                self._embedding_cache[memory.id] = mem_vec

            # Semantic similarity
            semantic_score = self.embeddings.similarity(query_vec, mem_vec)

            # Confidence boost
            confidence_boost = memory.confidence

            # Priority boost
            priority_boost = {"high": 1.3, "medium": 1.0, "low": 0.7}.get(memory.priority.value, 1.0)

            # SKIP memories get penalized
            skip_penalty = 0.2 if memory.memory_type == MemoryType.SKIP else 1.0

            # Final score
            score = semantic_score * confidence_boost * priority_boost * skip_penalty

            results.append(RecallResult(memory=memory, score=score, source="semantic"))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def delete(self, memory_id: str):
        """Delete a memory by ID."""
        self.storage.delete(memory_id)

    def count(self, agent_id: str) -> int:
        """Count memories for an agent."""
        return len(self.storage.list_all(agent_id))
