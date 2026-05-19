"use client";

import { useEffect, useState } from "react";
import { listAgents, createAgent, deleteAgent, type Agent } from "@/lib/api";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      const data = await listAgents();
      setAgents(data);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const agent = await createAgent(newName.trim());
      setAgents((prev) => [agent, ...prev]);
      setNewName("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this agent and all its memories?")) return;
    setDeleting(id);
    try {
      await deleteAgent(id);
      setAgents((prev) => prev.filter((a) => a.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold">Agents</h1>
        <p className="text-[var(--color-text-muted)] text-sm mt-1">
          Manage your AI agents
        </p>
      </div>

      {/* Create form */}
      <form
        onSubmit={handleCreate}
        className="flex gap-3 border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]"
      >
        <input
          type="text"
          placeholder="Agent name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="flex-1"
          required
        />
        <button
          type="submit"
          disabled={creating || !newName.trim()}
          className="px-4 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] transition-colors disabled:opacity-50 whitespace-nowrap"
        >
          {creating ? "Creating..." : "Create Agent"}
        </button>
      </form>

      {error && (
        <p className="text-[var(--color-danger)] text-sm">{error}</p>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-5 h-5 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : agents.length === 0 ? (
        <div className="border border-[var(--color-border)] rounded-xl p-8 bg-[var(--color-bg-card)] text-center">
          <p className="text-[var(--color-text-muted)] text-sm">No agents yet. Create one above.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)] flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <p className="font-medium truncate">{agent.name}</p>
                <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)] mt-1">
                  <span>{agent.memory_count} memories</span>
                  <span>·</span>
                  <span>{new Date(agent.created_at).toLocaleDateString()}</span>
                  {agent.last_active_at && (
                    <>
                      <span>·</span>
                      <span>
                        Active {new Date(agent.last_active_at).toLocaleDateString()}
                      </span>
                    </>
                  )}
                </div>
                <p className="text-xs text-[var(--color-text-muted)] mt-1 font-mono">
                  {agent.id}
                </p>
              </div>
              <button
                onClick={() => handleDelete(agent.id)}
                disabled={deleting === agent.id}
                className="px-3 py-1.5 rounded-lg border border-[var(--color-danger)]/30 text-[var(--color-danger)] text-xs hover:bg-[var(--color-danger)]/10 transition-colors disabled:opacity-50 whitespace-nowrap"
              >
                {deleting === agent.id ? "..." : "Delete"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
