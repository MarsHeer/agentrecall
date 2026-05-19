"use client";

import { getUser, signOut } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function Header() {
  const [email, setEmail] = useState<string>("");
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    getUser().then((u) => {
      if (u?.email) setEmail(u.email);
    });
  }, []);

  async function handleSignOut() {
    await signOut();
    router.push("/login");
  }

  return (
    <header className="h-14 border-b border-[var(--color-border)] bg-[var(--color-bg-card)] flex items-center justify-between px-4 lg:px-6">
      {/* Mobile sidebar toggle */}
      <button
        onClick={() => {
          const el = document.getElementById("mobile-sidebar");
          el?.classList.toggle("hidden");
          el?.classList.toggle("fixed");
        }}
        className="lg:hidden text-[var(--color-text-muted)] hover:text-[var(--color-text)] p-1"
      >
        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 6h14M3 10h14M3 14h14" />
        </svg>
      </button>

      <div className="hidden lg:block" />

      <div className="relative">
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
        >
          <span className="w-7 h-7 rounded-full bg-[var(--color-accent)]/20 text-[var(--color-accent)] flex items-center justify-center text-xs font-medium">
            {email ? email[0].toUpperCase() : "?"}
          </span>
          <span className="max-w-[140px] truncate hidden sm:inline">{email}</span>
        </button>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 top-full mt-2 w-44 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg shadow-xl z-50 py-1">
              <button
                onClick={handleSignOut}
                className="w-full text-left px-4 py-2 text-sm text-[var(--color-danger)] hover:bg-[var(--color-bg-hover)]"
              >
                Sign out
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
