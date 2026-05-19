"use client";

import { useEffect, useState } from "react";
import { getUsage, type UsageStats } from "@/lib/api";
import { getUser, signOut } from "@/lib/supabase";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [upgrading, setUpgrading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    async function load() {
      try {
        const [u, user] = await Promise.all([getUsage(), import("@/lib/supabase").then(m => m.getUser())]);
        setUsage(u);
        if (user?.email) setEmail(user.email);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleUpgrade() {
    setUpgrading(true);
    try {
      // In production this would hit a /v1/billing/checkout endpoint
      // that creates a Stripe Checkout session and redirects
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8700";
      const { getAccessToken } = await import("@/lib/supabase");
      const token = await getAccessToken();
      const res = await fetch(`${API_BASE}/v1/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.url) window.location.href = data.url;
      } else {
        setError("Checkout not available yet. Coming soon!");
      }
    } catch {
      setError("Checkout not available yet. Coming soon!");
    } finally {
      setUpgrading(false);
    }
  }

  async function handleSignOut() {
    await signOut();
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-5 h-5 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold">Settings</h1>
        <p className="text-[var(--color-text-muted)] text-sm mt-1">
          Account and subscription settings
        </p>
      </div>

      {error && (
        <div className="border border-[var(--color-danger)]/30 rounded-xl p-4 bg-[var(--color-danger)]/5">
          <p className="text-sm text-[var(--color-danger)]">{error}</p>
        </div>
      )}

      {/* Account */}
      <div className="border border-[var(--color-border)] rounded-xl p-5 bg-[var(--color-bg-card)] space-y-4">
        <h2 className="text-sm font-semibold">Account</h2>
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-full bg-[var(--color-accent)]/20 text-[var(--color-accent)] flex items-center justify-center text-lg font-medium">
            {email ? email[0].toUpperCase() : "?"}
          </span>
          <div>
            <p className="text-sm font-medium">{email}</p>
            <p className="text-xs text-[var(--color-text-muted)]">Signed in with Google</p>
          </div>
        </div>
        <button
          onClick={handleSignOut}
          className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-sm text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] transition-colors"
        >
          Sign Out
        </button>
      </div>

      {/* Subscription */}
      <div className="border border-[var(--color-border)] rounded-xl p-5 bg-[var(--color-bg-card)] space-y-4">
        <h2 className="text-sm font-semibold">Subscription</h2>

        {usage?.plan === "pro" ? (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-success)]/5 border border-[var(--color-success)]/20">
            <span className="text-[var(--color-success)]">✓</span>
            <div>
              <p className="text-sm font-medium">Pro Plan</p>
              <p className="text-xs text-[var(--color-text-muted)]">
                Unlimited memories and API calls
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-sm">Free</span>
              <div className="text-xs text-[var(--color-text-muted)]">
                {usage?.limit ?? 100} API calls/day, 1000 memories
              </div>
            </div>

            <div className="border border-[var(--color-accent)]/30 rounded-xl p-5 bg-[var(--color-accent)]/5">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">Pro — $3/month</h3>
                  <ul className="text-xs text-[var(--color-text-muted)] mt-2 space-y-1">
                    <li>• Unlimited memories</li>
                    <li>• Unlimited API calls</li>
                    <li>• Priority support</li>
                    <li>• Advanced recall algorithms</li>
                  </ul>
                </div>
                <button
                  onClick={handleUpgrade}
                  disabled={upgrading}
                  className="px-5 py-2.5 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] transition-colors disabled:opacity-50 shrink-0"
                >
                  {upgrading ? "Redirecting..." : "Upgrade to Pro"}
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Usage details */}
      <div className="border border-[var(--color-border)] rounded-xl p-5 bg-[var(--color-bg-card)] space-y-4">
        <h2 className="text-sm font-semibold">Today&apos;s Usage</h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-[var(--color-text-muted)]">API Calls</p>
            <p className="text-lg font-bold mt-1">{usage?.api_calls_today ?? 0}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-muted)]">Memories Stored</p>
            <p className="text-lg font-bold mt-1">{usage?.memories_stored ?? 0}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-muted)]">Memories Recalled</p>
            <p className="text-lg font-bold mt-1">{usage?.memories_recalled ?? 0}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
