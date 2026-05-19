import { getAccessToken } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8700";

async function authFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(`${API_BASE}${path}`, { ...options, headers });
}

// ─── Usage ───────────────────────────────────────────────────────

export interface UsageStats {
  api_calls_today: number;
  memories_stored: number;
  memories_recalled: number;
  plan: string;
  limit: number;
}

export async function getUsage(): Promise<UsageStats> {
  const res = await authFetch("/v1/usage");
  if (!res.ok) throw new Error("Failed to fetch usage");
  return res.json();
}

// ─── Agents ──────────────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  memory_count: number;
  created_at: string;
  last_active_at: string | null;
}

export async function listAgents(): Promise<Agent[]> {
  const res = await authFetch("/v1/agents");
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function createAgent(name: string): Promise<Agent> {
  const res = await authFetch("/v1/agents", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create agent");
  }
  return res.json();
}

export async function deleteAgent(id: string): Promise<void> {
  const res = await authFetch(`/v1/agents/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete agent");
}

export async function countMemories(agentId: string): Promise<number> {
  const res = await authFetch(`/v1/agents/${agentId}/count`);
  if (!res.ok) throw new Error("Failed to count memories");
  const data = await res.json();
  return data.count;
}

// ─── Memories ────────────────────────────────────────────────────

export interface Memory {
  id: number;
  agent_id: string;
  content: string;
  category: string;
  importance: string;
  confidence: number;
  skipped: boolean;
  access_count: number;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface RecallResult extends Memory {
  score: number;
}

export async function searchMemories(
  query: string,
  agentId: string,
  category?: string
): Promise<RecallResult[]> {
  const params = new URLSearchParams({ query: query, agent_id: agentId });
  if (category) params.set("category", category);
  const res = await authFetch(`/v1/memories/recall?${params}`);
  if (!res.ok) throw new Error("Failed to search memories");
  return res.json();
}

export async function getMemory(id: number): Promise<Memory> {
  const res = await authFetch(`/v1/memories/${id}`);
  if (!res.ok) throw new Error("Memory not found");
  return res.json();
}

export async function deleteMemory(id: number): Promise<void> {
  const res = await authFetch(`/v1/memories/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete memory");
}

export async function storeMemory(data: {
  content: string;
  agent_id: string;
  category?: string;
  importance?: string;
  metadata?: Record<string, unknown>;
}): Promise<Memory> {
  const res = await authFetch("/v1/memories", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to store memory");
  }
  return res.json();
}

// ─── API Keys ────────────────────────────────────────────────────

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  full_key: string;
}

export async function listApiKeys(): Promise<ApiKey[]> {
  const res = await authFetch("/v1/api-keys");
  if (!res.ok) throw new Error("Failed to fetch API keys");
  return res.json();
}

export async function createApiKey(name: string): Promise<ApiKeyCreated> {
  const res = await authFetch("/v1/api-keys", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error("Failed to create API key");
  return res.json();
}

export async function deleteApiKey(id: string): Promise<void> {
  const res = await authFetch(`/v1/api-keys/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to revoke API key");
}

// ─── Graph Memory ───────────────────────────────────────────────

export interface GraphEntity {
  name: string;
  type: string;
  memory_count: number;
  first_seen: string | null;
  last_seen: string | null;
}

export interface GraphRelationship {
  source: string;
  target: string;
  relation_type: string;
  memory_ids: number[];
  strength: number;
}

export interface GraphStats {
  total_entities: number;
  total_relationships: number;
  total_memories_in_graph: number;
  entity_types: Record<string, number>;
  top_entities: { name: string; connections: number }[];
}

export interface GraphContextResult {
  entity: GraphEntity;
  memories: { summary: string; memory_id: number }[];
  connected_entities: { name: string; type: string; relationship: string }[];
}

export async function getGraphEntities(agentId: string, type?: string, limit = 50): Promise<GraphEntity[]> {
  const params = new URLSearchParams({ agent_id: agentId, limit: String(limit) });
  if (type) params.set("type", type);
  const res = await authFetch(`/v1/graph/entities?${params}`);
  if (!res.ok) throw new Error("Failed to fetch graph entities");
  return res.json();
}

export async function getGraphEntityNeighbors(
  agentId: string,
  entityName: string,
  depth = 1
): Promise<{ entity: GraphEntity | null; neighbors: any[] }> {
  const params = new URLSearchParams({ agent_id: agentId, depth: String(depth) });
  const encoded = encodeURIComponent(entityName);
  const res = await authFetch(`/v1/graph/entities/${encoded}/neighbors?${params}`);
  if (!res.ok) throw new Error("Failed to fetch entity neighbors");
  return res.json();
}

export async function getGraphRelationships(
  agentId: string,
  source?: string,
  target?: string,
  limit = 50
): Promise<GraphRelationship[]> {
  const params = new URLSearchParams({ agent_id: agentId, limit: String(limit) });
  if (source) params.set("source", source);
  if (target) params.set("target", target);
  const res = await authFetch(`/v1/graph/relationships?${params}`);
  if (!res.ok) throw new Error("Failed to fetch graph relationships");
  return res.json();
}

export async function getGraphPaths(
  agentId: string,
  from: string,
  to: string,
  maxDepth = 5
): Promise<{ path: any[]; length: number }> {
  const params = new URLSearchParams({ agent_id: agentId, from, to, max_depth: String(maxDepth) });
  const res = await authFetch(`/v1/graph/paths?${params}`);
  if (!res.ok) throw new Error("Failed to find graph path");
  return res.json();
}

export async function getGraphStats(agentId: string): Promise<GraphStats> {
  const params = new URLSearchParams({ agent_id: agentId });
  const res = await authFetch(`/v1/graph/stats?${params}`);
  if (!res.ok) throw new Error("Failed to fetch graph stats");
  return res.json();
}

export async function getGraphContext(
  agentId: string,
  query: string,
  limit = 10
): Promise<{ results: GraphContextResult[] }> {
  const params = new URLSearchParams({ agent_id: agentId, query, limit: String(limit) });
  const res = await authFetch(`/v1/graph/context?${params}`);
  if (!res.ok) throw new Error("Failed to fetch graph context");
  return res.json();
}
