import sqlite3
import json
import uuid
from datetime import datetime
from agentrecall.models import Memory, MemoryType, MemoryPriority


class SQLiteStorage:
    def __init__(self, db_path: str = "agentrecall.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT,
                priority TEXT,
                tags TEXT,
                confidence REAL,
                ttl_seconds INTEGER,
                created_at TEXT,
                updated_at TEXT,
                expires_at TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                embedding BLOB
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_agent ON memories(agent_id)")
        self.conn.commit()

    def store(self, memory: Memory) -> Memory:
        if not memory.id:
            memory.id = str(uuid.uuid4())
        self.conn.execute("""
            INSERT OR REPLACE INTO memories
            (id, agent_id, content, memory_type, priority, tags, confidence,
             ttl_seconds, created_at, updated_at, expires_at, access_count, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id, memory.agent_id, memory.content,
            memory.memory_type.value, memory.priority.value,
            json.dumps(memory.tags), memory.confidence,
            memory.ttl_seconds, memory.created_at.isoformat(),
            memory.updated_at.isoformat(),
            memory.expires_at.isoformat() if memory.expires_at else None,
            memory.access_count,
            memory.last_accessed.isoformat() if memory.last_accessed else None
        ))
        self.conn.commit()
        return memory

    def search(self, agent_id: str, query: str = "", limit: int = 10) -> list[Memory]:
        if query:
            # FTS-like text match
            rows = self.conn.execute(
                "SELECT * FROM memories WHERE agent_id = ? AND content LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (agent_id, f"%{query}%", limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM memories WHERE agent_id = ? ORDER BY updated_at DESC LIMIT ?",
                (agent_id, limit)
            ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def delete(self, memory_id: str):
        self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()

    def get(self, memory_id: str) -> Memory | None:
        row = self.conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return self._row_to_memory(row) if row else None

    def list_all(self, agent_id: str) -> list[Memory]:
        rows = self.conn.execute(
            "SELECT * FROM memories WHERE agent_id = ? ORDER BY updated_at DESC", (agent_id,)
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def store_embedding(self, memory_id: str, embedding: list[float]):
        import struct
        blob = struct.pack(f"{len(embedding)}f", *embedding)
        self.conn.execute("UPDATE memories SET embedding = ? WHERE id = ?", (blob, memory_id))
        self.conn.commit()

    def get_embedding(self, memory_id: str) -> list[float] | None:
        row = self.conn.execute("SELECT embedding FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if row and row["embedding"]:
            import struct
            data = row["embedding"]
            n = len(data) // 4
            return list(struct.unpack(f"{n}f", data))
        return None

    def _row_to_memory(self, row) -> Memory:
        return Memory(
            id=row["id"], agent_id=row["agent_id"], content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            priority=MemoryPriority(row["priority"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            confidence=row["confidence"],
            ttl_seconds=row["ttl_seconds"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            access_count=row["access_count"],
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None
        )
