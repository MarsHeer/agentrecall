import asyncpg
import logging
from agentrecall_cloud.config import config

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            config.database_url, min_size=2, max_size=10
        )
        logger.info("Database pool created")
    return _pool


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def init_db():
    """Run migrations to initialize the database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Users are managed by Supabase Auth
        # API Keys
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                key_hash TEXT NOT NULL,
                key_prefix TEXT NOT NULL,
                name TEXT DEFAULT 'default',
                created_at TIMESTAMPTZ DEFAULT now(),
                last_used_at TIMESTAMPTZ,
                is_active BOOLEAN DEFAULT true
            )
        """)

        # Agents
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                memory_count INT DEFAULT 0,
                last_active_at TIMESTAMPTZ
            )
        """)

        # Memories
        await conn.execute("""
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
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)"
        )

        # Usage tracking
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_daily (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                date DATE NOT NULL DEFAULT CURRENT_DATE,
                api_calls INT DEFAULT 0,
                memories_stored INT DEFAULT 0,
                memories_recalled INT DEFAULT 0,
                UNIQUE(user_id, date)
            )
        """)

        # Subscriptions
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL UNIQUE,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                plan TEXT DEFAULT 'free',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)

        logger.info("Database initialized successfully")
