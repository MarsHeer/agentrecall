import Database from "better-sqlite3";
import path from "path";
import os from "os";
import fs from "fs";
import type { Memory } from "./types.js";

const DEFAULT_DB_PATH = path.join(
  os.homedir(),
  ".agentrecall",
  "memories.db"
);

export class Storage {
  private db: Database.Database;
  private closed = false;

  constructor(dbPath?: string) {
    const dir = path.dirname(dbPath || DEFAULT_DB_PATH);
    fs.mkdirSync(dir, { recursive: true });

    this.db = new Database(dbPath || DEFAULT_DB_PATH);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("foreign_keys = ON");
    this.init();
  }

  private init(): void {
    this.db.exec(`
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
      );

      CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent);
      CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
      CREATE INDEX IF NOT EXISTS idx_memories_skipped ON memories(skipped);
    `);

    // Migration: add embedding column if missing (for existing DBs)
    try {
      this.db.prepare("SELECT embedding FROM memories LIMIT 1").get();
    } catch {
      this.db.exec("ALTER TABLE memories ADD COLUMN embedding BLOB");
    }

    // Migration: rename skip -> skipped if needed
    try {
      this.db.prepare("SELECT skipped FROM memories LIMIT 1").get();
    } catch {
      try {
        this.db.exec("ALTER TABLE memories RENAME COLUMN skip TO skipped");
        this.db.exec("DROP INDEX IF EXISTS idx_memories_skip");
        this.db.exec(
          "CREATE INDEX IF NOT EXISTS idx_memories_skipped ON memories(skipped)"
        );
      } catch {
        // skip column doesn't exist at all, that's fine
      }
    }
  }

  checkClosed(): void {
    if (this.closed) {
      throw new Error("Store is closed");
    }
  }

  insert(
    content: string,
    category: string,
    agent: string,
    importance: string,
    metadata: Record<string, unknown> = {},
    embedding?: number[] | null
  ): number {
    this.checkClosed();
    const embeddingBlob =
      embedding != null
        ? Buffer.from(JSON.stringify(embedding), "utf-8")
        : null;
    const stmt = this.db.prepare(`
      INSERT INTO memories (content, category, agent, importance, metadata, embedding)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    const result = stmt.run(
      content,
      category,
      agent,
      importance,
      JSON.stringify(metadata),
      embeddingBlob
    );
    return Number(result.lastInsertRowid);
  }

  get(id: number): Memory | undefined {
    this.checkClosed();
    const row = this.db
      .prepare("SELECT * FROM memories WHERE id = ?")
      .get(id) as Record<string, unknown> | undefined;
    if (!row) return undefined;
    return this.parseRow(row);
  }

  update(
    id: number,
    updates: Partial<
      Pick<Memory, "content" | "confidence" | "skipped" | "access_count">
    >
  ): void {
    this.checkClosed();
    const sets: string[] = [];
    const values: unknown[] = [];

    if (updates.content !== undefined) {
      sets.push("content = ?");
      values.push(updates.content);
    }
    if (updates.confidence !== undefined) {
      sets.push("confidence = ?");
      values.push(updates.confidence);
    }
    if (updates.skipped !== undefined) {
      sets.push("skipped = ?");
      values.push(updates.skipped ? 1 : 0);
    }
    if (updates.access_count !== undefined) {
      sets.push("access_count = ?");
      values.push(updates.access_count);
    }

    if (sets.length === 0) return;

    sets.push("updated_at = datetime('now')");
    values.push(id);

    this.db
      .prepare(`UPDATE memories SET ${sets.join(", ")} WHERE id = ?`)
      .run(...values);
  }

  delete(id: number): void {
    this.checkClosed();
    this.db.prepare("DELETE FROM memories WHERE id = ?").run(id);
  }

  deleteMany(ids: number[]): void {
    this.checkClosed();
    if (ids.length === 0) return;
    const placeholders = ids.map(() => "?").join(",");
    this.db
      .prepare(`DELETE FROM memories WHERE id IN (${placeholders})`)
      .run(...ids);
  }

  search(
    agent: string,
    category?: string,
    limit: number = 10,
    excludeSkipped: boolean = false
  ): Memory[] {
    this.checkClosed();
    let query = "SELECT * FROM memories WHERE agent = ?";
    const params: unknown[] = [agent];

    if (category) {
      query += " AND category = ?";
      params.push(category);
    }
    if (excludeSkipped) {
      query += " AND skipped = 0";
    }

    query += " ORDER BY confidence DESC, access_count DESC, created_at DESC";
    query += " LIMIT ?";
    params.push(limit);

    const rows = this.db
      .prepare(query)
      .all(...params) as Record<string, unknown>[];
    return rows.map((r) => this.parseRow(r));
  }

  /** Get all memories (used for decay) */
  getAll(): Memory[] {
    this.checkClosed();
    const rows = this.db
      .prepare("SELECT * FROM memories")
      .all() as Record<string, unknown>[];
    return rows.map((r) => this.parseRow(r));
  }

  count(agent?: string): number {
    this.checkClosed();
    if (agent) {
      const row = this.db
        .prepare("SELECT COUNT(*) as count FROM memories WHERE agent = ?")
        .get(agent) as { count: number };
      return row.count;
    }
    const row = this.db
      .prepare("SELECT COUNT(*) as count FROM memories")
      .get() as { count: number };
    return row.count;
  }

  wipe(agent?: string, category?: string): void {
    this.checkClosed();
    let query = "DELETE FROM memories WHERE 1=1";
    const params: unknown[] = [];

    if (agent) {
      query += " AND agent = ?";
      params.push(agent);
    }
    if (category) {
      query += " AND category = ?";
      params.push(category);
    }

    this.db.prepare(query).run(...params);
  }

  close(): void {
    this.checkClosed();
    this.closed = true;
    this.db.close();
  }

  private parseRow(row: Record<string, unknown>): Memory {
    let embedding: number[] | null = null;
    if (row.embedding != null) {
      try {
        const blob =
          row.embedding instanceof Buffer
            ? row.embedding
            : Buffer.from(row.embedding as string);
        embedding = JSON.parse(blob.toString("utf-8"));
      } catch {
        embedding = null;
      }
    }
    return {
      id: row.id as number,
      content: row.content as string,
      category: row.category as string,
      agent: row.agent as string,
      importance: row.importance as string,
      confidence: row.confidence as number,
      skipped: (row.skipped as number) === 1,
      access_count: row.access_count as number,
      created_at: row.created_at as string,
      updated_at: row.updated_at as string,
      metadata: JSON.parse((row.metadata as string) || "{}"),
      embedding,
      ai_processed: false,
      summary: "",
      keywords: [],
      entities: [],
      relationships: [],
    };
  }
}
