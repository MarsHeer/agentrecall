"""AI Memory Processor — calls DeepSeek V4 Flash API.

Falls back to regex classification when API key is not configured.
DeepSeek V4 Flash is fast, cheap (~$0.27/M tokens), and produces excellent
structured output for memory processing.
"""

import json
import logging
from typing import Optional

import httpx

from agentrecall_cloud.config import config
from agentrecall_cloud.scoring import classify

logger = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


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


SYSTEM_PROMPT = """You are an AI memory processor. Given a memory text, extract structured info and return ONLY valid JSON.

Return exactly this JSON (no markdown, no explanation):
{"category": "<correction|preference|temporal|factual|general>", "importance": "<high|medium|low>", "entities": [{"name": "...", "type": "person|place|tool|concept|date"}], "relationships": [{"source": "...", "target": "...", "type": "..."}], "summary": "<one sentence, max 100 chars>", "keywords": ["kw1", "kw2"]}

Rules:
- "prefer/like/hate/always/never use" = preference. "actually/wrong/correction" = correction. "yesterday/tomorrow/deadline" = temporal. "is/are/was/has/lives" = factual. Else = general.
- importance: "high" if correction, strong preference, or deadline. Else "medium".
- entities: People, places, tools, concepts, dates. Type = person/place/tool/concept/date.
- relationships: How entities relate.
- summary: One sentence, max 100 chars.
- keywords: 2-5 searchable words."""


async def _call_deepseek(content: str) -> dict:
    """Call DeepSeek API for memory processing."""
    client = await _get_client()

    response = await client.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {config.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f'Process this memory:\n\n"{content}"\n\nReturn ONLY the JSON.'},
            ],
            "temperature": 0.3,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
        },
    )

    if response.status_code != 200:
        raise RuntimeError(f"DeepSeek API returned {response.status_code}: {response.text[:200]}")

    data = response.json()
    text = data["choices"][0]["message"]["content"].strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    return json.loads(text)


async def process_memory(memory_id: int, content: str, agent_id: str) -> dict:
    """Process a single memory through DeepSeek or regex fallback."""
    if not config.deepseek_api_key:
        logger.debug("DeepSeek not configured, using regex fallback for memory %d", memory_id)
        return _regex_fallback(content)

    try:
        result = await _call_deepseek(content)
        return _validate_output(result, content)
    except httpx.TimeoutException:
        logger.warning("DeepSeek timeout for memory %d", memory_id)
        return _regex_fallback(content)
    except Exception as e:
        logger.error("DeepSeek processing failed for memory %d: %s", memory_id, e)
        return _regex_fallback(content)


async def process_memories_batch(memories: list[dict]) -> list[dict]:
    """Process multiple memories (sequential via API)."""
    if not config.deepseek_api_key:
        return [_regex_fallback(m["content"]) for m in memories]

    results = []
    for m in memories:
        try:
            result = await _call_deepseek(m["content"])
            results.append(_validate_output(result, m["content"]))
        except Exception:
            results.append(_regex_fallback(m["content"]))
    return results


async def enrich_memory(memory_id: int, content: str, agent_id: str) -> None:
    """Enrich a memory in the database with AI processing results."""
    result = await process_memory(memory_id, content, agent_id)

    from agentrecall_cloud.database import get_pool

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE memories
                SET category = $1, importance = $2, metadata = $3,
                    ai_processed = true, summary = $4, keywords = $5,
                    updated_at = now()
                WHERE id = $6
                """,
                result.get("category", "general"),
                result.get("importance", "medium"),
                json.dumps({
                    "entities": result.get("entities", []),
                    "relationships": result.get("relationships", []),
                }),
                result.get("summary", ""),
                result.get("keywords", []),
                memory_id,
            )
            # Store entities in separate table
            entities = result.get("entities", [])
            for ent in entities:
                if isinstance(ent, dict) and ent.get("name"):
                    await conn.execute(
                        "INSERT INTO entities (memory_id, name, type) VALUES ($1, $2, $3)",
                        memory_id, ent["name"], ent.get("type", "concept"),
                    )

            # Store relationships
            rels = result.get("relationships", [])
            for rel in rels:
                if isinstance(rel, dict) and rel.get("source") and rel.get("target"):
                    await conn.execute(
                        "INSERT INTO relationships (memory_id, source, target, relation_type) VALUES ($1, $2, $3, $4)",
                        memory_id, rel["source"], rel["target"], rel.get("type", "related_to"),
                    )

            logger.info("Enriched memory %d: category=%s, importance=%s, entities=%d",
                       memory_id, result.get("category"), result.get("importance"), len(entities))
    except Exception as e:
        logger.error("Failed to enrich memory %d: %s", memory_id, e)


def _regex_fallback(content: str) -> dict:
    """Fast regex classification when API is unavailable."""
    category = classify(content)

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
