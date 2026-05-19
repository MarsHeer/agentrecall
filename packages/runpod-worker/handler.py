"""RunPod Serverless Worker — Qwen2.5-3B memory processing for AgentRecall.

Uses the RunPod serverless protocol. Downloads Qwen2.5-3B (~6GB) on cold start.
"""

import json
import logging
import os
import runpod

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

logger = logging.getLogger(__name__)

# ─── Model Loading (outside handler — once per cold start) ───────────────────

MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
MAX_NEW_TOKENS = 512

logger.info(f"Loading model: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, padding_side="left")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto" if torch.cuda.is_available() else None,
    trust_remote_code=True,
)
logger.info(f"Model loaded on: {model.device}")

# ─── Prompt ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI memory processor. Given a memory text, extract structured info and return ONLY valid JSON.

Return exactly this JSON (no markdown, no explanation):
{"category": "<correction|preference|temporal|factual|general>", "importance": "<high|medium|low>", "entities": [{"name": "...", "type": "person|place|tool|concept|date"}], "relationships": [{"source": "...", "target": "...", "type": "..."}], "summary": "<one sentence, max 100 chars>", "keywords": ["kw1", "kw2"]}

Rules: "prefer/like/hate/always/never use" = preference. "actually/wrong/correction" = correction. "yesterday/tomorrow/deadline" = temporal. "is/are/was/has/lives" = factual. Else = general.
importance: "high" if correction, strong preference, or deadline. Else "medium".
entities: People, places, tools, concepts, dates.
summary: One sentence, max 100 chars.
keywords: 2-5 searchable words."""


def _run(content: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f'Process this memory:\n\n"{content}"\n\nReturn ONLY the JSON.'},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs, max_new_tokens=MAX_NEW_TOKENS,
            temperature=0.3, top_p=0.9, do_sample=True,
        )

    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

    try:
        if response.startswith("```"):
            response = "\n".join(response.split("\n")[1:-1])
        result = json.loads(response)
    except json.JSONDecodeError:
        result = {"category": "general", "importance": "medium", "entities": [], "relationships": [], "summary": content[:100], "keywords": []}

    if result.get("category") not in {"correction", "preference", "temporal", "factual", "general"}:
        result["category"] = "general"
    if result.get("importance") not in {"high", "medium", "low"}:
        result["importance"] = "medium"

    return result


# ─── Handler ─────────────────────────────────────────────────────────────────

def handler(job):
    job_input = job["input"]
    content = job_input.get("content", "")

    if not content.strip():
        return {"error": "Empty content"}

    return _run(content)


runpod.serverless.start({"handler": handler})
