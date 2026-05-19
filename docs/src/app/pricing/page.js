export default function Pricing() {
  return (
    <>
      <h1>Pricing</h1>
      <p>Simple, transparent pricing. Start free, upgrade when you need more.</p>

      <div className="install-grid">
        <div className="card">
          <h3>Free</h3>
          <p><strong style={{fontSize: '32px', color: 'white'}}>$0</strong> / month</p>
          <ul>
            <li>1,000 memories</li>
            <li>Basic semantic search</li>
            <li>1 agent</li>
            <li>60 requests/min</li>
            <li>Community support</li>
            <li>Standard data retention</li>
          </ul>
          <p>Perfect for personal projects and experimentation.</p>
        </div>

        <div className="card" style={{borderColor: '#8B5CF6'}}>
          <h3>Pro</h3>
          <p><strong style={{fontSize: '32px', color: '#8B5CF6'}}>$3</strong> / month</p>
          <ul>
            <li><strong>Unlimited</strong> memories</li>
            <li>Semantic search + <strong>Graph Memory</strong></li>
            <li><strong>AI Processing</strong> (Qwen2.5-7B)</li>
            <li>Unlimited agents</li>
            <li>600 requests/min</li>
            <li>Priority support</li>
            <li>Enhanced data retention</li>
            <li>Graph traversal</li>
            <li>Auto-categorization</li>
            <li>Importance scoring</li>
          </ul>
          <p>For production agents that need intelligent memory.</p>
        </div>
      </div>

      <h2>Feature Comparison</h2>
      <table>
        <thead>
          <tr><th>Feature</th><th>Free</th><th>Pro</th></tr>
        </thead>
        <tbody>
          <tr><td>Memories</td><td>1,000</td><td>Unlimited</td></tr>
          <tr><td>Semantic Search</td><td>✅</td><td>✅</td></tr>
          <tr><td>Graph Memory</td><td>—</td><td>✅</td></tr>
          <tr><td>AI Processing</td><td>—</td><td>✅</td></tr>
          <tr><td>Entity Extraction</td><td>—</td><td>✅</td></tr>
          <tr><td>Relationship Detection</td><td>—</td><td>✅</td></tr>
          <tr><td>Auto-Categorization</td><td>—</td><td>✅</td></tr>
          <tr><td>Importance Scoring</td><td>—</td><td>✅</td></tr>
          <tr><td>Agents</td><td>1</td><td>Unlimited</td></tr>
          <tr><td>Rate Limit</td><td>60 req/min</td><td>600 req/min</td></tr>
          <tr><td>Python SDK</td><td>✅</td><td>✅</td></tr>
          <tr><td>Node.js SDK</td><td>✅</td><td>✅</td></tr>
          <tr><td>Cloud API</td><td>✅</td><td>✅</td></tr>
          <tr><td>Self-Hosting</td><td>✅</td><td>✅</td></tr>
        </tbody>
      </table>

      <h2>FAQ</h2>
      <h3>Can I self-host for free?</h3>
      <p>Yes! AgentRecall is open source. You can run the full stack locally with your own Neo4j and model at no cost. The pricing applies to the hosted cloud API.</p>

      <h3>What happens when I hit the free tier limit?</h3>
      <p>Your existing memories remain accessible. You just can&apos;t store new ones until you upgrade or delete some.</p>

      <h3>Do unused memories roll over?</h3>
      <p>No, limits are per billing period. Free tier resets monthly.</p>
    </>
  )
}
