"use client";

import { useEffect, useState } from "react";
import { getUsage, listAgents, type UsageStats, type Agent } from "@/lib/api";

export default function DashboardPage() {
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [u, a] = await Promise.all([getUsage(), listAgents()]);
        setUsage(u);
        setAgents(a);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-5 h-5 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-20 text-center">
        <p className="text-[var(--color-danger)]">{error}</p>
      </div>
    );
  }

  const totalMemories = agents.reduce((s, a) => s + a.memory_count, 0);

  const stats = [
    { label: "Total Memories", value: totalMemories.toLocaleString(), icon: "🧠" },
    { label: "Agents", value: agents.length.toString(), icon: "🤖" },
    { label: "API Calls Today", value: (usage?.api_calls_today ?? 0).toLocaleString(), icon: "📈" },
    { label: "Plan", value: (usage?.plan ?? "free").charAt(0).toUpperCase() + (usage?.plan ?? "free").slice(1), icon: "💳" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Dashboard</h1>
        <p className="text-[var(--color-text-muted)] text-sm mt-1">Overview of your AgentRecall cloud</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div
            key={s.label}
            className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">{s.label}</span>
              <span className="text-lg">{s.icon}</span>
            </div>
            <p className="text-2xl font-bold">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Usage bar */}
      {usage && usage.plan === "free" && usage.limit > 0 && (
        <div className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm">API Calls Today</span>
            <span className="text-xs text-[var(--color-text-muted)]">
              {usage.api_calls_today} / {usage.limit}
            </span>
          </div>
          <div className="w-full h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--color-accent)] rounded-full transition-all"
              style={{
                width: `${Math.min((usage.api_calls_today / usage.limit) * 100, 100)}%`,
              }}
            />
          </div>
          {usage.api_calls_today / usage.limit > 0.8 && (
            <p className="text-xs text-[var(--color-danger)] mt-2">
              Approaching daily limit.{" "}
              <a href="/dashboard/settings" className="underline">Upgrade to Pro</a>
            </p>
          )}
        </div>
      )}

      {/* Recent agents */}
      {agents.length > 0 && (
        <div className="border border-[var(--color-border)] rounded-xl bg-[var(--color-bg-card)]">
          <div className="px-4 py-3 border-b border-[var(--color-border)]">
            <h2 className="text-sm font-semibold">Your Agents</h2>
          </div>
          <div className="divide-y divide-[var(--color-border)]">
            {agents.slice(0, 5).map((a) => (
              <div key={a.id} className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{a.name}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {a.memory_count} memories
                  </p>
                </div>
                <a
                  href="/dashboard/agents"
                  className="text-xs text-[var(--color-accent)] hover:underline"
                >
                  View
                </a>
              </div>
            ))}
          </div>
        </div>
      )}

      {agents.length === 0 && !loading && (
        <div className="border border-[var(--color-border)] rounded-xl p-8 bg-[var(--color-bg-card)] text-center">
          <p className="text-[var(--color-text-muted)] text-sm mb-3">No agents yet</p>
          <a
            href="/dashboard/agents"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] transition-colors"
          >
            Create your first agent
          </a>
        </div>
      )}
    </div>
  );
}
