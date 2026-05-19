import { CodeBlock } from '../components'

export default function GraphMemory() {
  return (
    <>
      <h1>Graph Memory</h1>
      <p>AgentRecall builds a <strong>Neo4j-powered knowledge graph</strong> from your memories, automatically extracting entities and relationships.</p>

      <h2>How It Works</h2>
      <p>When you store a memory, the AI processing pipeline extracts:</p>
      <ul>
        <li><strong>Entities</strong> — People, places, concepts, objects mentioned in the text</li>
        <li><strong>Relationships</strong> — How entities connect to each other (e.g., "works_at", "prefers", "is_allergic_to")</li>
        <li><strong>Properties</strong> — Attributes of each entity (e.g., name, type, value)</li>
      </ul>
      <p>These are stored as nodes and edges in Neo4j, forming a rich graph structure.</p>

      <h2>Example Graph</h2>
      <CodeBlock>{`[User] --prefers--> [Dark Mode]
[User] --allergic_to--> [Peanuts]
[User] --works_at--> [Acme Corp]
[Acme Corp] --located_in--> [San Francisco]
[User] --uses--> [Python] --is_a--> [Programming Language]`}</CodeBlock>

      <h2>Traversal Queries</h2>
      <p>Use <code>traverse()</code> to walk the graph and find connections between entities.</p>

      <h3>Python</h3>
      <CodeBlock>{`<span class="cm"># Find all entities connected to a node</span>
connections = memory.traverse(
    entity=<span class="str">"User"</span>,
    depth=<span class="num">2</span>,
    agent_id=<span class="str">"my-agent"</span>
)

<span class="kw">for</span> node <span class="kw">in</span> connections:
    <span class="fn">print</span>(f<span class="str">"{node.entity} --{node.relationship}--> {node.target}"</span>)`}</CodeBlock>

      <h3>Node.js</h3>
      <CodeBlock>{`<span class="kw">const</span> connections = <span class="kw">await</span> memory.<span class="fn">traverse</span>({
  entity: <span class="str">"User"</span>,
  depth: <span class="num">2</span>,
  agentId: <span class="str">"my-agent"</span>,
});

connections.forEach(node =&gt; {
  console.<span class="fn">log</span>(\`\${node.entity} --\${node.relationship}--&gt; \${node.target}\`);
});`}</CodeBlock>

      <h2>Finding Hidden Connections</h2>
      <p>Graph traversal can discover non-obvious links between concepts. For example:</p>
      <CodeBlock>{`<span class="cm"># "What connects the user to San Francisco?"</span>
paths = memory.traverse(
    source=<span class="str">"User"</span>,
    target=<span class="str">"San Francisco"</span>,
    agent_id=<span class="str">"my-agent"</span>
)
<span class="cm"># Result: User -> works_at -> Acme Corp -> located_in -> San Francisco</span>`}</CodeBlock>

      <h2>Graph via Cloud API</h2>
      <CodeBlock>{`<span class="cm"># POST /v1/traverse</span>
curl -X POST https://api.agentrecall.cloud/v1/traverse \\
  -H <span class="str">"Authorization: Bearer ar_your_key"</span> \\
  -H <span class="str">"Content-Type: application/json"</span> \\
  -d '{
    "entity": "User",
    "depth": 3,
    "agent_id": "my-agent"
  }'`}</CodeBlock>
    </>
  )
}
