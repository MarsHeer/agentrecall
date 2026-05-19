"""RunPod Serverless Worker — Qwen2.5-7B memory processing for AgentRecall."""

import json
import logging
import runpod

from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)

# Model loading (outside handler — loaded once per worker)
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MAX_NEW_TOKENS = 1024

logger.info(f"Loading model: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, padding_side="left")
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype="auto", device_map="auto", trust_remote_code=True)
logger.info(f"Model loaded on device: {model.device}")

SYSTEM_PROMPT = """You are an AI memory processor for the AgentRecall platform.
Given a memory text, extract structured information and return ONLY valid JSON.

Return exactly this JSON structure (no markdown, no explanation):
{
  "category": "<one of: correction, preference, temporal, factual, general>",
  "importance": "<one of: high, medium, low>",
  "entities": [{"name": "...", "type": "..."}],
  "relationships": [{"source": "...", "target": "...", "type": "..."}],
  "summary": "<one sentence summary, max 100 chars>",
  "keywords": ["keyword1", "keyword2"]
}

Rules:
- category: "prefer/like/hate/always/never use" = preference. "actually/wrong/correction/should be" = correction. "yesterday/tomorrow/deadline" = temporal. "is/are/was/has/lives" = factual. Else = general.
- importance: "high" if correction, strong preference, or deadline. "medium" for facts. "low" for casual.
- entities: Extract people, places, tools, concepts, dates. Type = person/place/tool/concept/date.
- relationships: How entities relate.
- summary: One-line summary, max 100 chars.
- keywords: 2-5 searchable keywords."""

USER_PROMPT_TEMPLATE = '''Process this memory:

"{content}"

Return ONLY the JSON, no markdown fences.'''


def _run_inference(content):
    """Run Qwen2.5-7B on a single memory."""
    import torch

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(content=content)},
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, temperature=0.3, top_p=0.9, do_sample=True)

    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

    # Parse JSON
    try:
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        result = json.loads(response)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse LLM response: {response[:200]}")
        result = {
            "category": "general",
            "importance": "medium",
            "entities": [],
            "relationships": [],
            "summary": content[:100],
            "keywords": [],
        }

    # Validate
    if result.get("category") not in {"correction", "preference", "temporal", "factual", "general"}:
        result["category"] = "general"
    if result.get("importance") not in {"high", "medium", "low"}:
        result["importance"] = "medium"

    return result


def process_memory(job):
    """Process a single memory."""
    job_input = job["input"]
    content = job_input.get("content", "")

    if not content.strip():
        return {"error": "Empty content"}

    result = _run_inference(content)
    return result


def batch_process_memories(job):
    """Process multiple memories in one call."""
    job_input = job["input"]
    memories = job_input.get("memories", [])

    if not memories:
        return {"error": "Empty memories list"}

    results = []
    for mem in memories:
        content = mem.get("content", "")
        memory_id = mem.get("id", None)

        if not content.strip():
            results.append({"id": memory_id, "error": "Empty content"})
            continue

        parsed = _run_inference(content)
        parsed["id"] = memory_id
        results.append(parsed)

    return {"results": results}


runpod.serverless.start({"handler": process_memory})
