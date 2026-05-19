import { CodeBlock } from '../components'

export default function CloudAPI() {
  return (
    <>
      <h1>Cloud API</h1>
      <p>REST API reference for <code>https://api.agentrecall.cloud</code> (port 8700).</p>

      <h2>Authentication</h2>
      <p>All requests require an API key in the <code>Authorization</code> header:</p>
      <CodeBlock>{'Authorization: Bearer ar_your_api_key'}</CodeBlock>

      <h3>Getting an API Key</h3>
      <p>API keys are generated from the dashboard. They start with <code>ar_</code> and can be scoped to specific agents or permissions.</p>

      <h2>Rate Limiting</h2>
      <table>
        <thead>
          <tr><th>Tier</th><th>Requests/min</th><th>Memories/month</th></tr>
        </thead>
        <tbody>
          <tr><td>Free</td><td>60</td><td>1,000</td></tr>
          <tr><td>Pro</td><td>600</td><td>Unlimited</td></tr>
        </tbody>
      </table>

      <h2>Endpoints</h2>

      <h3><span className="badge post">POST</span> /v1/memories</h3>
      <p>Store a new memory.</p>
      <CodeBlock>{`{
  "content": "The user prefers dark mode",
  "agent_id": "my-agent",
  "category": "preferences",
  "metadata": { "source": "chat" },
  "importance": 0.8
}`}</CodeBlock>

      <h3><span className="badge get">GET</span> /v1/memories</h3>
      <p>List memories with optional filters.</p>
      <CodeBlock>{`<span class="cm">// Query params: agent_id, category, limit, offset</span>
GET /v1/memories?agent_id=my-agent&amp;category=preferences&amp;limit=20`}</CodeBlock>

      <h3><span className="badge get">GET</span> /v1/memories/:id</h3>
      <p>Get a single memory by ID.</p>

      <h3><span className="badge put">PUT</span> /v1/memories/:id</h3>
      <p>Update a memory's content, category, or metadata.</p>
      <CodeBlock>{`{
  "content": "Updated memory content",
  "category": "updated_category",
  "metadata": { "updated": true }
}`}</CodeBlock>

      <h3><span className="badge delete">DELETE</span> /v1/memories/:id</h3>
      <p>Delete a memory and its graph connections.</p>

      <h3><span className="badge post">POST</span> /v1/recall</h3>
      <p>Semantic search across memories.</p>
      <CodeBlock>{`{
  "query": "what are the user's preferences?",
  "agent_id": "my-agent",
  "category": "preferences",
  "limit": 10
}`}</CodeBlock>

      <h3><span className="badge post">POST</span> /v1/skip</h3>
      <p>Store a memory without AI processing (skip enrichment).</p>
      <CodeBlock>{`{
  "content": "Raw content without AI processing",
  "agent_id": "my-agent"
}`}</CodeBlock>

      <h3><span className="badge post">POST</span> /v1/traverse</h3>
      <p>Traverse the knowledge graph.</p>
      <CodeBlock>{`{
  "entity": "User",
  "depth": 3,
  "agent_id": "my-agent"
}`}</CodeBlock>

      <h3><span className="badge get">GET</span> /v1/agents</h3>
      <p>List all agents and their memory counts.</p>

      <h3><span className="badge get">GET</span> /v1/agents/:id/stats</h3>
      <p>Get statistics for a specific agent (memory count, categories, last activity).</p>

      <h3><span className="badge get">GET</span> /v1/billing/usage</h3>
      <p>Get current billing period usage.</p>

      <h3><span className="badge get">GET</span> /v1/billing/plan</h3>
      <p>Get current plan details (free/pro, limits, expiry).</p>

      <h2>Error Responses</h2>
      <CodeBlock>{`{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Please retry after 60s.",
    "retry_after": 60
  }
}`}</CodeBlock>
      <table>
        <thead>
          <tr><th>Status</th><th>Code</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td>400</td><td>INVALID_REQUEST</td><td>Malformed request body</td></tr>
          <tr><td>401</td><td>UNAUTHORIZED</td><td>Missing or invalid API key</td></tr>
          <tr><td>403</td><td>FORBIDDEN</td><td>Insufficient permissions</td></tr>
          <tr><td>404</td><td>NOT_FOUND</td><td>Memory or resource not found</td></tr>
          <tr><td>429</td><td>RATE_LIMITED</td><td>Too many requests</td></tr>
          <tr><td>500</td><td>INTERNAL_ERROR</td><td>Server error (please report)</td></tr>
        </tbody>
      </table>
    </>
  )
}
