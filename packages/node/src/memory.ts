import { Storage } from "./storage.js";
import { classify } from "./classifier.js";
import type {
  Memory,
  RecallResult,
  RememberOptions,
  RecallOptions,
  EmbeddingFunction,
} from "./types.js";

export interface MemoryStoreOptions {
  dbPath?: string;
  embed?: EmbeddingFunction;
}

export class MemoryStore {
  private storage: Storage;
  private embedFn: EmbeddingFunction | null;
  private embeddings: Map<number, number[]> = new Map();

  constructor(options: MemoryStoreOptions = {}) {
    this.storage = new Storage(options.dbPath);
    this.embedFn = options.embed || null;
  }

  /**
   * Store a memory.
   */
  async remember(
    content: string,
    options: RememberOptions = {}
  ): Promise<Memory> {
    const agent = options.agent || "default";
    const category = options.category || classify(content);
    const importance = options.importance || "medium";
    const metadata = options.metadata || {};

    const id = this.storage.insert(content, category, agent, importance, metadata);

    // Generate embedding if function provided
    if (this.embedFn) {
      const embedding = await this.embedFn(content);
      this.embeddings.set(id, embedding);
    }

    return this.storage.get(id)!;
  }

  /**
   * Recall memories relevant to a query.
   */
  async recall(
    query: string,
    options: RecallOptions = {}
  ): Promise<RecallResult[]> {
    const agent = options.agent || "default";
    const category = options.category;
    const limit = options.limit || 5;
    const minScore = options.min_score || 0.0;
    const skipPenalty = options.skip_penalty || 0.5;

    // Get candidate memories
    const candidates = this.storage.search(agent, category, limit * 3, true);

    if (candidates.length === 0) return [];

    // If no embedding function, return by confidence + access_count
    if (!this.embedFn) {
      const scored = candidates.map((m) => ({
        ...m,
        score: this.basicScore(m),
      }));
      return scored
        .filter((r) => r.score >= minScore)
        .sort((a, b) => b.score - a.score)
        .slice(0, limit);
    }

    // Semantic scoring with embeddings
    const queryEmbedding = await this.embedFn(query);
    const scored = candidates.map((m) => {
      const memEmbedding = this.embeddings.get(m.id);
      const similarity = memEmbedding
        ? cosineSimilarity(queryEmbedding, memEmbedding)
        : 0;

      const skipPenaltyValue = m.skip ? skipPenalty : 1.0;
      const score = similarity * m.confidence * skipPenaltyValue;

      return { ...m, score };
    });

    return scored
      .filter((r) => r.score >= minScore)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  /**
   * Update a memory's content.
   */
  update(id: number, content: string): void {
    this.storage.update(id, { content });
  }

  /**
   * Skip/ignore a memory (reduces its recall score).
   */
  skip(id: number): void {
    this.storage.update(id, { skip: true });
  }

  /**
   * Unskip a memory.
   */
  unskip(id: number): void {
    this.storage.update(id, { skip: false });
  }

  /**
   * Delete a memory.
   */
  delete(id: number): void {
    this.storage.delete(id);
    this.embeddings.delete(id);
  }

  /**
   * Get a single memory by ID.
   */
  get(id: number): Memory | undefined {
    return this.storage.get(id);
  }

  /**
   * Count memories for an agent.
   */
  count(agent?: string): number {
    return this.storage.count(agent);
  }

  /**
   * Wipe all memories (optionally filtered by agent/category).
   */
  wipe(options: { agent?: string; category?: string } = {}): void {
    this.storage.wipe(options.agent, options.category);
    if (!options.agent && !options.category) {
      this.embeddings.clear();
    }
  }

  /**
   * Close the database connection.
   */
  close(): void {
    this.storage.close();
  }

  private basicScore(memory: Memory): number {
    const recencyBoost = 1 / (1 + this.daysSince(memory.created_at) * 0.1);
    return memory.confidence * recencyBoost * (memory.skip ? 0.5 : 1.0);
  }

  private daysSince(dateStr: string): number {
    const date = new Date(dateStr);
    const now = new Date();
    return (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24);
  }
}

function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) return 0;
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}
