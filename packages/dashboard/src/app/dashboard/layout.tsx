"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getUser } from "@/lib/supabase";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [ready, setReady] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    getUser().then((u) => {
      if (!u) router.replace("/login");
      else setReady(true);
    });
  }, [router]);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Mobile sidebar overlay */}
      {menuOpen && (
        <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={() => setMenuOpen(false)} />
      )}

      {/* Mobile sidebar */}
      <div
        id="mobile-sidebar"
        className={`${
          menuOpen ? "fixed inset-0 z-40" : "hidden"
        } lg:hidden`}
      >
        <div className="w-60 h-full bg-[var(--color-bg-card)] border-r border-[var(--color-border)]">
          <MobileNav />
        </div>
      </div>

      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 lg:ml-60">
          <Header />
          {/* Mobile hamburger */}
          <button
            onClick={() => setMenuOpen(true)}
            className="lg:hidden fixed bottom-4 right-4 z-20 w-12 h-12 rounded-full bg-[var(--color-accent)] text-white shadow-lg flex items-center justify-center text-lg"
          >
            ☰
          </button>
          <main className="flex-1 p-4 lg:p-6 overflow-auto">{children}</main>
        </div>
      </div>
    </div>
  );
}

function MobileNav() {
  const pathname = usePathname();
  const nav = [
    { href: "/dashboard", label: "Overview", icon: "📊" },
    { href: "/dashboard/agents", label: "Agents", icon: "🤖" },
    { href: "/dashboard/memories", label: "Memories", icon: "🧠" },
    { href: "/dashboard/keys", label: "API Keys", icon: "🔑" },
    { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="p-5 border-b border-[var(--color-border)]">
        <span className="text-sm font-semibold">
          <span className="text-[var(--color-accent)]">A</span>gentRecall
        </span>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {nav.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          return (
            <a
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </a>
          );
        })}
      </nav>
    </div>
  );
}
