import { CodeBlock } from '../components'

export default function AIProcessing() {
  return (
    <>
      <h1>AI Memory Processing</h1>
      <p>Every memory stored in AgentRecall is <strong>automatically processed by Qwen2.5-7B</strong> to extract structured information.</p>

      <h2>What Happens When You Store a Memory</h2>
      <ol>
        <li><strong>Ingestion</strong> — Your text is received and validated</li>
        <li><strong>AI Processing</strong> — Qwen2.5-7B analyzes the content</li>
        <li><strong>Entity Extraction</strong> — Named entities are identified and typed</li>
        <li><strong>Relationship Detection</strong> — Connections between entities are mapped</li>
        <li><strong>Auto-Categorization</strong> — Content is classified into categories</li>
        <li><strong>Importance Scoring</strong> — Relevance score is computed</li>
        <li><strong>Graph Storage</strong> — Everything is stored in Neo4j</li>
        <li><strong>Vector Indexing</strong> — Embeddings are generated for semantic search</li>
      </ol>

      <h2>Entity Extraction</h2>
      <p>The model identifies and types entities from your memories:</p>
      <table>
        <thead>
          <tr><th>Entity Type</th><th>Example</th></tr>
        </thead>
        <tbody>
          <tr><td>Person</td><td>"Alice", "the user"</td></tr>
          <tr><td>Organization</td><td>"Acme Corp", "OpenAI"</td></tr>
          <tr><td>Location</td><td>"San Francisco", "the office"</td></tr>
          <tr><td>Concept</td><td>"dark mode", "machine learning"</td></tr>
          <tr><td>Technology</td><td>"Python", "Neo4j", "React"</td></tr>
          <tr><td>Preference</td><td>"prefers X", "likes Y"</td></tr>
        </tbody>
      </table>

      <h2>Relationship Detection</h2>
      <p>The model infers relationships between extracted entities:</p>
      <CodeBlock>{`<span class="cm">// Input memory:</span>
<span class="cm">// "Alice works at Acme Corp in San Francisco and prefers Python"</span>

<span class="cm">// Extracted relationships:</span>
<span class="cm">// [Alice] --works_at--&gt; [Acme Corp]</span>
<span class="cm">// [Acme Corp] --located_in--&gt; [San Francisco]</span>
<span class="cm">// [Alice] --prefers--&gt; [Python]</span>
<span class="cm">// [Python] --is_a--&gt; [Technology]</span>`}</CodeBlock>

      <h2>Auto-Categorization</h2>
      <p>If no category is provided, the AI assigns one automatically:</p>
      <ul>
        <li><code>preferences</code> — User preferences, likes/dislikes</li>
        <li><code>facts</code> — Factual information about entities</li>
        <li><code>conversations</code> — Dialogue summaries</li>
        <li><code>tasks</code> — Action items, to-dos</li>
        <li><code>context</code> — Background information</li>
      </ul>

      <h2>How It Works Under the Hood</h2>
      <div className="card">
        <h3>Processing Pipeline</h3>
        <CodeBlock>{`Memory Text
    |
    v
+---------------------+
|   Qwen2.5-7B LLM    |
|  (entity extraction, |
|   relationships,     |
|   categorization,    |
|   importance)        |
+----------+----------+
           |
    +------+------+
    v             v
+--------+  +--------+
| Neo4j  |  | Vector |
| Graph  |  | Index  |
+--------+  +--------+`}</CodeBlock>
      </div>
      <p>The entire pipeline runs asynchronously. Your <code>store()</code> call returns immediately after the memory is persisted. The AI processing happens in the background, and the graph/vector indices are updated within seconds.</p>

      <h2>Disabling AI Processing</h2>
      <p>If you want raw storage without AI enrichment:</p>
      <CodeBlock>{`memory.store(
    content=<span class="str">"Raw text without processing"</span>,
    agent_id=<span class="str">"my-agent"</span>,
    process=<span class="kw">False</span>  <span class="cm"># Skip AI processing</span>
)`}</CodeBlock>
    </>
  )
}
