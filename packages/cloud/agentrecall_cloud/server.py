"""AgentRecall Cloud API — main FastAPI server."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from agentrecall_cloud.config import config
from agentrecall_cloud.database import get_pool, init_db, init_auth, close_pool
from agentrecall_cloud.auth import get_current_user, generate_api_key, hash_api_key
from agentrecall_cloud.scoring import classify, should_skip, compute_score
from agentrecall_cloud.models import (
    MemoryCreate,
    MemoryResponse,
    RecallResult,
    AgentCreate,
    AgentResponse,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    CountResponse,
    MessageResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    await init_db()
    await init_auth()
    yield
    await close_pool()


app = FastAPI(
    title="AgentRecall Cloud",
    version="0.1.0",
    description="Hosted persistent memory for AI agents",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ─────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ─── Memories ────────────────────────────────────────────────────────


@app.post("/v1/memories", response_model=MemoryResponse)
async def remember(
    req: MemoryCreate,
    user: dict = Depends(get_current_user),
):
    """Store a memory for an agent."""
    pool = await get_pool()
    user_id = user["user_id"]
    agent_id = req.agent_id

    # Verify agent belongs to user
    async with pool.acquire() as conn:
        agent = await conn.fetchrow(
            "SELECT id FROM agents WHERE id = $1 AND user_id = $2",
            agent_id,
            user_id,
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Auto-classify if not provided
        category = req.category or classify(req.content)

        # Auto-skip noise
        skipped = should_skip(req.content)

        # Check free tier limits
        sub = await conn.fetchrow(
            "SELECT plan FROM subscriptions WHERE user_id = $1", user_id
        )
        plan = sub["plan"] if sub else "free"

        if plan == "free":
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM memories m JOIN agents a ON m.agent_id = a.id WHERE a.user_id = $1",
                user_id,
            )
            if count >= config.free_tier_memories:
                raise HTTPException(
                    status_code=402,
                    detail=f"Free tier limit reached ({config.free_tier_memories} memories). Upgrade to Pro.",
                )

        # Insert memory
        row = await conn.fetchrow(
            """
            INSERT INTO memories (agent_id, content, category, importance, skipped, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, agent_id, content, category, importance, confidence,
                      skipped, access_count, created_at, updated_at, metadata
            """,
            agent_id,
            req.content,
            category,
            req.importance,
            skipped,
            str(req.metadata) if req.metadata else "{}",
        )

        # Update agent memory count
        await conn.execute(
            "UPDATE agents SET memory_count = memory_count + 1, last_active_at = now() WHERE id = $1",
            agent_id,
        )

        # Track usage
        await _track_usage(conn, user_id, memories_stored=1)

        return MemoryResponse(
            id=row["id"],
            agent_id=str(row["agent_id"]),
            content=row["content"],
            category=row["category"],
            importance=row["importance"],
            confidence=row["confidence"],
            skipped=row["skipped"],
            access_count=row["access_count"],
            created_at=row["created_at"].isoformat(),
            updated_at=row["updated_at"].isoformat(),
            metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
        )


@app.get("/v1/memories/recall", response_model=list[RecallResult])
async def recall(
    query: str,
    agent_id: str,
    limit: int = 5,
    category: str = None,
    user: dict = Depends(get_current_user),
):
    """Find relevant memories for a query."""
    pool = await get_pool()
    user_id = user["user_id"]

    async with pool.acquire() as conn:
        # Verify agent belongs to user
        agent = await conn.fetchrow(
            "SELECT id FROM agents WHERE id = $1 AND user_id = $2",
            agent_id,
            user_id,
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Fetch memories for this agent
        if category:
            rows = await conn.fetch(
                """
                SELECT id, agent_id, content, category, importance, confidence,
                       skipped, access_count, created_at, updated_at, metadata
                FROM memories
                WHERE agent_id = $1 AND category = $2 AND skipped = false
                ORDER BY created_at DESC
                LIMIT 100
                """,
                agent_id,
                category,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, agent_id, content, category, importance, confidence,
                       skipped, access_count, created_at, updated_at, metadata
                FROM memories
                WHERE agent_id = $1 AND skipped = false
                ORDER BY created_at DESC
                LIMIT 100
                """,
                agent_id,
            )

        # Score and rank (simple text matching for now — embeddings added later)
        results = []
        query_lower = query.lower()
        for row in rows:
            # Simple text similarity (0.0 to 1.0)
            content_lower = row["content"].lower()
            words = set(query_lower.split())
            content_words = set(content_lower.split())
            if not words:
                similarity = 0.0
            else:
                overlap = words & content_words
                similarity = len(overlap) / len(words)

            score = compute_score(
                similarity=similarity,
                confidence=row["confidence"],
                importance=row["importance"],
                created_at=row["created_at"],
                skipped=row["skipped"],
            )

            if score > 0:
                results.append(
                    RecallResult(
                        id=row["id"],
                        agent_id=str(row["agent_id"]),
                        content=row["content"],
                        category=row["category"],
                        importance=row["importance"],
                        confidence=row["confidence"],
                        score=round(score, 4),
                        created_at=row["created_at"].isoformat(),
                    )
                )

        # Sort by score and return top N
        results.sort(key=lambda r: r.score, reverse=True)
        top = results[:limit]

        # Increment access_count for recalled memories
        for r in top:
            await conn.execute(
                "UPDATE memories SET access_count = access_count + 1 WHERE id = $1",
                r.id,
            )

        # Track usage
        await _track_usage(conn, user_id, memories_recalled=len(top))

        return top


@app.get("/v1/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: int,
    user: dict = Depends(get_current_user),
):
    """Get a single memory by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT m.id, m.agent_id, m.content, m.category, m.importance,
                   m.confidence, m.skipped, m.access_count, m.created_at,
                   m.updated_at, m.metadata
            FROM memories m
            JOIN agents a ON m.agent_id = a.id
            WHERE m.id = $1 AND a.user_id = $2
            """,
            memory_id,
            user["user_id"],
        )
        if not row:
            raise HTTPException(status_code=404, detail="Memory not found")

        return MemoryResponse(
            id=row["id"],
            agent_id=str(row["agent_id"]),
            content=row["content"],
            category=row["category"],
            importance=row["importance"],
            confidence=row["confidence"],
            skipped=row["skipped"],
            access_count=row["access_count"],
            created_at=row["created_at"].isoformat(),
            updated_at=row["updated_at"].isoformat(),
            metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
        )


@app.delete("/v1/memories/{memory_id}", response_model=MessageResponse)
async def delete_memory(
    memory_id: int,
    user: dict = Depends(get_current_user),
):
    """Delete a memory."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM memories
            WHERE id = $1 AND agent_id IN (
                SELECT id FROM agents WHERE user_id = $2
            )
            """,
            memory_id,
            user["user_id"],
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Memory not found")
        return MessageResponse(message="Memory deleted")


# ─── Agents ──────────────────────────────────────────────────────────


@app.get("/v1/agents", response_model=list[AgentResponse])
async def list_agents(user: dict = Depends(get_current_user)):
    """List all agents for the user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, memory_count, created_at, last_active_at
            FROM agents WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user["user_id"],
        )
        return [
            AgentResponse(
                id=str(r["id"]),
                name=r["name"],
                memory_count=r["memory_count"],
                created_at=r["created_at"].isoformat(),
                last_active_at=r["last_active_at"].isoformat() if r["last_active_at"] else None,
            )
            for r in rows
        ]


@app.post("/v1/agents", response_model=AgentResponse)
async def create_agent(
    req: AgentCreate,
    user: dict = Depends(get_current_user),
):
    """Create a new agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO agents (user_id, name)
            VALUES ($1, $2)
            RETURNING id, name, memory_count, created_at, last_active_at
            """,
            user["user_id"],
            req.name,
        )
        return AgentResponse(
            id=str(row["id"]),
            name=row["name"],
            memory_count=row["memory_count"],
            created_at=row["created_at"].isoformat(),
            last_active_at=None,
        )


@app.delete("/v1/agents/{agent_id}", response_model=MessageResponse)
async def delete_agent(
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete an agent and all its memories."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM agents WHERE id = $1 AND user_id = $2",
            agent_id,
            user["user_id"],
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Agent not found")
        return MessageResponse(message="Agent deleted")


@app.get("/v1/agents/{agent_id}/count", response_model=CountResponse)
async def count_memories(
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    """Count memories for an agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        agent = await conn.fetchrow(
            "SELECT id FROM agents WHERE id = $1 AND user_id = $2",
            agent_id,
            user["user_id"],
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        count = await conn.fetchval(
            "SELECT COUNT(*) FROM memories WHERE agent_id = $1", agent_id
        )
        return CountResponse(count=count)


# ─── API Keys ────────────────────────────────────────────────────────


@app.get("/v1/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(user: dict = Depends(get_current_user)):
    """List API keys for the user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, key_prefix, created_at, last_used_at
            FROM api_keys WHERE user_id = $1 AND is_active = true
            ORDER BY created_at DESC
            """,
            user["user_id"],
        )
        return [
            ApiKeyResponse(
                id=str(r["id"]),
                name=r["name"],
                key_prefix=r["key_prefix"],
                created_at=r["created_at"].isoformat(),
                last_used_at=r["last_used_at"].isoformat() if r["last_used_at"] else None,
            )
            for r in rows
        ]


@app.post("/v1/api-keys", response_model=ApiKeyCreatedResponse)
async def create_api_key(
    req: ApiKeyCreate,
    user: dict = Depends(get_current_user),
):
    """Create a new API key. Returns the full key ONCE."""
    full_key = generate_api_key()
    key_hash = hash_api_key(full_key)
    key_prefix = full_key[:12] + "..."

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO api_keys (user_id, key_hash, key_prefix, name)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, key_prefix, created_at
            """,
            user["user_id"],
            key_hash,
            key_prefix,
            req.name,
        )
        return ApiKeyCreatedResponse(
            id=str(row["id"]),
            name=row["name"],
            key_prefix=row["key_prefix"],
            created_at=row["created_at"].isoformat(),
            last_used_at=None,
            full_key=full_key,
        )


@app.delete("/v1/api-keys/{key_id}", response_model=MessageResponse)
async def delete_api_key(
    key_id: str,
    user: dict = Depends(get_current_user),
):
    """Revoke an API key."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE api_keys SET is_active = false WHERE id = $1 AND user_id = $2",
            key_id,
            user["user_id"],
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="API key not found")
        return MessageResponse(message="API key revoked")


# ─── Usage ───────────────────────────────────────────────────────────


async def _track_usage(conn, user_id: str, api_calls: int = 1, memories_stored: int = 0, memories_recalled: int = 0):
    """Track daily usage."""
    await conn.execute(
        """
        INSERT INTO usage_daily (user_id, api_calls, memories_stored, memories_recalled)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id, date) DO UPDATE SET
            api_calls = usage_daily.api_calls + EXCLUDED.api_calls,
            memories_stored = usage_daily.memories_stored + EXCLUDED.memories_stored,
            memories_recalled = usage_daily.memories_recalled + EXCLUDED.memories_recalled
        """,
        user_id,
        api_calls,
        memories_stored,
        memories_recalled,
    )


@app.get("/v1/usage")
async def get_usage(user: dict = Depends(get_current_user)):
    """Get current usage stats."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT api_calls, memories_stored, memories_recalled
            FROM usage_daily
            WHERE user_id = $1 AND date = CURRENT_DATE
            """,
            user["user_id"],
        )

        sub = await conn.fetchrow(
            "SELECT plan FROM subscriptions WHERE user_id = $1",
            user["user_id"],
        )
        plan = sub["plan"] if sub else "free"

        return {
            "api_calls_today": row["api_calls"] if row else 0,
            "memories_stored": row["memories_stored"] if row else 0,
            "memories_recalled": row["memories_recalled"] if row else 0,
            "plan": plan,
            "limit": config.free_tier_api_calls_daily if plan == "free" else -1,
        }


# ─── Main ────────────────────────────────────────────────────────────


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8700)


if __name__ == "__main__":
    main()


# ─── Auth (simple JWT for dashboard) ──────────────────────────────

@app.post("/v1/auth/signup")
async def signup(request: Request):
    """Simple signup: creates user + returns JWT."""
    body = await request.json()
    email = body.get("email", "").strip()
    password = body.get("password", "")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT id FROM auth_users WHERE email = $1", email
        )
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        
        # Hash password with bcrypt
        import hashlib
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create user
        row = await conn.fetchrow(
            "INSERT INTO auth_users (email, password_hash) VALUES ($1, $2) RETURNING id, email",
            email, pw_hash
        )
        user_id = str(row["id"])
        
        # Create subscription
        await conn.execute(
            "INSERT INTO subscriptions (user_id, plan) VALUES ($1, 'free') ON CONFLICT DO NOTHING",
            user_id
        )
        
        # Create default agent
        await conn.execute(
            "INSERT INTO agents (user_id, name) VALUES ($1, 'default')",
            user_id
        )
        
        # Generate JWT
        import jwt as pyjwt
        token = pyjwt.encode(
            {"sub": user_id, "email": email, "exp": __import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=30)},
            config.jwt_secret,
            algorithm="HS256"
        )
        
        return {"token": token, "user": {"id": user_id, "email": email}}


@app.post("/v1/auth/login")
async def login(request: Request):
    """Simple login: returns JWT."""
    body = await request.json()
    email = body.get("email", "").strip()
    password = body.get("password", "")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        import hashlib
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        
        row = await conn.fetchrow(
            "SELECT id, email FROM auth_users WHERE email = $1 AND password_hash = $2",
            email, pw_hash
        )
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        user_id = str(row["id"])
        
        import jwt as pyjwt
        token = pyjwt.encode(
            {"sub": user_id, "email": email, "exp": __import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=30)},
            config.jwt_secret,
            algorithm="HS256"
        )
        
        return {"token": token, "user": {"id": user_id, "email": email}}


@app.get("/v1/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, created_at FROM auth_users WHERE id = $1",
            user["user_id"]
        )
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return {"id": str(row["id"]), "email": row["email"], "created_at": row["created_at"].isoformat()}
