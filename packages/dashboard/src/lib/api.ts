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
  const params = new URLSearchParams({ q: query, agent_id: agentId });
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
