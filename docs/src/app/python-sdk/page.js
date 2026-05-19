import { CodeBlock } from '../components'

export default function PythonSDK() {
  return (
    <>
      <h1>Python SDK</h1>
      <p>Full reference for the <code>agentrecall-sdk</code> Python package.</p>

      <h2>Installation</h2>
      <CodeBlock>{'pip install agentrecall-sdk'}</CodeBlock>

      <h2>Setup</h2>
      <h3>Cloud Mode</h3>
      <CodeBlock>{`<span class="kw">from</span> agentrecall_sdk <span class="kw">import</span> AgentRecall

memory = AgentRecall(
    api_key=<span class="str">"ar_your_api_key"</span>,
    mode=<span class="str">"cloud"</span>,  <span class="cm"># default</span>
    base_url=<span class="str">"https://api.agentrecall.cloud"</span>  <span class="cm"># optional</span>
)`}</CodeBlock>

      <h3>Local Mode</h3>
      <CodeBlock>{`memory = AgentRecall(
    mode=<span class="str">"local"</span>,
    neo4j_uri=<span class="str">"bolt://localhost:7687"</span>,
    neo4j_user=<span class="str">"neo4j"</span>,
    neo4j_password=<span class="str">"password"</span>,
    model_path=<span class="str">"Qwen/Qwen2.5-7B"</span>  <span class="cm"># optional</span>
)`}</CodeBlock>

      <h2>API Reference</h2>

      <h3><code>store()</code></h3>
      <table>
        <thead>
          <tr><th>Parameter</th><th>Type</th><th>Required</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>content</code></td><td>str</td><td>Yes</td><td>Memory text content</td></tr>
          <tr><td><code>agent_id</code></td><td>str</td><td>Yes</td><td>Agent identifier for isolation</td></tr>
          <tr><td><code>category</code></td><td>str</td><td>No</td><td>Memory category</td></tr>
          <tr><td><code>metadata</code></td><td>dict</td><td>No</td><td>Extra key-value data</td></tr>
          <tr><td><code>importance</code></td><td>float</td><td>No</td><td>Manual importance (0–1)</td></tr>
          <tr><td><code>process</code></td><td>bool</td><td>No</td><td>Enable AI processing (default: True)</td></tr>
        </tbody>
      </table>
      <CodeBlock>{`result = memory.store(
    content=<span class="str">"User prefers TypeScript over JavaScript"</span>,
    agent_id=<span class="str">"coding-assistant"</span>,
    category=<span class="str">"preferences"</span>,
    metadata={<span class="str">"source"</span>: <span class="str">"code_review"</span>},
    importance=<span class="num">0.7</span>
)
<span class="fn">print</span>(result.id)  <span class="cm"># "mem_abc123"</span>`}</CodeBlock>

      <h3><code>search()</code></h3>
      <table>
        <thead>
          <tr><th>Parameter</th><th>Type</th><th>Required</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>query</code></td><td>str</td><td>Yes</td><td>Natural language search query</td></tr>
          <tr><td><code>agent_id</code></td><td>str</td><td>Yes</td><td>Agent to search within</td></tr>
          <tr><td><code>category</code></td><td>str</td><td>No</td><td>Filter by category</td></tr>
          <tr><td><code>limit</code></td><td>int</td><td>No</td><td>Max results (default: 10)</td></tr>
          <tr><td><code>min_score</code></td><td>float</td><td>No</td><td>Minimum relevance score</td></tr>
        </tbody>
      </table>
      <CodeBlock>{`results = memory.search(
    query=<span class="str">"what are the user's coding preferences?"</span>,
    agent_id=<span class="str">"coding-assistant"</span>,
    category=<span class="str">"preferences"</span>,
    limit=<span class="num">5</span>
)

<span class="kw">for</span> r <span class="kw">in</span> results:
    <span class="fn">print</span>(f<span class="str">"[{r.score:.2f}] {r.content}"</span>)`}</CodeBlock>

      <h3><code>traverse()</code></h3>
      <table>
        <thead>
          <tr><th>Parameter</th><th>Type</th><th>Required</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>entity</code></td><td>str</td><td>Yes*</td><td>Starting entity name</td></tr>
          <tr><td><code>source</code></td><td>str</td><td>Yes*</td><td>Source entity (for path finding)</td></tr>
          <tr><td><code>target</code></td><td>str</td><td>No</td><td>Target entity (for path finding)</td></tr>
          <tr><td><code>depth</code></td><td>int</td><td>No</td><td>Traversal depth (default: 2)</td></tr>
          <tr><td><code>agent_id</code></td><td>str</td><td>Yes</td><td>Agent scope</td></tr>
        </tbody>
      </table>
      <CodeBlock>{`<span class="cm"># Find connections from an entity</span>
connections = memory.traverse(entity=<span class="str">"User"</span>, depth=<span class="num">3</span>, agent_id=<span class="str">"my-agent"</span>)

<span class="cm"># Find shortest path between two entities</span>
paths = memory.traverse(source=<span class="str">"User"</span>, target=<span class="str">"San Francisco"</span>, agent_id=<span class="str">"my-agent"</span>)`}</CodeBlock>

      <h3><code>agent()</code></h3>
      <CodeBlock>{`<span class="cm"># Create a high-level agent with memory</span>
agent = memory.agent(
    agent_id=<span class="str">"my-agent"</span>,
    system_prompt=<span class="str">"You are a helpful assistant with memory."</span>
)

<span class="cm"># The agent automatically stores and retrieves memories</span>
response = agent.chat(<span class="str">"Remember that I like coffee"</span>)`}</CodeBlock>

      <h2>Configuration</h2>
      <table>
        <thead>
          <tr><th>Option</th><th>Default</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>api_key</code></td><td>—</td><td>Cloud API key</td></tr>
          <tr><td><code>mode</code></td><td><code>"cloud"</code></td><td><code>"cloud"</code> or <code>"local"</code></td></tr>
          <tr><td><code>base_url</code></td><td>api.agentrecall.cloud</td><td>API endpoint</td></tr>
          <tr><td><code>timeout</code></td><td>30</td><td>Request timeout in seconds</td></tr>
          <tr><td><code>retries</code></td><td>3</td><td>Max retry attempts</td></tr>
        </tbody>
      </table>
    </>
  )
}
