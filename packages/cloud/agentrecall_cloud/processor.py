"""AI Memory Processor — calls RunPod serverless endpoint (Qwen2.5-3B).

Falls back to DeepSeek API, then regex classification.
RunPod provides free GPU inference via serverless workers.
"""

import json
import logging
from typing import Optional

import httpx

from agentrecall_cloud.config import config
from agentrecall_cloud.scoring import classify

logger = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None

# RunPod serverless endpoint
RUNPOD_API_URL = "https://api.runpod.ai/v2/{endpoint_id}/{operation}"
# DeepSeek API (fallback)
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


# ── RunPod ───────────────────────────────────────────────────────────────

async def _call_runpod(content: str) -> dict:
    """Call RunPod serverless endpoint for memory processing."""
    if not config.runpod_api_key or not config.runpod_endpoint_id:
        raise RuntimeError("RunPod not configured")

    client = await _get_client()
    url = RUNPOD_API_URL.format(
        endpoint_id=config.runpod_endpoint_id, operation="runsync"
    )

    response = await client.post(
        url,
        headers={
            "Authorization": f"Bearer {config.runpod_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "input": {"text": content},
            "policy": {"executionTimeout": 300000},
        },
    )

    if response.status_code != 200:
        raise RuntimeError(f"RunPod returned {response.status_code}: {response.text[:200]}")

    data = response.json()

    # RunPod async: check status if IN_QUEUE
    if data.get("status") == "IN_QUEUE":
        job_id = data["id"]
        status_url = RUNPOD_API_URL.format(
            endpoint_id=config.runpod_endpoint_id, operation=f"status/{job_id}"
        )
        # Poll with backoff
        import asyncio
        for delay in [5, 10, 15, 20]:
            await asyncio.sleep(delay)
            status_resp = await client.get(
                status_url,
                headers={"Authorization": f"Bearer {config.runpod_api_key}"},
            )
            if status_resp.status_code == 200:
                data = status_resp.json()
                if data.get("status") == "COMPLETED":
                    return data.get("output", {})
                elif data.get("status") == "FAILED":
                    raise RuntimeError(f"RunPod job failed: {data}")
        raise RuntimeError("RunPod job timed out")

    if data.get("status") == "COMPLETED":
        return data.get("output", {})
    elif data.get("status") == "FAILED":
        raise RuntimeError(f"RunPod job failed: {data}")

    # Direct output (runsync returned result)
    if "output" in data:
        return data["output"]

    return data


# ── DeepSeek (fallback) ──────────────────────────────────────────────────

DEEPSEEK_SYSTEM_PROMPT = """You are an AI memory processor. Given a memory text, extract structured info and return ONLY valid JSON.

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
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": DEEPSEEK_SYSTEM_PROMPT},
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

    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    return json.loads(text)


# ── Main processing ──────────────────────────────────────────────────────

async def process_memory(memory_id: int, content: str, agent_id: str) -> dict:
    """Process a single memory: RunPod → DeepSeek → regex fallback."""

    # 1. Try RunPod
    if config.runpod_api_key and config.runpod_endpoint_id:
        try:
            result = await _call_runpod(content)
            return _validate_output(result, content)
        except httpx.TimeoutException:
            logger.warning("RunPod timeout for memory %d, trying DeepSeek", memory_id)
        except Exception as e:
            logger.warning("RunPod failed for memory %d: %s, trying DeepSeek", memory_id, e)

    # 2. Try DeepSeek
    if config.deepseek_api_key:
        try:
            result = await _call_deepseek(content)
            return _validate_output(result, content)
        except httpx.TimeoutException:
            logger.warning("DeepSeek timeout for memory %d, using regex", memory_id)
        except Exception as e:
            logger.warning("DeepSeek failed for memory %d: %s", memory_id, e)

    # 3. Regex fallback
    return _regex_fallback(content)


async def process_memories_batch(memories: list[dict]) -> list[dict]:
    """Process multiple memories."""
    return [await process_memory(0, m["content"], m.get("agent_id", "")) for m in memories]


async def enrich_memory(memory_id: int, content: str, agent_id: str) -> None:
    """Enrich a memory in the database with AI processing results."""
    from agentrecall_cloud.graph_db import sync_memory_to_graph

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
            # Store entities
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
                        memory_id, rel["source"], rel["target"], rel.get("relation", rel.get("type", "related_to")),
                    )

            logger.info("Enriched memory %d: category=%s, importance=%s, entities=%d",
                       memory_id, result.get("category"), result.get("importance"), len(entities))

            await sync_memory_to_graph(
                memory_id=memory_id,
                content=content,
                agent_id=agent_id,
                entities=entities,
                relationships=rels,
                summary=result.get("summary", ""),
            )
    except Exception as e:
        logger.error("Failed to enrich memory %d: %s", memory_id, e)


def _regex_fallback(content: str) -> dict:
    """Fast regex classification when API is unavailable."""
    import re as _re
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

    entities = []
    caps = _re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', content)
    seen = set()
    for name in caps:
        name_clean = name.strip()
        if name_clean.lower() not in seen and len(name_clean) > 2:
            seen.add(name_clean.lower())
            if any(w in name_clean.lower() for w in ["street", "road", "ave", "blvd", "st"]):
                etype = "location"
            elif any(w in name_clean.lower() for w in ["inc", "llc", "corp", "ltd", "co"]):
                etype = "organization"
            else:
                etype = "concept"
            entities.append({"name": name_clean, "type": etype})

    relationships = []
    for pattern, rel_type in [
        (r'lives in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'lives_in'),
        (r'works? on\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'works_on'),
        (r'works? at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'works_at'),
        (r'has a\s+([A-Z][a-z]+)', 'has'),
        (r'is a\s+([A-Z][a-z]+)', 'is_a'),
    ]:
        matches = _re.findall(pattern, content)
        for match in matches:
            if entities:
                relationships.append({
                    "source": entities[0]["name"],
                    "target": match.strip(),
                    "type": rel_type,
                })

    return {
        "category": category,
        "importance": importance,
        "entities": entities,
        "relationships": relationships,
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
        "ai_processed": output.get("ai_processed", True),
    }
