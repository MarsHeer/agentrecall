export interface Memory {
  id: number;
  content: string;
  category: string;
  agent: string;
  importance: string;
  confidence: number;
  skipped: boolean;
  access_count: number;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  embedding: number[] | null;
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
}

export type EmbeddingFunction = (text: string) => Promise<number[]>;

export type StoreMode = 'local' | 'cloud' | 'auto';

// ─── Graph Memory Types ────────────────────────────────────────

export interface Entity {
  name: string;
  type: string;
  memory_count: number;
  first_seen: string | null;
  last_seen: string | null;
}

export interface EntityNeighbor {
  name: string;
  type: string;
  relationship_type: string;
  strength: number;
  distance: number;
}

export interface EntityNeighborsResponse {
  entity: Entity | null;
  neighbors: EntityNeighbor[];
}

export interface Relationship {
  source: string;
  target: string;
  relation_type: string;
  memory_ids: number[];
  strength: number;
}

export interface GraphPathItem {
  entity: { name: string; type: string } | null;
  relationship: { relationship_type: string } | null;
}

export interface GraphPathResponse {
  path: GraphPathItem[];
  length: number;
}

export interface GraphStats {
  total_entities: number;
  total_relationships: number;
  total_memories_in_graph: number;
  entity_types: Record<string, number>;
  top_entities: { name: string; connections: number }[];
}

export interface GraphContextMemory {
  summary: string;
  memory_id: number;
}

export interface GraphContextConnectedEntity {
  name: string;
  type: string;
  relationship: string;
}

export interface GraphContextResult {
  entity: Entity;
  memories: GraphContextMemory[];
  connected_entities: GraphContextConnectedEntity[];
}

export interface GraphContextResponse {
  results: GraphContextResult[];
}

export interface GraphEntitiesOptions {
  type?: string;
  limit?: number;
}

export interface GraphNeighborsOptions {
  depth?: number;
}

export interface GraphRelationshipsOptions {
  source?: string;
  target?: string;
  limit?: number;
}

export interface GraphPathsOptions {
  max_depth?: number;
}

export interface GraphContextOptions {
  limit?: number;
}
