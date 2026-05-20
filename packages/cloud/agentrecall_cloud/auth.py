import hashlib
import secrets
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from agentrecall_cloud.config import config
from agentrecall_cloud.database import get_pool

security = HTTPBearer(auto_error=False)


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key with prefix."""
    prefix = "ark_"  # agentrecall key
    raw = secrets.token_hex(24)
    return f"{prefix}{raw}"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Authenticate via JWT (dashboard) or API key (agent).

    JWT returns:  {"user_id": "...", "source": "jwt"}
    API key returns: {"user_id": "...", "agent_id": "...", "source": "api_key"}

    The agent_id from the API key means the agent is implicit —
    no need to pass agent_id in requests.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization")

    token = credentials.credentials

    # Try JWT first (dashboard sessions)
    try:
        payload = jwt.decode(token, config.jwt_secret, algorithms=["HS256"])
        return {"user_id": payload["sub"], "source": "jwt"}
    except jwt.InvalidTokenError:
        pass

    # Try API key (agent SDK) — returns the tied agent_id
    key_hash = hash_api_key(token)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, agent_id FROM api_keys WHERE key_hash = $1 AND is_active = true",
            key_hash,
        )
        if row:
            # Update last_used_at
            await conn.execute(
                "UPDATE api_keys SET last_used_at = now() WHERE id = $1", row["id"]
            )
            return {
                "user_id": str(row["user_id"]),
                "agent_id": str(row["agent_id"]),
                "source": "api_key",
            }

    raise HTTPException(status_code=401, detail="Invalid token or API key")


async def verify_api_key_owner(api_key_id: str, user_id: str) -> bool:
    """Verify that an API key belongs to a user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM api_keys WHERE id = $1 AND user_id = $2",
            api_key_id,
            user_id,
        )
        return row is not None
