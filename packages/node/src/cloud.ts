import type {
  Memory,
  RecallResult,
  RememberOptions,
  RecallOptions,
  Entity,
  EntityNeighborsResponse,
  Relationship,
  GraphPathResponse,
  GraphStats,
  GraphContextResponse,
  GraphEntitiesOptions,
  GraphNeighborsOptions,
  GraphRelationshipsOptions,
  GraphPathsOptions,
  GraphContextOptions,
} from "./types.js";

export class CloudClient {
  private baseUrl: string;
  private apiKey: string;

  constructor(cloudUrl: string, apiKey: string) {
    this.baseUrl = cloudUrl.replace(/\/+$/, "");
    this.apiKey = apiKey;
  }

  private headers(): Record<string, string> {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${this.apiKey}`,
    };
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const init: RequestInit = { method, headers: this.headers() };
    if (body !== undefined) init.body = JSON.stringify(body);

    const res = await fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`Cloud API ${res.status}: ${text}`);
    }
    const json = await res.json() as any;
    // Unwrap { memories: [...] } or { memory: {...} } or direct
    return (json.memories || json.memory || json) as T;
  }

  private getAgentId(agent?: string): string {
    return agent || "default";
  }

  async remember(content: string, options: RememberOptions = {}): Promise<Memory> {
    const body = {
      content,
      agent_id: this.getAgentId(options.agent),
      category: options.category || "general",
      importance: options.importance || "medium",
      metadata: options.metadata || {},
    };
    return this.request<Memory>("POST", "/v1/memories", body);
  }

  async recall(query: string, options: RecallOptions = {}): Promise<RecallResult[]> {
    const params = new URLSearchParams({
      query,
      agent_id: this.getAgentId(options.agent),
      limit: String(options.limit || 5),
    });
    if (options.category) params.set("category", options.category);
    return this.request<RecallResult[]>("GET", `/v1/memories/recall?${params}`);
  }

  get(id: number): Memory | undefined {
    // Synchronous interface not possible with fetch; throw descriptive error
    throw new Error("Cloud mode does not support synchronous get(). Use recall() instead.");
  }

  update(id: number, content: string): void {
    throw new Error("Cloud mode does not support synchronous update().");
  }

  async delete(id: number): Promise<void> {
    await this.request<unknown>("DELETE", `/v1/memories/${id}`);
  }

  async count(agent?: string): Promise<number> {
    const agentId = this.getAgentId(agent);
    // Resolve agent name to ID via agents endpoint
    const agents = await this.request<any[]>("GET", "/v1/agents");
    const agentObj = agents.find((a: any) => a.name === agentId || a.id === agentId);
    if (!agentObj) return 0;
    const result = await this.request<{ count: number }>("GET", `/v1/agents/${agentObj.id}/count`);
    return result.count ?? 0;
  }

  async wipe(options: { agent?: string; category?: string } = {}): Promise<void> {
    // Wipe all memories for an agent via delete loop or dedicated endpoint
    const results = await this.recall("*", { agent: options.agent, limit: 1000 });
    for (const mem of results) {
      await this.delete(mem.id);
    }
  }

  // ─── Graph Memory Methods ──────────────────────────────────────

  async graphEntities(agent: string, options: GraphEntitiesOptions = {}): Promise<Entity[]> {
    const agentId = this.getAgentId(agent);
    const params = new URLSearchParams({ agent_id: agentId });
    if (options.type) params.set("type", options.type);
    if (options.limit) params.set("limit", String(options.limit));
    return this.request<Entity[]>("GET", `/v1/graph/entities?${params}`);
  }

  async graphEntityNeighbors(
    entityName: string,
    agent: string,
    options: GraphNeighborsOptions = {}
  ): Promise<EntityNeighborsResponse> {
    const agentId = this.getAgentId(agent);
    const params = new URLSearchParams({ agent_id: agentId });
    if (options.depth) params.set("depth", String(options.depth));
    const encoded = encodeURIComponent(entityName);
    return this.request<EntityNeighborsResponse>(
      "GET",
      `/v1/graph/entities/${encoded}/neighbors?${params}`
    );
  }

  async graphRelationships(
    agent: string,
    options: GraphRelationshipsOptions = {}
  ): Promise<Relationship[]> {
    const agentId = this.getAgentId(agent);
    const params = new URLSearchParams({ agent_id: agentId });
    if (options.source) params.set("source", options.source);
    if (options.target) params.set("target", options.target);
    if (options.limit) params.set("limit", String(options.limit));
    return this.request<Relationship[]>("GET", `/v1/graph/relationships?${params}`);
  }

  async graphPaths(
    agent: string,
    from: string,
    to: string,
    options: GraphPathsOptions = {}
  ): Promise<GraphPathResponse> {
    const agentId = this.getAgentId(agent);
    const params = new URLSearchParams({
      agent_id: agentId,
      from,
      to,
    });
    if (options.max_depth) params.set("max_depth", String(options.max_depth));
    return this.request<GraphPathResponse>("GET", `/v1/graph/paths?${params}`);
  }

  async graphStats(agent: string): Promise<GraphStats> {
    const agentId = this.getAgentId(agent);
    const params = new URLSearchParams({ agent_id: agentId });
    return this.request<GraphStats>("GET", `/v1/graph/stats?${params}`);
  }

  async graphContext(
    agent: string,
    query: string,
    options: GraphContextOptions = {}
  ): Promise<GraphContextResponse> {
    const agentId = this.getAgentId(agent);
    const params = new URLSearchParams({ agent_id: agentId, query });
    if (options.limit) params.set("limit", String(options.limit));
    return this.request<GraphContextResponse>("GET", `/v1/graph/context?${params}`);
  }

  close(): void {
    // No-op for cloud client
  }
}
