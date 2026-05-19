import Database from "better-sqlite3";
import path from "path";
import os from "os";
import type { Memory } from "./types.js";

const DEFAULT_DB_PATH = path.join(
  os.homedir(),
  ".agentrecall",
  "memories.db"
);

export class Storage {
  private db: Database.Database;

  constructor(dbPath?: string) {
    const dir = path.dirname(dbPath || DEFAULT_DB_PATH);
    require("fs").mkdirSync(dir, { recursive: true });

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
        skip INTEGER NOT NULL DEFAULT 0,
        access_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        metadata TEXT NOT NULL DEFAULT '{}'
      );

      CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent);
      CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
      CREATE INDEX IF NOT EXISTS idx_memories_skip ON memories(skip);
    `);
  }

  insert(
    content: string,
    category: string,
    agent: string,
    importance: string,
    metadata: Record<string, unknown> = {}
  ): number {
    const stmt = this.db.prepare(`
      INSERT INTO memories (content, category, agent, importance, metadata)
      VALUES (?, ?, ?, ?, ?)
    `);
    const result = stmt.run(
      content,
      category,
      agent,
      importance,
      JSON.stringify(metadata)
    );
    return Number(result.lastInsertRowid);
  }

  get(id: number): Memory | undefined {
    const row = this.db
      .prepare("SELECT * FROM memories WHERE id = ?")
      .get(id) as Record<string, unknown> | undefined;
    if (!row) return undefined;
    return this.parseRow(row);
  }

  update(
    id: number,
    updates: Partial<Pick<Memory, "content" | "confidence" | "skip" | "access_count">>
  ): void {
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
    if (updates.skip !== undefined) {
      sets.push("skip = ?");
      values.push(updates.skip ? 1 : 0);
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
    this.db.prepare("DELETE FROM memories WHERE id = ?").run(id);
  }

  search(
    agent: string,
    category?: string,
    limit: number = 10,
    skip: boolean = true
  ): Memory[] {
    let query = "SELECT * FROM memories WHERE agent = ?";
    const params: unknown[] = [agent];

    if (category) {
      query += " AND category = ?";
      params.push(category);
    }
    if (skip) {
      query += " AND skip = 0";
    }

    query += " ORDER BY confidence DESC, access_count DESC, created_at DESC";
    query += " LIMIT ?";
    params.push(limit);

    const rows = this.db.prepare(query).all(...params) as Record<string, unknown>[];
    return rows.map((r) => this.parseRow(r));
  }

  count(agent?: string): number {
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
    this.db.close();
  }

  private parseRow(row: Record<string, unknown>): Memory {
    return {
      id: row.id as number,
      content: row.content as string,
      category: row.category as string,
      agent: row.agent as string,
      importance: row.importance as string,
      confidence: row.confidence as number,
      skip: (row.skip as number) === 1,
      access_count: row.access_count as number,
      created_at: row.created_at as string,
      updated_at: row.updated_at as string,
      metadata: JSON.parse((row.metadata as string) || "{}"),
    };
  }
}
