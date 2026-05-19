from datetime import datetime
from agentrecall.storage import SQLiteStorage
from agentrecall.models import Memory


class MemoryLifecycle:
    def __init__(self, db_path: str, decay_rate: float = 0.01, min_confidence: float = 0.1):
        self.storage = SQLiteStorage(db_path)
        self.decay_rate = decay_rate
        self.min_confidence = min_confidence

    def cleanup_expired(self, agent_id: str) -> int:
        """Remove expired memories. Returns count removed."""
        now = datetime.utcnow().isoformat()
        cursor = self.storage.conn.execute(
            "DELETE FROM memories WHERE agent_id = ? AND expires_at IS NOT NULL AND expires_at < ?",
            (agent_id, now)
        )
        self.storage.conn.commit()
        return cursor.rowcount

    def decay_confidence(self, memory: Memory, days: int) -> float:
        """Calculate decayed confidence."""
        return max(0.0, memory.confidence - (self.decay_rate * days))

    def run_decay(self, agent_id: str) -> int:
        """Apply decay to all memories and remove those below threshold."""
        now = datetime.utcnow()
        memories = self.storage.list_all(agent_id)
        removed = 0

        for m in memories:
            days_old = (now - m.updated_at).days
            new_conf = self.decay_confidence(m, days_old)

            if new_conf < self.min_confidence:
                self.storage.delete(m.id)
                removed += 1
            elif new_conf != m.confidence:
                m.confidence = new_conf
                self.storage.store(m)

        return removed

    def touch(self, memory_id: str):
        """Update last_accessed and access_count."""
        self.storage.conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), memory_id)
        )
        self.storage.conn.commit()
