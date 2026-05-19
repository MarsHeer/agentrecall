import { Storage } from "./storage.js";
import { classify } from "./classifier.js";
import type {
  Memory,
  RecallResult,
  RememberOptions,
  RecallOptions,
  EmbeddingFunction,
} from "./types.js";

const IMPORTANCE_WEIGHTS: Record<string, number> = {
  high: 1.3,
  medium: 1.0,
  low: 0.7,
};

export interface MemoryStoreOptions {
  dbPath?: string;
  embed?: EmbeddingFunction;
  decay_rate?: number;
  min_confidence?: number;
}

export class MemoryStore {
  private storage: Storage;
  private embedFn: EmbeddingFunction | null;
  private closed = false;
  private decayRate: number;
  private minConfidence: number;

  constructor(options: MemoryStoreOptions = {}) {
    this.storage = new Storage(options.dbPath);
    this.embedFn = options.embed || null;
    this.decayRate = options.decay_rate ?? 0.01;
    this.minConfidence = options.min_confidence ?? 0.1;
  }

  private checkClosed(): void {
    if (this.closed) {
      throw new Error("Store is closed");
    }
  }

  /**
   * Store a memory.
   * @param content - The memory text (required, non-empty)
   * @param options - Optional: agent, category, importance, metadata
   * @returns The created Memory object
   */
  async remember(
    content: string,
    options: RememberOptions = {}
  ): Promise<Memory> {
    this.checkClosed();
    if (!content || content.trim().length === 0) {
      throw new Error("Content cannot be empty");
    }

    const agent = options.agent || "default";
    const category = options.category || classify(content);
    const importance = options.importance || "medium";
    const metadata = options.metadata || {};

    // Generate embedding if function provided
    let embedding: number[] | null = null;
    if (this.embedFn) {
      try {
        embedding = await this.embedFn(content);
      } catch (e) {
        console.warn("Embedding function failed, falling back:", e);
        embedding = null;
      }
    }

    const id = this.storage.insert(
      content,
      category,
      agent,
      importance,
      metadata,
      embedding
    );

    return this.storage.get(id)!;
  }

  /**
   * Recall memories relevant to a query.
   * Runs confidence decay on all memories before scoring.
   * @param query - The search query (required, non-empty)
   * @param options - Optional: agent, category, limit, min_score
   * @returns Array of RecallResult sorted by score descending
   */
  async recall(
    query: string,
    options: RecallOptions = {}
  ): Promise<RecallResult[]> {
    this.checkClosed();
    if (!query || query.trim().length === 0) {
      throw new Error("Query cannot be empty");
    }

    const agent = options.agent || "default";
    const category = options.category;
    const limit = options.limit || 5;
    const minScore = options.min_score || 0.0;

    // Run confidence decay
    this.runDecay();

    // Get candidate memories (include skipped ones — they get penalized in scoring)
    const candidates = this.storage.search(agent, category, limit * 3, false);

    if (candidates.length === 0) return [];

    // Compute scores
    let scored: RecallResult[];

    if (this.embedFn) {
      let queryEmbedding: number[] | null = null;
      try {
        queryEmbedding = await this.embedFn(query);
      } catch (e) {
        console.warn("Embedding function failed for query, falling back:", e);
        queryEmbedding = null;
      }

      scored = candidates.map((m) => ({
        ...m,
        score: this.computeScore(m, queryEmbedding),
      }));
    } else {
      scored = candidates.map((m) => ({
        ...m,
        score: this.computeScore(m, null),
      }));
    }

    // Filter, sort, and limit
    const results = scored
      .filter((r) => r.score >= minScore)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);

    return results;
  }

  /**
   * Update a memory's content.
   * @param id - Memory ID
   * @param content - New content (required, non-empty)
   */
  update(id: number, content: string): void {
    this.checkClosed();
    if (!content || content.trim().length === 0) {
      throw new Error("Content cannot be empty");
    }
    this.storage.update(id, { content });
  }

  /**
   * Skip/ignore a memory (reduces its recall score by 80%).
   * @param id - Memory ID
   */
  skip(id: number): void {
    this.checkClosed();
    this.storage.update(id, { skipped: true });
  }

  /**
   * Unskip a memory.
   * @param id - Memory ID
   */
  unskip(id: number): void {
    this.checkClosed();
    this.storage.update(id, { skipped: false });
  }

  /**
   * Delete a memory permanently.
   * @param id - Memory ID
   */
  delete(id: number): void {
    this.checkClosed();
    this.storage.delete(id);
  }

  /**
   * Get a single memory by ID.
   * @param id - Memory ID
   * @returns Memory object or undefined if not found
   */
  get(id: number): Memory | undefined {
    this.checkClosed();
    return this.storage.get(id);
  }

  /**
   * Count memories, optionally filtered by agent.
   * @param agent - Optional agent filter
   * @returns Number of memories
   */
  count(agent?: string): number {
    this.checkClosed();
    return this.storage.count(agent);
  }

  /**
   * Delete memories. Filter by agent and/or category. If no filters, delete ALL.
   * @param options - Optional: agent, category
   */
  wipe(options: { agent?: string; category?: string } = {}): void {
    this.checkClosed();
    this.storage.wipe(options.agent, options.category);
  }

  /**
   * Close database connection.
   */
  close(): void {
    if (this.closed) return;
    this.closed = true;
    this.storage.close();
  }

  /**
   * Run confidence decay on all memories.
   * Formula: new_confidence = confidence × (1 - decay_rate)
   * Memories below min_confidence are auto-deleted.
   */
  private runDecay(): void {
    const allMemories = this.storage.getAll();
    const toDelete: number[] = [];

    for (const mem of allMemories) {
      const newConfidence = mem.confidence * (1 - this.decayRate);
      if (newConfidence < this.minConfidence) {
        toDelete.push(mem.id);
      } else if (Math.abs(newConfidence - mem.confidence) > 1e-10) {
        this.storage.update(mem.id, { confidence: newConfidence });
      }
    }

    if (toDelete.length > 0) {
      this.storage.deleteMany(toDelete);
    }
  }

  /**
   * Compute composite score for a memory per API spec:
   * score = similarity × confidence × importance_weight × recency × skip_penalty
   */
  private computeScore(
    memory: Memory,
    queryEmbedding: number[] | null
  ): number {
    // Similarity: cosine similarity of embeddings, or 1.0 if no embeddings
    let similarity = 1.0;
    if (queryEmbedding && memory.embedding) {
      similarity = cosineSimilarity(queryEmbedding, memory.embedding);
      if (isNaN(similarity)) similarity = 0;
    }
    // If queryEmbedding but no memory.embedding, similarity stays at 1.0 (lenient fallback)

    // Confidence
    const confidence = memory.confidence;

    // Importance weight: high=1.3, medium=1.0, low=0.7
    const importanceWeight = IMPORTANCE_WEIGHTS[memory.importance] ?? 1.0;

    // Recency = 1 / (1 + days_since_creation × 0.05)
    const days = this.daysSince(memory.created_at);
    const recency = 1 / (1 + days * 0.05);

    // Skip penalty: 0.2 if skipped, 1.0 if not
    const skipPenalty = memory.skipped ? 0.2 : 1.0;

    return similarity * confidence * importanceWeight * recency * skipPenalty;
  }

  private daysSince(dateStr: string): number {
    const date = new Date(dateStr + "Z"); // ensure UTC
    const now = new Date();
    return Math.max(
      0,
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    );
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
  const denominator = Math.sqrt(normA) * Math.sqrt(normB);
  if (denominator === 0) return 0;
  return dot / denominator;
}
