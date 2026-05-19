import Link from "next/link";

/* ─────────────────────────── DATA ─────────────────────────── */

const FEATURES = [
  {
    icon: "🔗",
    title: "Graph Memory",
    description:
      "Neo4j-powered relationship graph between memories. Memories aren't just stored — they're connected. Query by traversal, find hidden connections across your agent's entire history.",
    code: `<span class="comment">// Traverse memory relationships</span>
<span class="keyword">const</span> related <span class="operator">=</span> <span class="keyword">await</span> recall.<span class="function">traverse</span>(memoryId, {
  depth<span class="operator">:</span> <span class="variable">3</span>,
  relationship<span class="operator">:</span> <span class="string">"relates_to"</span>,
  filter<span class="operator">:</span> { topic<span class="operator">:</span> <span class="string">"project_alpha"</span> }
});`,
  },
  {
    icon: "🧠",
    title: "AI Memory Processing",
    description:
      "Qwen2.5-7B extracts entities, detects relationships, and auto-categorizes every memory. Your agent's knowledge base is enriched automatically — no manual tagging needed.",
    code: `<span class="comment">// Memories are processed automatically</span>
<span class="keyword">await</span> recall.<span class="function">store</span>({
  content<span class="operator">:</span> <span class="string">"User prefers dark mode and React"</span>,
  agentId<span class="operator">:</span> <span class="string">"support-agent"</span>
});
<span class="comment">// → entities: [dark_mode, React]</span>
<span class="comment">// → relationships: [user→preference→dark_mode]</span>
<span class="comment">// → category: "user_preferences"</span>`,
  },
  {
    icon: "🔍",
    title: "Semantic Search",
    description:
      "Vector embeddings plus full-text search. Find memories by meaning, not just keywords. Your agent understands context and retrieves what's truly relevant.",
    code: `<span class="comment">// Search by meaning, not keywords</span>
<span class="keyword">const</span> results <span class="operator">=</span> <span class="keyword">await</span> recall.<span class="function">search</span>({
  query<span class="operator">:</span> <span class="string">"what did we discuss about pricing?"</span>,
  agentId<span class="operator">:</span> <span class="string">"support-agent"</span>,
  limit<span class="operator">:</span> <span class="variable">5</span>,
  threshold<span class="operator">:</span> <span class="variable">0.7</span>
});`,
  },
  {
    icon: "☁️",
    title: "Cloud API",
    description:
      "RESTful API with authentication, usage tracking, and multi-agent support. Deploy in minutes, scale to millions of memories. Built for production workloads.",
    code: `<span class="comment">// RESTful API with auth</span>
<span class="keyword">const</span> recall <span class="operator">=</span> <span class="keyword">new</span> <span class="type">AgentRecall</span>({
  mode<span class="operator">:</span> <span class="string">"cloud"</span>,
  apiKey<span class="operator">:</span> process.env.<span class="variable">AGENTRECALL_API_KEY</span>
});

<span class="keyword">await</span> recall.<span class="function">store</span>({
  content<span class="operator">:</span> <span class="string">"Session notes from standup"</span>,
  metadata<span class="operator">:</span> { team<span class="operator">:</span> <span class="string">"engineering"</span> }
});`,
  },
  {
    icon: "🤖",
    title: "Multi-Agent Support",
    description:
      "Each agent gets isolated memory with its own namespace. Cross-agent query when needed. Perfect for teams of specialized agents working together.",
    code: `<span class="comment">// Isolated memory per agent</span>
<span class="keyword">const</span> salesAgent <span class="operator">=</span> recall.<span class="function">agent</span>(<span class="string">"sales"</span>);
<span class="keyword">const</span> supportAgent <span class="operator">=</span> recall.<span class="function">agent</span>(<span class="string">"support"</span>);

<span class="comment">// Cross-agent query when needed</span>
<span class="keyword">const</span> shared <span class="operator">=</span> <span class="keyword">await</span> recall.<span class="function">search</span>({
  query<span class="operator">:</span> <span class="string">"customer onboarding status"</span>,
  agents<span class="operator">:</span> [<span class="string">"sales"</span>, <span class="string">"support"</span>]
});`,
  },
  {
    icon: "🔑",
    title: "Bring Your Own Key",
    description:
      "Local mode uses your own Neo4j and models. Cloud mode hosted by us. Same SDK, same API. Switch between modes with a single config change.",
    code: `<span class="comment">// Local mode — your infrastructure</span>
<span class="keyword">const</span> local <span class="operator">=</span> <span class="keyword">new</span> <span class="type">AgentRecall</span>({
  mode<span class="operator">:</span> <span class="string">"local"</span>,
  neo4j<span class="operator">:</span> <span class="string">"bolt://localhost:7687"</span>,
  model<span class="operator">:</span> <span class="string">"qwen2.5-7b"</span>
});

<span class="comment">// Cloud mode — same API, hosted by us</span>
<span class="keyword">const</span> cloud <span class="operator">=</span> <span class="keyword">new</span> <span class="type">AgentRecall</span>({
  mode<span class="operator">:</span> <span class="string">"cloud"</span>,
  apiKey<span class="operator">:</span> process.env.<span class="variable">AGENTRECALL_API_KEY</span>
});`,
  },
];

const PRICING = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    features: [
      "1,000 memories",
      "Basic semantic search",
      "Single agent",
      "Community support",
      "Local mode (BYOK)",
    ],
    cta: "Get started for free",
    href: "https://dashboard.agentrecall.cloud",
    featured: false,
  },
  {
    name: "Pro",
    price: "$3",
    period: "/month",
    features: [
      "Unlimited memories",
      "Graph memory (Neo4j)",
      "AI memory processing",
      "Smart semantic search",
      "Multi-agent support",
      "Cloud API access",
      "Priority support",
    ],
    cta: "Create Pro Account",
    href: "https://dashboard.agentrecall.cloud",
    featured: true,
  },
];

/* ─────────────────────── COMPONENTS ──────────────────────── */

function Navbar() {
  return (
    <nav
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        padding: "16px 0",
        background: "rgba(10, 10, 15, 0.8)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 24 }}>🧠</span>
          <span
            style={{
              fontSize: 20,
              fontWeight: 700,
              color: "white",
              letterSpacing: "-0.02em",
            }}
          >
            AgentRecall
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
          <a href="#features" className="nav-link">
            Features
          </a>
          <a href="#code" className="nav-link">
            Code
          </a>
          <a href="#pricing" className="nav-link">
            Pricing
          </a>
          <a href="https://docs.agentrecall.cloud" className="nav-link">
            Docs
          </a>
          <a
            href="https://dashboard.agentrecall.cloud"
            className="btn-primary"
            style={{ padding: "8px 20px", fontSize: 14 }}
          >
            Dashboard →
          </a>
        </div>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section
      className="hero-gradient grid-bg"
      style={{ paddingTop: 160, paddingBottom: 100, position: "relative" }}
    >
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px", textAlign: "center" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 16px",
            borderRadius: 999,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            fontSize: 13,
            color: "var(--text-dim)",
            marginBottom: 32,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#22c55e",
              display: "inline-block",
            }}
          />
          Open source memory SDK for AI agents
        </div>

        <h1
          style={{
            fontSize: "clamp(40px, 6vw, 72px)",
            fontWeight: 800,
            lineHeight: 1.1,
            letterSpacing: "-0.03em",
            marginBottom: 24,
            maxWidth: 800,
            margin: "0 auto 24px",
          }}
        >
          Your agents forget{" "}
          <span className="gradient-text">everything</span>
          <br />
          between sessions.
        </h1>

        <p
          style={{
            fontSize: 20,
            lineHeight: 1.6,
            color: "var(--text-dim)",
            maxWidth: 640,
            margin: "0 auto 40px",
          }}
        >
          AgentRecall gives your AI agents persistent, intelligent memory.
          Graph relationships, semantic search, and AI-powered processing — so
          every conversation builds on the last.
        </p>

        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <a
            href="https://dashboard.agentrecall.cloud"
            className="btn-primary"
            style={{ fontSize: 16, padding: "14px 32px" }}
          >
            Start Building Free →
          </a>
          <a
            href="#code"
            className="btn-secondary"
            style={{ fontSize: 16, padding: "14px 32px" }}
          >
            View Code →
          </a>
        </div>

        {/* Quick stats */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 48,
            marginTop: 64,
            flexWrap: "wrap",
          }}
        >
          {[
            { value: "Graph", label: "Memory" },
            { value: "Semantic", label: "Search" },
            { value: "AI", label: "Processing" },
            { value: "Multi-Agent", label: "Support" },
          ].map((stat) => (
            <div key={stat.label} style={{ textAlign: "center" }}>
              <div
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  color: "var(--purple)",
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 4 }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function QuickStart() {
  return (
    <section
      id="code"
      style={{ padding: "80px 0", borderTop: "1px solid var(--border)" }}
    >
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "0 24px" }}>
        <h2
          style={{
            fontSize: 32,
            fontWeight: 700,
            marginBottom: 8,
            letterSpacing: "-0.02em",
          }}
        >
          Three lines to persistent memory
        </h2>
        <p style={{ color: "var(--text-dim)", marginBottom: 32, fontSize: 16 }}>
          Install the SDK, initialize with your API key, and start storing
          memories. That&apos;s it.
        </p>

        <div
          className="code-block"
          style={{ marginBottom: 16 }}
          dangerouslySetInnerHTML={{
            __html: `<span class="comment"># Install</span>
<span class="function">npm</span> install agentrecall

<span class="comment"># Or with Python</span>
<span class="function">pip</span> install agentrecall`,
          }}
        />

        <div
          className="code-block"
          dangerouslySetInnerHTML={{
            __html: `<span class="keyword">import</span> { <span class="type">AgentRecall</span> } <span class="keyword">from</span> <span class="string">"agentrecall"</span>;

<span class="keyword">const</span> recall <span class="operator">=</span> <span class="keyword">new</span> <span class="type">AgentRecall</span>({
  mode<span class="operator">:</span> <span class="string">"cloud"</span>,
  apiKey<span class="operator">:</span> process.env.<span class="variable">AGENTRECALL_API_KEY</span>
});

<span class="comment">// Store a memory — AI processes it automatically</span>
<span class="keyword">await</span> recall.<span class="function">store</span>({
  content<span class="operator">:</span> <span class="string">"User wants the dashboard redesigned with dark mode"</span>,
  agentId<span class="operator">:</span> <span class="string">"ui-agent"</span>
});

<span class="comment">// Search by meaning, not keywords</span>
<span class="keyword">const</span> memories <span class="operator">=</span> <span class="keyword">await</span> recall.<span class="function">search</span>({
  query<span class="operator">:</span> <span class="string">"what UI changes did the user request?"</span>,
  agentId<span class="operator">:</span> <span class="string">"ui-agent"</span>
});

<span class="comment">// Traverse relationships</span>
<span class="keyword">const</span> connected <span class="operator">=</span> <span class="keyword">await</span> recall.<span class="function">traverse</span>(memories[<span class="variable">0</span>].id, {
  depth<span class="operator">:</span> <span class="variable">2</span>,
  relationship<span class="operator">:</span> <span class="string">"relates_to"</span>
});`,
          }}
        />
      </div>
    </section>
  );
}

function Features() {
  return (
    <section
      id="features"
      style={{ padding: "80px 0", borderTop: "1px solid var(--border)" }}
    >
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
        <div style={{ textAlign: "center", marginBottom: 64 }}>
          <h2
            style={{
              fontSize: 40,
              fontWeight: 800,
              letterSpacing: "-0.03em",
              marginBottom: 16,
            }}
          >
            Memory that <span className="gradient-text">thinks</span>
          </h2>
          <p
            style={{
              fontSize: 18,
              color: "var(--text-dim)",
              maxWidth: 600,
              margin: "0 auto",
            }}
          >
            AgentRecall isn&apos;t a key-value store with a fancy name. It&apos;s a
            memory system built for how AI agents actually need to remember.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
            gap: 24,
          }}
        >
          {FEATURES.map((feature) => (
            <div key={feature.title} className="feature-card">
              <div style={{ fontSize: 32, marginBottom: 16 }}>{feature.icon}</div>
              <h3
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  marginBottom: 12,
                  letterSpacing: "-0.01em",
                }}
              >
                {feature.title}
              </h3>
              <p
                style={{
                  color: "var(--text-dim)",
                  fontSize: 15,
                  lineHeight: 1.6,
                  marginBottom: 20,
                }}
              >
                {feature.description}
              </p>
              <div
                className="code-block"
                style={{ fontSize: 12, padding: 16, marginBottom: 0 }}
                dangerouslySetInnerHTML={{ __html: feature.code }}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  return (
    <section
      id="pricing"
      style={{ padding: "80px 0", borderTop: "1px solid var(--border)" }}
    >
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "0 24px" }}>
        <div style={{ textAlign: "center", marginBottom: 64 }}>
          <h2
            style={{
              fontSize: 40,
              fontWeight: 800,
              letterSpacing: "-0.03em",
              marginBottom: 16,
            }}
          >
            Simple, transparent pricing
          </h2>
          <p
            style={{
              fontSize: 18,
              color: "var(--text-dim)",
              maxWidth: 500,
              margin: "0 auto",
            }}
          >
            Start free. Scale when you&apos;re ready. No surprises.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: 24,
          }}
        >
          {PRICING.map((plan) => (
            <div
              key={plan.name}
              className={`pricing-card ${plan.featured ? "featured" : ""}`}
              style={{ display: "flex", flexDirection: "column" }}
            >
              <div style={{ height: 28, marginBottom: 16 }}>
                {plan.featured && (
                  <div
                    style={{
                      display: "inline-block",
                      padding: "4px 12px",
                      borderRadius: 999,
                      background: "rgba(139, 92, 246, 0.15)",
                      color: "var(--purple)",
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    Most Popular
                  </div>
                )}
              </div>

              <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>
                {plan.name}
              </h3>

              <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginBottom: 32 }}>
                <span style={{ fontSize: 48, fontWeight: 800, letterSpacing: "-0.03em" }}>
                  {plan.price}
                </span>
                <span style={{ color: "var(--text-dim)", fontSize: 16 }}>{plan.period}</span>
              </div>

              <ul
                style={{
                  listStyle: "none",
                  padding: 0,
                  margin: "0 0 32px 0",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  flex: 1,
                }}
              >
                {plan.features.map((f) => (
                  <li
                    key={f}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      fontSize: 15,
                      color: "var(--text-dim)",
                    }}
                  >
                    <span style={{ color: "var(--purple)" }}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <a
                href={plan.href}
                className={plan.featured ? "btn-primary" : "btn-secondary"}
                style={{
                  display: "flex",
                  justifyContent: "center",
                  width: "100%",
                  padding: "14px 0",
                  fontSize: 15,
                  marginTop: "auto",
                }}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer
      style={{
        padding: "40px 0",
        borderTop: "1px solid var(--border)",
        textAlign: "center",
      }}
    >
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
        <div style={{ display: "flex", justifyContent: "center", gap: 32, marginBottom: 24 }}>
          <a href="#features" className="nav-link">Features</a>
          <a href="#pricing" className="nav-link">Pricing</a>
          <a href="https://dashboard.agentrecall.cloud" className="nav-link">Dashboard</a>
          <a href="https://docs.agentrecall.cloud" className="nav-link">Docs</a>
          <a href="https://github.com/agentrecall" className="nav-link">GitHub</a>
        </div>
        <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
          AgentRecall — Persistent memory for AI agents
        </p>
      </div>
    </footer>
  );
}

/* ──────────────────────── PAGE ─────────────────────────── */

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <QuickStart />
        <Features />
        <Pricing />
      </main>
      <Footer />
    </>
  );
}
