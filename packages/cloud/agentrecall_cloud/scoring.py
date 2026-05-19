"""Memory classification and scoring — matches the open-source SDK spec."""

import re
from datetime import datetime, timezone

# Classification rules — MUST match the SDK
CATEGORY_PATTERNS = {
    "correction": re.compile(
        r"\b(actually|in fact|correction|wrong|not quite|instead|should be|"
        r"meant to|I meant|don'?t|never|stop)\b",
        re.IGNORECASE,
    ),
    "preference": re.compile(
        r"\b(prefer|like|love|hate|favorite|best|worst|always|never use|"
        r"do not use|use instead|switch to|my style|I want|keep it)\b",
        re.IGNORECASE,
    ),
    "temporal": re.compile(
        r"\b(yesterday|today|tomorrow|last (week|month|year)|next (week|month|year)|"
        r"ago|recently|deadline|reminder|schedule|\d{4}-\d{2}-\d{2})\b",
        re.IGNORECASE,
    ),
    "factual": re.compile(
        r"\b(is|are|was|were|has|have|had|located|found|based|lives)\b",
        re.IGNORECASE,
    ),
}

# Importance weights
IMPORTANCE_WEIGHTS = {"high": 1.3, "medium": 1.0, "low": 0.7}

# Skip patterns (auto-skip noise)
SKIP_PATTERNS = [
    re.compile(r"wget.*download", re.IGNORECASE),
    re.compile(r"apt-get.*install", re.IGNORECASE),
    re.compile(r"pip.*install", re.IGNORECASE),
    re.compile(r"command.*executed", re.IGNORECASE),
    re.compile(r"process.*started", re.IGNORECASE),
    re.compile(r"downloaded.*successfully", re.IGNORECASE),
    re.compile(r"installation complete", re.IGNORECASE),
    re.compile(r"backup.*created", re.IGNORECASE),
]


def classify(content: str) -> str:
    """Auto-classify memory content."""
    for category, pattern in CATEGORY_PATTERNS.items():
        if pattern.search(content):
            return category
    return "general"


def should_skip(content: str) -> bool:
    """Check if content should be auto-skipped."""
    return any(p.search(content) for p in SKIP_PATTERNS)


def compute_score(
    similarity: float,
    confidence: float,
    importance: str,
    created_at: datetime,
    skipped: bool,
) -> float:
    """Compute recall score — MUST match the SDK spec.

    score = similarity × confidence × importance_weight × recency × skip_penalty
    """
    importance_weight = IMPORTANCE_WEIGHTS.get(importance, 1.0)
    now = datetime.now(timezone.utc)
    days_since = (now - created_at).total_seconds() / 86400
    recency = 1.0 / (1.0 + days_since * 0.05)
    skip_penalty = 0.2 if skipped else 1.0

    return similarity * confidence * importance_weight * recency * skip_penalty


def decay_confidence(confidence: float, decay_rate: float = 0.01) -> float:
    """Apply confidence decay."""
    new_conf = confidence * (1.0 - decay_rate)
    return max(new_conf, 0.0)
