"use client";

import { useEffect, useState } from "react";
import {
  listApiKeys,
  createApiKey,
  deleteApiKey,
  type ApiKey,
  type ApiKeyCreated,
} from "@/lib/api";

export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      const data = await listApiKeys();
      setKeys(data);
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
      const key: ApiKeyCreated = await createApiKey(newName.trim());
      setKeys((prev) => [key, ...prev]);
      setCreatedKey(key.full_key);
      setNewName("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(id: string) {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    setRevoking(id);
    try {
      await deleteApiKey(id);
      setKeys((prev) => prev.filter((k) => k.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to revoke");
    } finally {
      setRevoking(null);
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold">API Keys</h1>
        <p className="text-[var(--color-text-muted)] text-sm mt-1">
          Manage API keys for programmatic access
        </p>
      </div>

      {/* New key alert */}
      {createdKey && (
        <div className="border border-[var(--color-success)]/30 rounded-xl p-4 bg-[var(--color-success)]/5">
          <p className="text-sm text-[var(--color-success)] font-medium mb-2">
            ✓ API key created — copy it now, it won&apos;t be shown again
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs font-mono bg-[var(--color-bg)] rounded-lg px-3 py-2 overflow-x-auto">
              {createdKey}
            </code>
            <button
              onClick={() => navigator.clipboard.writeText(createdKey)}
              className="px-3 py-2 rounded-lg border border-[var(--color-border)] text-xs hover:bg-[var(--color-bg-hover)]"
            >
              Copy
            </button>
            <button
              onClick={() => setCreatedKey(null)}
              className="px-3 py-2 rounded-lg text-xs text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)]"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Create form */}
      <form
        onSubmit={handleCreate}
        className="flex gap-3 border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]"
      >
        <input
          type="text"
          placeholder="Key name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="flex-1"
          required
        />
        <button
          type="submit"
          disabled={creating || !newName.trim()}
          className="px-4 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] disabled:opacity-50 whitespace-nowrap"
        >
          {creating ? "Creating..." : "Create Key"}
        </button>
      </form>

      {error && <p className="text-[var(--color-danger)] text-sm">{error}</p>}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-5 h-5 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : keys.length === 0 ? (
        <div className="border border-[var(--color-border)] rounded-xl p-8 bg-[var(--color-bg-card)] text-center">
          <p className="text-[var(--color-text-muted)] text-sm">No API keys yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {keys.map((key) => (
            <div
              key={key.id}
              className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)] flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium">{key.name}</p>
                <p className="text-xs text-[var(--color-text-muted)] font-mono mt-1">
                  {key.key_prefix}
                </p>
                <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)] mt-1">
                  <span>Created {new Date(key.created_at).toLocaleDateString()}</span>
                  {key.last_used_at && (
                    <>
                      <span>·</span>
                      <span>Last used {new Date(key.last_used_at).toLocaleDateString()}</span>
                    </>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleRevoke(key.id)}
                disabled={revoking === key.id}
                className="px-3 py-1.5 rounded-lg border border-[var(--color-danger)]/30 text-[var(--color-danger)] text-xs hover:bg-[var(--color-danger)]/10 transition-colors disabled:opacity-50 whitespace-nowrap"
              >
                {revoking === key.id ? "..." : "Revoke"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
