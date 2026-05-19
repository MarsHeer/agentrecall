"""AI Memory Processor — calls RunPod serverless endpoint (Qwen2.5-7B).

Falls back to regex classification when RunPod is not configured.
"""

import json
import logging
import asyncio
from typing import Optional

import httpx

from agentrecall_cloud.config import config
from agentrecall_cloud.scoring import classify

logger = logging.getLogger(__name__)

# Singleton HTTP client for connection pooling
_client: Optional[httpx.AsyncClient] = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def process_memory(memory_id: int, content: str, agent_id: str) -> dict:
    """Process a single memory through AI (RunPod) or regex fallback.

    Returns dict with: category, importance, entities, relationships, summary, keywords.
    Always returns valid data — falls back to regex on any error.
    """
    if not config.runpod_api_key or not config.runpod_endpoint_id:
        logger.debug("RunPod not configured, using regex fallback for memory %d", memory_id)
        return _regex_fallback(content)

    try:
        client = await _get_client()
        url = f"https://api.runpod.ai/v2/{config.runpod_endpoint_id}/runsync"

        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {config.runpod_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": {
                    "content": content,
                    "memory_id": memory_id,
                }
            },
        )

        if response.status_code != 200:
            logger.warning("RunPod returned %d for memory %d, falling back to regex",
                          response.status_code, memory_id)
            return _regex_fallback(content)

        data = response.json()

        # RunPod runsync returns {"output": {...}}
        output = data.get("output", data)

        if "error" in output:
            logger.warning("RunPod error for memory %d: %s", memory_id, output["error"])
            return _regex_fallback(content)

        # Validate and clean the output
        return _validate_output(output, content)

    except httpx.TimeoutException:
        logger.warning("RunPod timeout for memory %d, falling back to regex", memory_id)
        return _regex_fallback(content)
    except Exception as e:
        logger.error("RunPod processing failed for memory %d: %s", memory_id, e)
        return _regex_fallback(content)


async def process_memories_batch(memories: list[dict]) -> list[dict]:
    """Process multiple memories in one RunPod call (batch).

    Each dict: {"id": int, "content": str}
    Returns list of results.
    """
    if not config.runpod_api_key or not config.runpod_endpoint_id:
        return [_regex_fallback(m["content"]) for m in memories]

    try:
        client = await _get_client()
        url = f"https://api.runpod.ai/v2/{config.runpod_endpoint_id}/runsync"

        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {config.runpod_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": {
                    "memories": [{"id": m["id"], "content": m["content"]} for m in memories]
                }
            },
        )

        if response.status_code != 200:
            logger.warning("RunPod batch returned %d, falling back to regex", response.status_code)
            return [_regex_fallback(m["content"]) for m in memories]

        data = response.json()
        output = data.get("output", data)

        if "error" in output:
            return [_regex_fallback(m["content"]) for m in memories]

        results = output.get("results", [])
        # Pad if RunPod returned fewer results than we sent
        while len(results) < len(memories):
            idx = len(results)
            results.append(_regex_fallback(memories[idx]["content"]))

        return [_validate_output(r, memories[i]["content"]) for i, r in enumerate(results)]

    except Exception as e:
        logger.error("RunPod batch processing failed: %s", e)
        return [_regex_fallback(m["content"]) for m in memories]


async def enrich_memory(memory_id: int, content: str, agent_id: str) -> None:
    """Enrich a memory in the database with AI processing results.

    This is called async after the memory is stored. Updates the DB directly.
    """
    result = await process_memory(memory_id, content, agent_id)

    from agentrecall_cloud.database import get_pool

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Update category and importance if AI gave better classification
            await conn.execute(
                """
                UPDATE memories
                SET category = $1, importance = $2, metadata = $3, updated_at = now()
                WHERE id = $4
                """,
                result.get("category", "general"),
                result.get("importance", "medium"),
                json.dumps({
                    "ai_processed": True,
                    "entities": result.get("entities", []),
                    "relationships": result.get("relationships", []),
                    "summary": result.get("summary", ""),
                    "keywords": result.get("keywords", []),
                }),
                memory_id,
            )
            logger.info("Enriched memory %d: category=%s, importance=%s",
                       memory_id, result.get("category"), result.get("importance"))
    except Exception as e:
        logger.error("Failed to enrich memory %d: %s", memory_id, e)


def _regex_fallback(content: str) -> dict:
    """Fast regex classification when RunPod is unavailable."""
    category = classify(content)

    # Simple importance heuristic
    content_lower = content.lower()
    if any(w in content_lower for w in ["actually", "wrong", "correction", "don't", "never use"]):
        importance = "high"
    elif any(w in content_lower for w in ["prefer", "love", "hate", "favorite", "always"]):
        importance = "high"
    elif any(w in content_lower for w in ["deadline", "reminder", "schedule", "tomorrow"]):
        importance = "high"
    else:
        importance = "medium"

    return {
        "category": category,
        "importance": importance,
        "entities": [],
        "relationships": [],
        "summary": content[:100],
        "keywords": [],
        "ai_processed": False,
    }


def _validate_output(output: dict, content: str) -> dict:
    """Validate and clean AI output."""
    valid_categories = {"correction", "preference", "temporal", "factual", "general"}
    valid_importance = {"high", "medium", "low"}

    category = output.get("category", "general")
    if category not in valid_categories:
        category = _regex_fallback(content)["category"]

    importance = output.get("importance", "medium")
    if importance not in valid_importance:
        importance = "medium"

    return {
        "category": category,
        "importance": importance,
        "entities": output.get("entities", []),
        "relationships": output.get("relationships", []),
        "summary": output.get("summary", content[:100]),
        "keywords": output.get("keywords", []),
        "ai_processed": True,
    }
