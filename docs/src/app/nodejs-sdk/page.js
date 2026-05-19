import { CodeBlock } from '../components'

export default function NodejsSDK() {
  return (
    <>
      <h1>Node.js SDK</h1>
      <p>Full reference for the <code>agentrecall-ai-sdk</code> npm package with TypeScript support.</p>

      <h2>Installation</h2>
      <CodeBlock>{'npm install agentrecall-ai-sdk'}</CodeBlock>

      <h2>Setup</h2>
      <h3>Cloud Mode</h3>
      <CodeBlock>{`<span class="kw">import</span> { AgentRecall } <span class="kw">from</span> <span class="str">"agentrecall-ai-sdk"</span>;

<span class="kw">const</span> memory = <span class="kw">new</span> <span class="fn">AgentRecall</span>({
  apiKey: <span class="str">"ar_your_api_key"</span>,
  mode: <span class="str">"cloud"</span>,
  baseUrl: <span class="str">"https://api.agentrecall.cloud"</span>,
});`}</CodeBlock>

      <h3>Local Mode</h3>
      <CodeBlock>{`<span class="kw">const</span> memory = <span class="kw">new</span> <span class="fn">AgentRecall</span>({
  mode: <span class="str">"local"</span>,
  neo4jUri: <span class="str">"bolt://localhost:7687"</span>,
  neo4jUser: <span class="str">"neo4j"</span>,
  neo4jPassword: <span class="str">"password"</span>,
});`}</CodeBlock>

      <h2>API Reference</h2>

      <h3><code>store()</code></h3>
      <CodeBlock>{`<span class="kw">const</span> result = <span class="kw">await</span> memory.<span class="fn">store</span>({
  content: <span class="str">"User prefers TypeScript over JavaScript"</span>,
  agentId: <span class="str">"coding-assistant"</span>,
  category: <span class="str">"preferences"</span>,
  metadata: { source: <span class="str">"code_review"</span> },
  importance: <span class="num">0.7</span>,
});

console.<span class="fn">log</span>(result.id); <span class="cm">// "mem_abc123"</span>`}</CodeBlock>

      <h3><code>search()</code></h3>
      <CodeBlock>{`<span class="kw">const</span> results = <span class="kw">await</span> memory.<span class="fn">search</span>({
  query: <span class="str">"what are the user's coding preferences?"</span>,
  agentId: <span class="str">"coding-assistant"</span>,
  category: <span class="str">"preferences"</span>,
  limit: <span class="num">5</span>,
});

results.<span class="fn">forEach</span>(r =&gt; console.<span class="fn">log</span>(\`[\${r.score.toFixed(<span class="num">2</span>)}] \${r.content}\`));`}</CodeBlock>

      <h3><code>traverse()</code></h3>
      <CodeBlock>{`<span class="cm">// Find connections from an entity</span>
<span class="kw">const</span> connections = <span class="kw">await</span> memory.<span class="fn">traverse</span>({
  entity: <span class="str">"User"</span>,
  depth: <span class="num">3</span>,
  agentId: <span class="str">"my-agent"</span>,
});

<span class="cm">// Find shortest path</span>
<span class="kw">const</span> paths = <span class="kw">await</span> memory.<span class="fn">traverse</span>({
  source: <span class="str">"User"</span>,
  target: <span class="str">"San Francisco"</span>,
  agentId: <span class="str">"my-agent"</span>,
});`}</CodeBlock>

      <h3><code>agent()</code></h3>
      <CodeBlock>{`<span class="kw">const</span> agent = memory.<span class="fn">agent</span>({
  agentId: <span class="str">"my-agent"</span>,
  systemPrompt: <span class="str">"You are a helpful assistant with memory."</span>,
});

<span class="kw">const</span> response = <span class="kw">await</span> agent.<span class="fn">chat</span>(<span class="str">"Remember that I like coffee"</span>);`}</CodeBlock>

      <h2>TypeScript Types</h2>
      <CodeBlock>{`<span class="kw">interface</span> <span class="type">AgentRecallConfig</span> {
  apiKey?: <span class="type">string</span>;
  mode?: <span class="str">"cloud"</span> | <span class="str">"local"</span>;
  baseUrl?: <span class="type">string</span>;
  neo4jUri?: <span class="type">string</span>;
  neo4jUser?: <span class="type">string</span>;
  neo4jPassword?: <span class="type">string</span>;
  timeout?: <span class="type">number</span>;
  retries?: <span class="type">number</span>;
}

<span class="kw">interface</span> <span class="type">StoreParams</span> {
  content: <span class="type">string</span>;
  agentId: <span class="type">string</span>;
  category?: <span class="type">string</span>;
  metadata?: <span class="type">Record</span>&lt;<span class="type">string</span>, <span class="type">any</span>&gt;;
  importance?: <span class="type">number</span>;
  process?: <span class="type">boolean</span>;
}

<span class="kw">interface</span> <span class="type">SearchParams</span> {
  query: <span class="type">string</span>;
  agentId: <span class="type">string</span>;
  category?: <span class="type">string</span>;
  limit?: <span class="type">number</span>;
  minScore?: <span class="type">number</span>;
}

<span class="kw">interface</span> <span class="type">MemoryResult</span> {
  id: <span class="type">string</span>;
  content: <span class="type">string</span>;
  score: <span class="type">number</span>;
  agentId: <span class="type">string</span>;
  category?: <span class="type">string</span>;
  metadata?: <span class="type">Record</span>&lt;<span class="type">string</span>, <span class="type">any</span>&gt;;
  importance: <span class="type">number</span>;
  createdAt: <span class="type">string</span>;
}

<span class="kw">interface</span> <span class="type">TraverseResult</span> {
  entity: <span class="type">string</span>;
  relationship: <span class="type">string</span>;
  target: <span class="type">string</span>;
  properties?: <span class="type">Record</span>&lt;<span class="type">string</span>, <span class="type">any</span>&gt;;
}`}</CodeBlock>

      <h2>Configuration</h2>
      <table>
        <thead>
          <tr><th>Option</th><th>Default</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>apiKey</code></td><td>—</td><td>Cloud API key</td></tr>
          <tr><td><code>mode</code></td><td><code>"cloud"</code></td><td><code>"cloud"</code> or <code>"local"</code></td></tr>
          <tr><td><code>baseUrl</code></td><td>api.agentrecall.cloud</td><td>API endpoint</td></tr>
          <tr><td><code>timeout</code></td><td>30000</td><td>Timeout in milliseconds</td></tr>
          <tr><td><code>retries</code></td><td>3</td><td>Max retry attempts</td></tr>
        </tbody>
      </table>
    </>
  )
}
