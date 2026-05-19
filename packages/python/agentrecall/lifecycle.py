from datetime import datetime, timezone
from agentrecall.storage import SQLiteStorage
from agentrecall.models import Memory


class MemoryLifecycle:
    """Handle memory lifecycle: confidence decay and cleanup."""

    def __init__(self, db_path: str, decay_rate: float = 0.01, min_confidence: float = 0.1):
        self.storage = SQLiteStorage(db_path)
        self.decay_rate = decay_rate
        self.min_confidence = min_confidence

    def cleanup_expired(self, agent: str) -> int:
        """Remove expired memories (legacy TTL support). Returns count removed."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.storage.conn.execute(
            "DELETE FROM memories WHERE agent = ? AND updated_at < ?",
            (agent, now),
        )
        self.storage.conn.commit()
        return cursor.rowcount

    def decay_confidence(self, memory: Memory) -> float:
        """Calculate decayed confidence — 1 step per call.

        new_confidence = confidence × (1 - decay_rate)
        """
        return max(0.0, memory.confidence * (1 - self.decay_rate))

    def run_decay(self, agent: str) -> int:
        """Apply decay to all memories and remove those below threshold.

        Returns count of memories removed.
        """
        memories = self.storage.list_all(agent)
        removed = 0

        for m in memories:
            new_conf = self.decay_confidence(m)

            if new_conf < self.min_confidence:
                self.storage.delete(m.id)
                removed += 1
            elif new_conf != m.confidence:
                self.storage.update_confidence(m.id, new_conf)

        return removed

    def touch(self, memory_id: int):
        """Update access_count for a memory."""
        self.storage.increment_access(memory_id)
