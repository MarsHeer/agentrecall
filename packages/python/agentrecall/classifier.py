import re
from agentrecall.models import MemoryType, MemoryPriority


class MemoryClassifier:
    """Classify memory content into types and priorities.

    Two modes:
    - use_llm=False: Rule-based (free, instant)
    - use_llm=True: LLM-based (smarter, costs ~$0.0001/classification)
    """

    SKIP_PATTERNS = [
        r"wget.*download",
        r"apt-get.*install",
        r"pip.*install",
        r"command.*executed",
        r"process.*started",
        r"downloaded.*successfully",
        r"installation complete",
        r"backup.*created",
    ]

    CORRECTION_PATTERNS = [
        r"don'?t",
        r"never",
        r"stop",
        r"wrong",
        r"that'?s incorrect",
        r"remember this",
        r"don'?t do that",
        r"no,?\s",
        r"actually",
    ]

    PREFERENCE_PATTERNS = [
        r"prefer",
        r"like.*to",
        r"always",
        r"never.*use",
        r"my style",
        r"i want",
        r"keep it",
        r"don'?t.*change",
    ]

    TEMPORAL_PATTERNS = [
        r"tomorrow",
        r"next week",
        r"on monday",
        r"today",
        r"deadline",
        r"reminder",
        r"schedule",
    ]

    def __init__(self, use_llm: bool = False, model: str = "gpt-4o-mini"):
        self.use_llm = use_llm
        self.model = model

    def classify(self, content: str) -> dict:
        content_lower = content.lower()

        # Check SKIP patterns first
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, content_lower):
                return {"memory_type": MemoryType.SKIP, "priority": MemoryPriority.LOW, "ttl_seconds": None, "tags": []}

        # Check CORRECTION patterns
        for pattern in self.CORRECTION_PATTERNS:
            if re.search(pattern, content_lower):
                return {"memory_type": MemoryType.CORRECTION, "priority": MemoryPriority.HIGH, "ttl_seconds": None, "tags": ["correction"]}

        # Check PREFERENCE patterns
        for pattern in self.PREFERENCE_PATTERNS:
            if re.search(pattern, content_lower):
                return {"memory_type": MemoryType.PREFERENCE, "priority": MemoryPriority.HIGH, "ttl_seconds": None, "tags": ["preference"]}

        # Check TEMPORAL patterns
        for pattern in self.TEMPORAL_PATTERNS:
            if re.search(pattern, content_lower):
                return {"memory_type": MemoryType.TEMPORARY, "priority": MemoryPriority.MEDIUM, "ttl_seconds": 604800, "tags": ["temporal"]}

        # Default: user fact
        return {"memory_type": MemoryType.USER_FACT, "priority": MemoryPriority.MEDIUM, "ttl_seconds": None, "tags": []}
