"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signIn, signUp, loginWithApiKey } from "@/lib/supabase";

export default function LoginPage() {
  const [authTab, setAuthTab] = useState<"human" | "agent">("human");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [magicSent, setMagicSent] = useState(false);
  const router = useRouter();

  async function handleEmail(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (mode === "signup") {
        await signUp(email, password);
        setMagicSent(true);
      } else {
        await signIn(email, password);
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    }
    setLoading(false);
  }

  async function handleApiKey(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await loginWithApiKey(apiKey);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "API key authentication failed");
    }
    setLoading(false);
  }

  if (magicSent) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <h1 className="text-2xl font-bold text-[var(--color-accent)]">
            Account created!
          </h1>
          <p className="text-[var(--color-text-muted)] text-sm">
            You can now sign in with <strong>{email}</strong>
          </p>
          <button
            onClick={() => {
              setMode("login");
              setMagicSent(false);
            }}
            className="text-[var(--color-accent)] hover:underline text-sm"
          >
            Sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">
            <span className="text-[var(--color-accent)]">A</span>gentRecall
          </h1>
          <p className="text-[var(--color-text-muted)] text-sm mt-1">
            Sign in to your dashboard
          </p>
        </div>

        {/* Auth Tab Toggle */}
        <div className="flex rounded-lg overflow-hidden border border-[var(--color-border)] bg-[var(--color-surface)]">
          <button
            onClick={() => { setAuthTab("human"); setError(""); }}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              authTab === "human"
                ? "bg-[var(--color-accent)] text-white"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            }`}
          >
            👤 Human
          </button>
          <button
            onClick={() => { setAuthTab("agent"); setError(""); }}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              authTab === "agent"
                ? "bg-[var(--color-accent)] text-white"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            }`}
          >
            🤖 Agent
          </button>
        </div>

        {/* Human Login */}
        {authTab === "human" && (
          <form onSubmit={handleEmail} className="space-y-3">
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full"
            />
            {error && (
              <p className="text-[var(--color-danger)] text-xs">{error}</p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-sm font-medium transition-colors disabled:opacity-50"
            >
              {loading ? "..." : mode === "login" ? "Sign In" : "Create Account"}
            </button>
            <p className="text-center text-xs text-[var(--color-text-muted)]">
              {mode === "login"
                ? "Don't have an account?"
                : "Already have an account?"}{" "}
              <button
                type="button"
                onClick={() => {
                  setMode(mode === "login" ? "signup" : "login");
                  setError("");
                }}
                className="text-[var(--color-accent)] hover:underline"
              >
                {mode === "login" ? "Sign up" : "Sign in"}
              </button>
            </p>
          </form>
        )}

        {/* Agent API Key Login */}
        {authTab === "agent" && (
          <form onSubmit={handleApiKey} className="space-y-3">
            <p className="text-xs text-[var(--color-text-muted)] text-center">
              Paste your API key (ark_...) to authenticate
            </p>
            <input
              type="password"
              placeholder="ark_..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
              className="w-full font-mono text-sm"
            />
            {error && (
              <p className="text-[var(--color-danger)] text-xs">{error}</p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-sm font-medium transition-colors disabled:opacity-50"
            >
              {loading ? "..." : "Authenticate with API Key"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
