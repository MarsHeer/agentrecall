import re
import logging
from datetime import datetime, timezone
from agentrecall.storage import SQLiteStorage
from agentrecall.embeddings import EmbeddingEngine
from agentrecall.classifier import MemoryClassifier
from agentrecall.models import Memory, RecallResult
from agentrecall.config import AgentMemoryConfig

logger = logging.getLogger(__name__)

# Auto-skip detection patterns (internal heuristic, not a category)
_SKIP_PATTERNS = [
    r"wget.*download",
    r"apt-get.*install",
    r"pip.*install",
    r"command.*executed",
    r"process.*started",
    r"downloaded.*successfully",
    r"installation complete",
    r"backup.*created",
]

# Importance weights per the spec
_IMPORTANCE_WEIGHTS = {"high": 1.3, "medium": 1.0, "low": 0.7}


class MemoryStore:
    """Unified memory store matching the API spec.

    When config.mode is 'cloud' (or 'auto' with an api_key set), operations
    are transparently routed to the Agent Recall cloud API.

    Supports: remember, recall, get, update, delete, skip, unskip, count, wipe, close.
    Also supports context manager (with statement).
    """

    def __new__(cls, db_path: str = None, config: AgentMemoryConfig | None = None):
        config = config or AgentMemoryConfig()
        mode = config.mode
        use_cloud = False
        if mode == "cloud":
            use_cloud = True
        elif mode == "auto" and config.api_key:
            use_cloud = True

        if use_cloud:
            from agentrecall.cloud import CloudClient
            return CloudClient(config)

        instance = super().__new__(cls)
        return instance

    def __init__(self, db_path: str = None, config: AgentMemoryConfig | None = None):
        # Guard: if __new__ returned a CloudClient, skip local init
        if not isinstance(self, MemoryStore):
            return
        self.config = config or AgentMemoryConfig()
        actual_db_path = db_path or self.config.db_path
        self.storage = SQLiteStorage(actual_db_path)
        self.embeddings = EmbeddingEngine(self.config.embedding_model)
        self.classifier = MemoryClassifier(use_llm=False)
        self._embedding_cache: dict[int, list[float]] = {}
        self._closed = False

    # -- Context manager ---------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        """Close database connection."""
        self._closed = True
        self.storage.close()

    def _check_closed(self):
        if self._closed:
            raise RuntimeError("MemoryStore is closed")

    # -- Core methods per spec ---------------------------------------------

    def remember(
        self,
        content: str,
        *,
        agent: str = "default",
        category: str = None,
        importance: str = "medium",
        metadata: dict = None,
    ) -> Memory:
        """Store a memory. Auto-classifies if category not provided."""
        self._check_closed()

        if not content or not content.strip():
            raise ValueError("Content must not be empty")

        # Auto-classify if category not provided
        if category is None:
            classification = self.classifier.classify(content)
            category = classification["category"]
            # Use classifier importance only when caller didn't specify
            if importance == "medium":
                importance = classification.get("importance", "medium")

        now = datetime.now(timezone.utc)
        memory = Memory(
            content=content.strip(),
            category=category,
            agent=agent,
            importance=importance,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        memory = self.storage.store(memory)

        # Compute and store embedding
        try:
            embedding = self.embeddings.embed(content)
            self._embedding_cache[memory.id] = embedding
            self.storage.store_embedding(memory.id, embedding)
        except Exception as e:
            logger.warning(f"Embedding computation failed: {e}. "
                           "Falling back to confidence+recency scoring.")

        return memory

    def recall(
        self,
        query: str,
        *,
        agent: str = "default",
        category: str = None,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[RecallResult]:
        """Find relevant memories using hybrid scoring."""
        self._check_closed()

        if not query or not query.strip():
            raise ValueError("Query must not be empty")

        # Run confidence decay for this agent before scoring
        from agentrecall.lifecycle import MemoryLifecycle
        lifecycle = MemoryLifecycle(
            db_path=self.storage.db_path,
            decay_rate=self.config.decay_rate,
            min_confidence=self.config.min_confidence,
        )
        lifecycle.storage = self.storage
        lifecycle.run_decay(agent)

        # Get all memories for this agent
        all_memories = self.storage.list_all(agent)
        if not all_memories:
            return []

        # Filter by category if provided
        if category:
            all_memories = [m for m in all_memories if m.category == category]

        if not all_memories:
            return []

        # Compute query embedding
        try:
            query_vec = self.embeddings.embed(query)
            has_embeddings = True
        except Exception as e:
            logger.warning(f"Query embedding failed: {e}. Using fallback scoring.")
            query_vec = None
            has_embeddings = False

        # Score each memory per the spec formula:
        # score = similarity × confidence × importance_weight × recency × skip_penalty
        results = []
        now = datetime.now(timezone.utc)

        for memory in all_memories:
            # --- similarity ---
            if has_embeddings:
                mem_vec = self._get_embedding(memory.id, memory.content)
                if mem_vec is not None:
                    similarity = self.embeddings.similarity(query_vec, mem_vec)
                else:
                    similarity = 1.0  # fallback
            else:
                similarity = 1.0

            # --- confidence ---
            confidence = memory.confidence

            # --- importance_weight ---
            importance_weight = _IMPORTANCE_WEIGHTS.get(memory.importance, 1.0)

            # --- recency ---
            days_since_creation = max(0, (now - memory.created_at).days)
            recency = 1.0 / (1.0 + days_since_creation * 0.05)

            # --- skip_penalty ---
            skip_penalty = 0.2 if memory.skipped else 1.0

            # --- final score ---
            score = (
                similarity
                * confidence
                * importance_weight
                * recency
                * skip_penalty
            )

            if score >= min_score:
                results.append(RecallResult(
                    id=memory.id,
                    content=memory.content,
                    category=memory.category,
                    agent=memory.agent,
                    importance=memory.importance,
                    confidence=memory.confidence,
                    skipped=memory.skipped,
                    access_count=memory.access_count,
                    created_at=memory.created_at,
                    updated_at=memory.updated_at,
                    metadata=memory.metadata,
                    embedding=memory.embedding,
                    score=score,
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def get(self, id: int) -> Memory | None:
        """Get a single memory by ID. Returns None if not found."""
        self._check_closed()
        return self.storage.get(id)

    def update(self, id: int, content: str) -> None:
        """Update a memory's content."""
        self._check_closed()
        if not content or not content.strip():
            raise ValueError("Content must not be empty")
        memory = self.storage.get(id)
        if memory is None:
            return  # no-op for invalid IDs per spec
        memory.content = content.strip()
        memory.updated_at = datetime.now(timezone.utc)
        self.storage.store(memory)

    def delete(self, id: int) -> None:
        """Delete a memory permanently."""
        self._check_closed()
        self.storage.delete(id)

    def skip(self, id: int) -> None:
        """Mark a memory as skipped (reduces recall score by 80%)."""
        self._check_closed()
        self.storage.skip(id)

    def unskip(self, id: int) -> None:
        """Unmark a skipped memory."""
        self._check_closed()
        self.storage.unskip(id)

    def count(self, agent: str = None) -> int:
        """Count memories, optionally filtered by agent."""
        self._check_closed()
        return self.storage.count(agent=agent)

    def wipe(self, agent: str = None, category: str = None) -> None:
        """Delete memories. Filter by agent and/or category. If no filters, delete ALL."""
        self._check_closed()
        self.storage.wipe(agent=agent, category=category)

    # -- Internal helpers --------------------------------------------------

    def _get_embedding(self, memory_id: int, content: str) -> list[float] | None:
        """Get embedding from cache, DB, or compute on the fly."""
        if memory_id in self._embedding_cache:
            return self._embedding_cache[memory_id]

        mem_vec = self.storage.get_embedding(memory_id)
        if mem_vec is not None:
            self._embedding_cache[memory_id] = mem_vec
            return mem_vec

        # Compute and cache
        try:
            mem_vec = self.embeddings.embed(content)
            self._embedding_cache[memory_id] = mem_vec
            self.storage.store_embedding(memory_id, mem_vec)
            return mem_vec
        except Exception as e:
            logger.warning(f"Failed to compute embedding for memory {memory_id}: {e}")
            return None
