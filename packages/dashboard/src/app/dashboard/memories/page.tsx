"use client";

import { useEffect, useState } from "react";
import {
  listAgents,
  searchMemories,
  deleteMemory,
  storeMemory,
  type Agent,
  type RecallResult,
} from "@/lib/api";

const CATEGORIES = [
  "fact", "preference", "instruction", "context", "episodic", "semantic",
];

export default function MemoriesPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [results, setResults] = useState<RecallResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<number | null>(null);

  // Store memory form
  const [storeContent, setStoreContent] = useState("");
  const [storeCategory, setStoreCategory] = useState("");
  const [storeImportance, setStoreImportance] = useState("medium");
  const [storing, setStoring] = useState(false);
  const [showStore, setShowStore] = useState(false);

  useEffect(() => {
    listAgents().then(setAgents).catch(() => {});
  }, []);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || !selectedAgent) {
      setError("Enter a query and select an agent");
      return;
    }
    setSearching(true);
    setError("");
    try {
      const data = await searchMemories(query, selectedAgent, category || undefined);
      setResults(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this memory?")) return;
    setDeleting(id);
    try {
      await deleteMemory(id);
      setResults((prev) => prev.filter((r) => r.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    } finally {
      setDeleting(null);
    }
  }

  async function handleStore(e: React.FormEvent) {
    e.preventDefault();
    if (!storeContent.trim() || !selectedAgent) return;
    setStoring(true);
    try {
      await storeMemory({
        content: storeContent.trim(),
        agent_id: selectedAgent,
        category: storeCategory || undefined,
        importance: storeImportance,
      });
      setStoreContent("");
      setStoreCategory("");
      setStoreImportance("medium");
      setShowStore(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to store");
    } finally {
      setStoring(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Memories</h1>
          <p className="text-[var(--color-text-muted)] text-sm mt-1">
            Search and manage agent memories
          </p>
        </div>
        <button
          onClick={() => setShowStore(!showStore)}
          className="px-4 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] transition-colors"
        >
          + Store Memory
        </button>
      </div>

      {/* Store memory form */}
      {showStore && (
        <form
          onSubmit={handleStore}
          className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)] space-y-3"
        >
          <textarea
            placeholder="Memory content..."
            value={storeContent}
            onChange={(e) => setStoreContent(e.target.value)}
            className="w-full h-24 resize-none"
            required
          />
          <div className="flex flex-wrap gap-3">
            <select value={storeCategory} onChange={(e) => setStoreCategory(e.target.value)}>
              <option value="">Auto-categorize</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <select value={storeImportance} onChange={(e) => setStoreImportance(e.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            <button
              type="submit"
              disabled={storing || !storeContent.trim() || !selectedAgent}
              className="px-4 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] disabled:opacity-50"
            >
              {storing ? "Storing..." : "Store"}
            </button>
          </div>
        </form>
      )}

      {/* Search form */}
      <form
        onSubmit={handleSearch}
        className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]"
      >
        <div className="flex flex-wrap gap-3">
          <input
            type="text"
            placeholder="Search memories..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
          >
            <option value="">Select agent</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <button
            type="submit"
            disabled={searching || !selectedAgent}
            className="px-4 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] disabled:opacity-50 whitespace-nowrap"
          >
            {searching ? "Searching..." : "Search"}
          </button>
        </div>
      </form>

      {error && <p className="text-[var(--color-danger)] text-sm">{error}</p>}

      {/* Results */}
      <div className="space-y-2">
        {results.map((r) => (
          <div
            key={r.id}
            className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm leading-relaxed">{r.content}</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-[var(--color-text-muted)]">
                  <span className="px-2 py-0.5 rounded bg-[var(--color-accent)]/10 text-[var(--color-accent)]">
                    {r.category}
                  </span>
                  <span>Score: {(r.score * 100).toFixed(1)}%</span>
                  <span>Confidence: {(r.confidence * 100).toFixed(0)}%</span>
                  <span>{r.importance}</span>
                  <span>{new Date(r.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <button
                onClick={() => handleDelete(r.id)}
                disabled={deleting === r.id}
                className="px-2 py-1 rounded text-xs text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10 disabled:opacity-50 shrink-0"
              >
                {deleting === r.id ? "..." : "×"}
              </button>
            </div>
          </div>
        ))}

        {results.length === 0 && !searching && selectedAgent && query && (
          <div className="text-center py-8 text-[var(--color-text-muted)] text-sm">
            No memories found
          </div>
        )}
      </div>
    </div>
  );
}
