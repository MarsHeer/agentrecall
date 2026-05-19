import { CodeBlock } from '../components'

export default function SelfHosting() {
  return (
    <>
      <h1>Self-Hosting</h1>
      <p>Run AgentRecall on your own infrastructure with full control over data and models.</p>

      <h2>BYOK Mode (Bring Your Own Key)</h2>
      <p>Self-hosting gives you complete control. Your data never leaves your servers, and you can use your own Neo4j instance and AI model.</p>

      <h2>Docker Setup</h2>
      <CodeBlock>{`<span class="cm"># docker-compose.yml</span>
version: <span class="str">"3.8"</span>
services:
  agentrecall:
    image: agentrecall/agentrecall:latest
    ports:
      - <span class="str">"8700:8700"</span>
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=your_password
      - MODEL_PATH=Qwen/Qwen2.5-7B
      - MODE=local
    depends_on:
      - neo4j

  neo4j:
    image: neo4j:5
    ports:
      - <span class="str">"7474:7474"</span>
      - <span class="str">"7687:7687"</span>
    environment:
      - NEO4J_AUTH=neo4j/your_password
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:`}</CodeBlock>

      <CodeBlock>{'docker compose up -d'}</CodeBlock>

      <h2>Running with Your Own Neo4j</h2>
      <CodeBlock>{`<span class="cm"># Connect to an existing Neo4j instance</span>
<span class="kw">from</span> agentrecall_sdk <span class="kw">import</span> AgentRecall

memory = AgentRecall(
    mode=<span class="str">"local"</span>,
    neo4j_uri=<span class="str">"bolt://your-neo4j-host:7687"</span>,
    neo4j_user=<span class="str">"neo4j"</span>,
    neo4j_password=<span class="str">"your_password"</span>
)`}</CodeBlock>

      <h2>Running with Your Own Model</h2>
      <p>By default, local mode uses a bundled Qwen2.5-7B. You can swap in any compatible model:</p>
      <CodeBlock>{`<span class="cm"># Using a different model path</span>
memory = AgentRecall(
    mode=<span class="str">"local"</span>,
    model_path=<span class="str">"/path/to/your/model"</span>,
    neo4j_uri=<span class="str">"bolt://localhost:7687"</span>,
    neo4j_user=<span class="str">"neo4j"</span>,
    neo4j_password=<span class="str">"password"</span>
)`}</CodeBlock>

      <h2>Environment Variables</h2>
      <table>
        <thead>
          <tr><th>Variable</th><th>Default</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>MODE</code></td><td><code>cloud</code></td><td><code>cloud</code> or <code>local</code></td></tr>
          <tr><td><code>NEO4J_URI</code></td><td>bolt://localhost:7687</td><td>Neo4j connection URI</td></tr>
          <tr><td><code>NEO4J_USER</code></td><td>neo4j</td><td>Neo4j username</td></tr>
          <tr><td><code>NEO4J_PASSWORD</code></td><td>—</td><td>Neo4j password</td></tr>
          <tr><td><code>MODEL_PATH</code></td><td>Qwen/Qwen2.5-7B</td><td>HuggingFace model or local path</td></tr>
          <tr><td><code>API_PORT</code></td><td>8700</td><td>API server port</td></tr>
          <tr><td><code>API_KEY</code></td><td>—</td><td>API key for authentication</td></tr>
          <tr><td><code>LOG_LEVEL</code></td><td>info</td><td>Logging verbosity</td></tr>
        </tbody>
      </table>

      <h2>Verification</h2>
      <CodeBlock>{`<span class="cm"># Health check</span>
curl http://localhost:8700/health

<span class="cm"># Expected response</span>
{
  <span class="str">"status"</span>: <span class="str">"healthy"</span>,
  <span class="str">"mode"</span>: <span class="str">"local"</span>,
  <span class="str">"neo4j"</span>: <span class="str">"connected"</span>,
  <span class="str">"model"</span>: <span class="str">"Qwen/Qwen2.5-7B"</span>
}`}</CodeBlock>
    </>
  )
}
