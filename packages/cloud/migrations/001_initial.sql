-- AgentRecall Cloud — Initial Migration
-- Run: psql $DATABASE_URL -f 001_initial.sql

-- API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    key_hash TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    name TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true
);

-- Agents
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    memory_count INT DEFAULT 0,
    last_active_at TIMESTAMPTZ
);

-- Memories
CREATE TABLE IF NOT EXISTS memories (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    importance TEXT NOT NULL DEFAULT 'medium',
    confidence REAL NOT NULL DEFAULT 1.0,
    skipped BOOLEAN DEFAULT false,
    access_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}',
    embedding FLOAT8[]
);

CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);

-- Usage tracking
CREATE TABLE IF NOT EXISTS usage_daily (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    api_calls INT DEFAULT 0,
    memories_stored INT DEFAULT 0,
    memories_recalled INT DEFAULT 0,
    UNIQUE(user_id, date)
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    plan TEXT DEFAULT 'free',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
