export interface Memory {
  id: number;
  content: string;
  category: string;
  agent: string;
  importance: string;
  confidence: number;
  skip: boolean;
  access_count: number;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface RecallResult extends Memory {
  score: number;
}

export interface RememberOptions {
  agent?: string;
  category?: string;
  importance?: string;
  metadata?: Record<string, unknown>;
}

export interface RecallOptions {
  agent?: string;
  category?: string;
  limit?: number;
  min_score?: number;
  skip_penalty?: number;
}

export type EmbeddingFunction = (text: string) => Promise<number[]>;
