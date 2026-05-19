import { CodeBlock } from '../components'

export default function CoreConcepts() {
  return (
    <>
      <h1>Core Concepts</h1>
      <p>Understanding the fundamental building blocks of AgentRecall.</p>

      <h2>Memory</h2>
      <p>A <strong>Memory</strong> is the atomic unit of AgentRecall. Each memory contains a piece of information that an agent stores for later retrieval.</p>
      <div className="card">
        <h3>Memory Structure</h3>
        <CodeBlock>{`{
  "id": "mem_abc123",
  "content": "The user mentioned they are allergic to peanuts",
  "agent_id": "assistant-v2",
  "category": "user_health",
  "metadata": { "source": "conversation", "timestamp": "2026-01-15" },
  "importance": 0.85,
  "created_at": "2026-01-15T10:30:00Z"
}`}</CodeBlock>
      </div>
      <ul>
        <li><strong>Content</strong> — The text of the memory (any string)</li>
        <li><strong>Category</strong> — Optional grouping (e.g., "preferences", "facts", "conversations")</li>
        <li><strong>Metadata</strong> — Arbitrary key-value pairs for extra context</li>
        <li><strong>Importance</strong> — A 0–1 score indicating relevance (auto-computed or manual)</li>
      </ul>

      <h2>Agents</h2>
      <p>Agents provide <strong>isolation boundaries</strong> for memories. Each agent has its own memory space, preventing cross-contamination between different AI systems or conversation threads.</p>
      <h3>Single Agent</h3>
      <CodeBlock>{`<span class="cm"># All memories belong to one agent</span>
memory.store(content=<span class="str">"..."</span>, agent_id=<span class="str">"customer-support"</span>)
results = memory.search(query=<span class="str">"..."</span>, agent_id=<span class="str">"customer-support"</span>)`}</CodeBlock>
      <h3>Multi-Agent</h3>
      <CodeBlock>{`<span class="cm"># Different agents have isolated memories</span>
memory.store(content=<span class="str">"..."</span>, agent_id=<span class="str">"sales-agent"</span>)
memory.store(content=<span class="str">"..."</span>, agent_id=<span class="str">"support-agent"</span>)

<span class="cm"># Each agent only sees its own memories by default</span>
<span class="cm"># You can query across agents if needed</span>`}</CodeBlock>

      <h2>Categories and Metadata</h2>
      <p><strong>Categories</strong> organize memories into logical groups. Use them to filter searches or apply different processing rules.</p>
      <CodeBlock>{`memory.store(
    content=<span class="str">"User's favorite color is blue"</span>,
    agent_id=<span class="str">"my-agent"</span>,
    category=<span class="str">"preferences"</span>,
    metadata={<span class="str">"confidence"</span>: <span class="num">0.9</span>, <span class="str">"source"</span>: <span class="str">"chat"</span>}
)

<span class="cm"># Search within a category</span>
results = memory.search(
    query=<span class="str">"color preferences"</span>,
    agent_id=<span class="str">"my-agent"</span>,
    category=<span class="str">"preferences"</span>
)`}</CodeBlock>

      <h2>Importance Scoring</h2>
      <p>Every memory gets an <strong>importance score</strong> from 0 to 1. This is either:</p>
      <ul>
        <li><strong>Auto-computed</strong> — The AI processing pipeline analyzes content and assigns importance based on specificity, actionability, and uniqueness</li>
        <li><strong>Manually set</strong> — You can override with your own score when storing</li>
      </ul>
      <CodeBlock>{`<span class="cm"># Manual importance</span>
memory.store(
    content=<span class="str">"Critical: server password is X"</span>,
    agent_id=<span class="str">"ops-agent"</span>,
    importance=<span class="num">0.95</span>
)

<span class="cm"># Auto importance (default)</span>
memory.store(
    content=<span class="str">"User said hi today"</span>,
    agent_id=<span class="str">"chat-agent"</span>
)
<span class="cm"># importance will be computed automatically, likely ~0.2</span>`}</CodeBlock>
    </>
  )
}
