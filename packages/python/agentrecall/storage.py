import sqlite3
import json
from datetime import datetime, timezone
from agentrecall.models import Memory


class SQLiteStorage:
    """SQLite storage backend matching the unified API spec schema."""

    def __init__(self, db_path: str = "agentrecall.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                agent TEXT NOT NULL DEFAULT 'default',
                importance TEXT NOT NULL DEFAULT 'medium',
                confidence REAL NOT NULL DEFAULT 1.0,
                skipped INTEGER NOT NULL DEFAULT 0,
                access_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                metadata TEXT NOT NULL DEFAULT '{}',
                embedding BLOB
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_skipped ON memories(skipped)")
        self.conn.commit()

    def store(self, memory: Memory) -> Memory:
        """Insert or update a memory. Returns the memory with id set."""
        if memory.id is not None:
            # Update existing — always stamp updated_at as now
            now_str = datetime.now(timezone.utc).isoformat()
            self.conn.execute("""
                UPDATE memories SET
                    content=?, category=?, agent=?, importance=?,
                    confidence=?, skipped=?, access_count=?,
                    updated_at=?, metadata=?
                WHERE id=?
            """, (
                memory.content, memory.category, memory.agent, memory.importance,
                memory.confidence, int(memory.skipped), memory.access_count,
                now_str, json.dumps(memory.metadata),
                memory.id,
            ))
            self.conn.commit()
            memory.updated_at = datetime.now(timezone.utc)
        else:
            # Insert new — respect the memory's timestamps
            cursor = self.conn.execute("""
                INSERT INTO memories
                    (content, category, agent, importance, confidence,
                     skipped, access_count, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.content, memory.category, memory.agent, memory.importance,
                memory.confidence, int(memory.skipped), memory.access_count,
                memory.created_at.isoformat(), memory.updated_at.isoformat(),
                json.dumps(memory.metadata),
            ))
            self.conn.commit()
            memory.id = cursor.lastrowid

        return memory

    def get(self, memory_id: int) -> Memory | None:
        """Get a single memory by ID."""
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return self._row_to_memory(row) if row else None

    def delete(self, memory_id: int):
        """Delete a memory by ID."""
        self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()

    def skip(self, memory_id: int):
        """Mark a memory as skipped."""
        now_str = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE memories SET skipped = 1, updated_at = ? WHERE id = ?",
            (now_str, memory_id),
        )
        self.conn.commit()

    def unskip(self, memory_id: int):
        """Unmark a skipped memory."""
        now_str = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE memories SET skipped = 0, updated_at = ? WHERE id = ?",
            (now_str, memory_id),
        )
        self.conn.commit()

    def list_all(self, agent: str) -> list[Memory]:
        """List all memories for an agent, ordered by updated_at DESC."""
        rows = self.conn.execute(
            "SELECT * FROM memories WHERE agent = ? ORDER BY updated_at DESC",
            (agent,),
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def count(self, agent: str = None) -> int:
        """Count memories, optionally filtered by agent."""
        if agent:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM memories WHERE agent = ?", (agent,)
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        return row[0]

    def wipe(self, agent: str = None, category: str = None):
        """Delete memories. If no filters, delete ALL."""
        conditions = []
        params = []
        if agent:
            conditions.append("agent = ?")
            params.append(agent)
        if category:
            conditions.append("category = ?")
            params.append(category)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        self.conn.execute(f"DELETE FROM memories{where}", params)
        self.conn.commit()

    def search(self, agent: str, query: str = "", limit: int = 10) -> list[Memory]:
        """Text search within an agent's memories."""
        if query:
            rows = self.conn.execute(
                "SELECT * FROM memories WHERE agent = ? AND content LIKE ? "
                "ORDER BY updated_at DESC LIMIT ?",
                (agent, f"%{query}%", limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM memories WHERE agent = ? "
                "ORDER BY updated_at DESC LIMIT ?",
                (agent, limit),
            ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def store_embedding(self, memory_id: int, embedding: list[float]):
        """Store embedding as JSON array in BLOB (spec-compliant)."""
        blob = json.dumps(embedding).encode("utf-8")
        self.conn.execute(
            "UPDATE memories SET embedding = ? WHERE id = ?", (blob, memory_id)
        )
        self.conn.commit()

    def get_embedding(self, memory_id: int) -> list[float] | None:
        """Retrieve embedding from BLOB. Handles both JSON and struct formats."""
        row = self.conn.execute(
            "SELECT embedding FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if row and row["embedding"]:
            data = row["embedding"]
            if isinstance(data, str):
                return json.loads(data)
            # bytes → decode JSON
            return json.loads(data.decode("utf-8"))
        return None

    def update_confidence(self, memory_id: int, confidence: float):
        """Update a memory's confidence value."""
        now_str = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE memories SET confidence = ?, updated_at = ? WHERE id = ?",
            (confidence, now_str, memory_id),
        )
        self.conn.commit()

    def increment_access(self, memory_id: int):
        """Increment access_count for a memory."""
        now_str = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE memories SET access_count = access_count + 1, "
            "updated_at = ? WHERE id = ?",
            (now_str, memory_id),
        )
        self.conn.commit()

    def _row_to_memory(self, row) -> Memory:
        """Convert a SQLite row to a Memory object."""
        return Memory(
            id=row["id"],
            content=row["content"],
            category=row["category"],
            agent=row["agent"],
            importance=row["importance"],
            confidence=row["confidence"],
            skipped=bool(row["skipped"]),
            access_count=row["access_count"],
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime:
        """Parse ISO datetime string, ensuring timezone awareness."""
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
