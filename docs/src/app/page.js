import { CodeBlock } from './components'

export default function Home() {
  return (
    <>
      <h1>🧠 AgentRecall</h1>
      <p className="hero-subtitle">The memory SDK for AI agents. Store, search, and traverse memories with graph-powered intelligence.</p>

      <h2>What is AgentRecall?</h2>
      <p>AgentRecall gives your AI agents <strong>persistent, searchable memory</strong> backed by a graph database. Every memory is automatically processed by AI to extract entities, detect relationships, and build a connected knowledge graph.</p>
      <ul>
        <li><strong>Semantic Search</strong> — Find relevant memories with natural language queries</li>
        <li><strong>Graph Memory</strong> — Neo4j-powered relationship traversal to uncover hidden connections</li>
        <li><strong>AI Processing</strong> — Qwen2.5-7B automatically enriches every memory</li>
        <li><strong>Multi-Agent</strong> — Isolate memory per agent or share across agents</li>
        <li><strong>Cloud or Local</strong> — Use our hosted API or run everything yourself</li>
      </ul>

      <h2>Installation</h2>
      <div className="install-grid">
        <div className="card">
          <h3>🐍 Python</h3>
          <CodeBlock>{'pip install agentrecall-sdk'}</CodeBlock>
        </div>
        <div className="card">
          <h3>📦 Node.js</h3>
          <CodeBlock>{'npm install agentrecall-ai-sdk'}</CodeBlock>
        </div>
      </div>

      <h2>Quick Start</h2>
      <h3>Python</h3>
      <CodeBlock>{`<span class="kw">from</span> agentrecall_sdk <span class="kw">import</span> AgentRecall

<span class="cm"># Connect to the cloud API</span>
memory = AgentRecall(
    api_key=<span class="str">"ar_your_api_key"</span>,
    mode=<span class="str">"cloud"</span>
)

<span class="cm"># Store a memory</span>
memory.store(
    content=<span class="str">"The user prefers dark mode and Python over JavaScript"</span>,
    agent_id=<span class="str">"my-agent"</span>,
    category=<span class="str">"preferences"</span>
)

<span class="cm"># Search memories</span>
results = memory.search(
    query=<span class="str">"what UI preferences does the user have?"</span>,
    agent_id=<span class="str">"my-agent"</span>
)

<span class="kw">for</span> result <span class="kw">in</span> results:
    <span class="fn">print</span>(result.content, result.score)`}</CodeBlock>

      <h3>Node.js</h3>
      <CodeBlock>{`<span class="kw">import</span> { AgentRecall } <span class="kw">from</span> <span class="str">"agentrecall-ai-sdk"</span>;

<span class="kw">const</span> memory = <span class="kw">new</span> <span class="fn">AgentRecall</span>({
  apiKey: <span class="str">"ar_your_api_key"</span>,
  mode: <span class="str">"cloud"</span>,
});

<span class="cm">// Store a memory</span>
<span class="kw">await</span> memory.<span class="fn">store</span>({ 
  content: <span class="str">"The user prefers dark mode and Python over JavaScript"</span>,
  agentId: <span class="str">"my-agent"</span>,
  category: <span class="str">"preferences"</span>
});

<span class="cm">// Search memories</span>
<span class="kw">const</span> results = <span class="kw">await</span> memory.<span class="fn">search</span>({
  query: <span class="str">"what UI preferences does the user have?"</span>,
  agentId: <span class="str">"my-agent"</span>,
});

results.forEach(r =&gt; console.<span class="fn">log</span>(r.content, r.score));`}</CodeBlock>

      <h2>Cloud vs Local</h2>
      <table>
        <thead>
          <tr><th>Feature</th><th>Cloud</th><th>Local</th></tr>
        </thead>
        <tbody>
          <tr><td>Setup</td><td>API key only</td><td>Requires Neo4j + model</td></tr>
          <tr><td>Graph Memory</td><td>✅</td><td>✅ (self-hosted Neo4j)</td></tr>
          <tr><td>AI Processing</td><td>✅ Managed</td><td>✅ (your own model)</td></tr>
          <tr><td>Semantic Search</td><td>✅</td><td>✅</td></tr>
          <tr><td>Data Privacy</td><td>Hosted on our servers</td><td>100% on your infrastructure</td></tr>
        </tbody>
      </table>
    </>
  )
}
