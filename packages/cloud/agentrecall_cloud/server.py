"""AgentRecall Cloud API — main FastAPI server."""

import asyncio
import json
import logging
import stripe
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from agentrecall_cloud.config import config
from agentrecall_cloud.database import get_pool, init_db, init_auth, close_pool
from agentrecall_cloud.auth import get_current_user, generate_api_key, hash_api_key
from agentrecall_cloud.scoring import classify, should_skip, compute_score
from agentrecall_cloud.processor import enrich_memory
import bcrypt
from agentrecall_cloud.models import (
    MemoryCreate,
    MemoryResponse,
    MemoryUpdate,
    RecallResult,
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    CountResponse,
    MessageResponse,
    SubscriptionResponse,
    PortalResponse,
)

# Configure Stripe if key is available
if config.stripe_secret_key:
    stripe.api_key = config.stripe_secret_key

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

        # Launch async AI enrichment (non-blocking)
        asyncio.create_task(enrich_memory(row["id"], req.content, agent_id))

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
            ai_processed=row.get("ai_processed", False),
            summary=row.get("summary", ""),
            keywords=row.get("keywords", []) or [],
            entities=[],
            relationships=[],
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


# ─── Memory Management ───────────────────────────────────────────


@app.put("/v1/memories/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: int,
    req: MemoryUpdate,
    user: dict = Depends(get_current_user),
):
    """Update memory content."""
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

        updated = await conn.fetchrow(
            """
            UPDATE memories
            SET content = $1, updated_at = now()
            WHERE id = $2
            RETURNING id, agent_id, content, category, importance, confidence,
                      skipped, access_count, created_at, updated_at, metadata
            """,
            req.content,
            memory_id,
        )

        return MemoryResponse(
            id=updated["id"],
            agent_id=str(updated["agent_id"]),
            content=updated["content"],
            category=updated["category"],
            importance=updated["importance"],
            confidence=updated["confidence"],
            skipped=updated["skipped"],
            access_count=updated["access_count"],
            created_at=updated["created_at"].isoformat(),
            updated_at=updated["updated_at"].isoformat(),
            metadata=updated["metadata"] if isinstance(updated["metadata"], dict) else {},
        )


@app.post("/v1/memories/{memory_id}/skip", response_model=MessageResponse)
async def skip_memory(
    memory_id: int,
    user: dict = Depends(get_current_user),
):
    """Mark a memory as skipped."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE memories SET skipped = true
            WHERE id = $1 AND agent_id IN (
                SELECT id FROM agents WHERE user_id = $2
            )
            """,
            memory_id,
            user["user_id"],
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Memory not found")
        return MessageResponse(message="Memory skipped")


@app.delete("/v1/memories/{memory_id}/skip", response_model=MessageResponse)
async def unskip_memory(
    memory_id: int,
    user: dict = Depends(get_current_user),
):
    """Unskip a memory."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE memories SET skipped = false
            WHERE id = $1 AND agent_id IN (
                SELECT id FROM agents WHERE user_id = $2
            )
            """,
            memory_id,
            user["user_id"],
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Memory not found")
        return MessageResponse(message="Memory unskipped")


@app.get("/v1/memories", response_model=list[MemoryResponse])
async def list_memories(
    agent_id: str = None,
    category: str = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    """List memories for the user."""
    limit = min(limit, 200)
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = ["a.user_id = $1"]
        params: list = [user["user_id"]]
        param_idx = 2

        if agent_id:
            conditions.append(f"m.agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        if category:
            conditions.append(f"m.category = ${param_idx}")
            params.append(category)
            param_idx += 1

        where_clause = " AND ".join(conditions)

        rows = await conn.fetch(
            f"""
            SELECT m.id, m.agent_id, m.content, m.category, m.importance,
                   m.confidence, m.skipped, m.access_count, m.created_at,
                   m.updated_at, m.metadata
            FROM memories m
            JOIN agents a ON m.agent_id = a.id
            WHERE {where_clause}
            ORDER BY m.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """,
            *params,
            limit,
            offset,
        )

        return [
            MemoryResponse(
                id=r["id"],
                agent_id=str(r["agent_id"]),
                content=r["content"],
                category=r["category"],
                importance=r["importance"],
                confidence=r["confidence"],
                skipped=r["skipped"],
                access_count=r["access_count"],
                created_at=r["created_at"].isoformat(),
                updated_at=r["updated_at"].isoformat(),
                metadata=r["metadata"] if isinstance(r["metadata"], dict) else {},
            )
            for r in rows
        ]


# ─── Agent Management ─────────────────────────────────────────────


@app.put("/v1/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    req: AgentUpdate,
    user: dict = Depends(get_current_user),
):
    """Rename an agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE agents SET name = $1
            WHERE id = $2 AND user_id = $3
            RETURNING id, name, memory_count, created_at, last_active_at
            """,
            req.name,
            agent_id,
            user["user_id"],
        )
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        return AgentResponse(
            id=str(row["id"]),
            name=row["name"],
            memory_count=row["memory_count"],
            created_at=row["created_at"].isoformat(),
            last_active_at=row["last_active_at"].isoformat() if row["last_active_at"] else None,
        )


@app.get("/v1/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a single agent's details."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, name, memory_count, created_at, last_active_at
            FROM agents WHERE id = $1 AND user_id = $2
            """,
            agent_id,
            user["user_id"],
        )
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        return AgentResponse(
            id=str(row["id"]),
            name=row["name"],
            memory_count=row["memory_count"],
            created_at=row["created_at"].isoformat(),
            last_active_at=row["last_active_at"].isoformat() if row["last_active_at"] else None,
        )


# ─── Billing ──────────────────────────────────────────────────────


@app.post("/v1/billing/checkout")
async def create_checkout(user: dict = Depends(get_current_user)):
    """Create a Stripe Checkout session for Pro upgrade ($3/month).

    If STRIPE_SECRET_KEY is not configured, returns a graceful fallback.
    """
    if not config.stripe_secret_key or not config.stripe_price_id:
        return {"url": None, "message": "Stripe not configured"}

    pool = await get_pool()
    user_id = user["user_id"]

    async with pool.acquire() as conn:
        # Get or create Stripe customer
        sub = await conn.fetchrow(
            "SELECT stripe_customer_id FROM subscriptions WHERE user_id = $1",
            user_id,
        )

        if sub and sub["stripe_customer_id"]:
            customer_id = sub["stripe_customer_id"]
        else:
            # Look up email for customer creation
            u = await conn.fetchrow(
                "SELECT email FROM auth_users WHERE id = $1", user_id
            )
            customer = stripe.Customer.create(
                email=u["email"] if u else None,
                metadata={"user_id": user_id},
            )
            customer_id = customer.id
            # Upsert subscription row with stripe_customer_id
            await conn.execute(
                """
                INSERT INTO subscriptions (user_id, stripe_customer_id, plan, status)
                VALUES ($1, $2, 'free', 'active')
                ON CONFLICT (user_id) DO UPDATE
                    SET stripe_customer_id = $2, updated_at = now()
                """,
                user_id,
                customer_id,
            )

    # Create Checkout Session
    base_url = config.app_base_url
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[
            {
                "price": config.stripe_price_id,
                "quantity": 1,
            }
        ],
        success_url=f"{base_url}/dashboard?checkout=success",
        cancel_url=f"{base_url}/dashboard?checkout=cancelled",
        metadata={"user_id": user_id},
    )

    return {"url": session.url}


@app.post("/v1/billing/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events.

    This endpoint does NOT use auth — it verifies requests via
    Stripe's webhook signature instead.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not config.stripe_webhook_secret:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET is not set")
        return {"received": True}

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.stripe_webhook_secret
        )
    except (stripe.error.SignatureVerificationError, ValueError, Exception) as e:
        logger.warning("Stripe webhook error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook")

    # Parse payload as plain JSON dict (avoids stripe object attribute issues)
    payload_json = json.loads(payload)
    event_type = payload_json["type"]
    event_data = payload_json["data"]["object"]
    logger.info("Stripe webhook received: %s", event_type)

    pool = await get_pool()

    if event_type == "checkout.session.completed":
        session = event_data
        user_id = session.get("metadata", {}).get("user_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if user_id and customer_id and subscription_id:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO subscriptions
                        (user_id, stripe_customer_id, stripe_subscription_id, plan, status)
                    VALUES ($1, $2, $3, 'pro', 'active')
                    ON CONFLICT (user_id) DO UPDATE
                        SET stripe_customer_id = $2,
                            stripe_subscription_id = $3,
                            plan = 'pro',
                            status = 'active',
                            updated_at = now()
                    """,
                    user_id,
                    customer_id,
                    subscription_id,
                )
            logger.info("Checkout completed for user %s", user_id)

    elif event_type == "customer.subscription.updated":
        subscription = event_data
        subscription_id = subscription.get("id")
        sub_status = subscription.get("status")

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1",
                subscription_id,
            )
            if row:
                plan = "pro" if sub_status == "active" else "free"
                await conn.execute(
                    """
                    UPDATE subscriptions
                    SET status = $1, plan = $2, updated_at = now()
                    WHERE stripe_subscription_id = $3
                    """,
                    sub_status,
                    plan,
                    subscription_id,
                )
            logger.info("Subscription %s updated: %s", subscription_id, sub_status)

    elif event_type == "customer.subscription.deleted":
        subscription = event_data
        subscription_id = subscription.get("id")

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE subscriptions
                SET plan = 'free', status = 'cancelled', updated_at = now()
                WHERE stripe_subscription_id = $1
                """,
                subscription_id,
            )
        logger.info("Subscription %s deleted", subscription_id)

    elif event_type == "invoice.payment_failed":
        invoice = event_data
        customer_id = invoice.get("customer")

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE subscriptions
                SET status = 'past_due', updated_at = now()
                WHERE stripe_customer_id = $1
                """,
                customer_id,
            )
        logger.info("Payment failed for customer %s", customer_id)

    return {"received": True}


@app.get("/v1/billing/subscription", response_model=SubscriptionResponse)
async def get_subscription(user: dict = Depends(get_current_user)):
    """Get the current subscription status for the user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT plan, status, stripe_customer_id FROM subscriptions WHERE user_id = $1",
            user["user_id"],
        )
        if not row:
            return SubscriptionResponse(plan="free", status="active", stripe_customer_id=None)

        return SubscriptionResponse(
            plan=row["plan"],
            status=row["status"],
            stripe_customer_id=row["stripe_customer_id"],
        )


@app.post("/v1/billing/portal")
async def create_portal(user: dict = Depends(get_current_user)):
    """Create a Stripe Customer Portal session for subscription management."""
    if not config.stripe_secret_key:
        return {"url": None, "message": "Stripe not configured"}

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT stripe_customer_id FROM subscriptions WHERE user_id = $1",
            user["user_id"],
        )

    if not row or not row["stripe_customer_id"]:
        raise HTTPException(
            status_code=400,
            detail="No Stripe customer found. Subscribe first.",
        )

    base_url = config.app_base_url
    portal_session = stripe.billing_portal.Session.create(
        customer=row["stripe_customer_id"],
        return_url=f"{base_url}/dashboard/settings",
    )

    return {"url": portal_session.url}


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
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
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
        row = await conn.fetchrow(
            "SELECT id, email, password_hash FROM auth_users WHERE email = $1",
            email
        )
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        stored_hash = row["password_hash"]
        # Detect hash format: bcrypt starts with $2b$, SHA-256 is 64 hex chars
        if stored_hash.startswith("$2b$"):
            valid = bcrypt.checkpw(password.encode(), stored_hash.encode())
        elif len(stored_hash) == 64 and all(c in "0123456789abcdef" for c in stored_hash):
            import hashlib
            valid = hashlib.sha256(password.encode()).hexdigest() == stored_hash
            if valid:
                # Auto-migrate to bcrypt
                new_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                await conn.execute(
                    "UPDATE auth_users SET password_hash = $1 WHERE id = $2",
                    new_hash, row["id"],
                )
        else:
            valid = False

        if not valid:
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
