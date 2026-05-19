import re


class MemoryClassifier:
    """Classify memory content into categories per the unified API spec.

    Categories and trigger patterns (MUST be identical across SDKs):
    - correction: actually, in fact, correction, wrong, not quite, instead,
                  should be, meant to, I meant, don't, never, stop
    - preference: prefer, like, love, hate, favorite, best, worst, always,
                  never use, do not use, use instead, switch to, my style,
                  I want, keep it
    - temporal: yesterday, today, tomorrow, last week/month/year,
                next week/month/year, ago, recently, deadline, reminder,
                schedule, YYYY-MM-DD dates
    - factual: is, are, was, were, has, have, had, located, found, based, lives
    - general: fallback for anything unclassified
    """

    # Multi-word preference patterns are checked before correction patterns
    # to avoid "never use" matching as correction via "never"
    PREFERENCE_PATTERNS = [
        r"\bprefer\b",
        r"\blike\b",
        r"\blove\b",
        r"\bhate\b",
        r"\bfavorite\b",
        r"\bbest\b",
        r"\bworst\b",
        r"\balways\b",
        r"\bnever use\b",
        r"\bdo not use\b",
        r"\buse instead\b",
        r"\bswitch to\b",
        r"\bmy style\b",
        r"\bi want\b",
        r"\bkeep it\b",
    ]

    CORRECTION_PATTERNS = [
        r"\bactually\b",
        r"\bin fact\b",
        r"\bcorrection\b",
        r"\bwrong\b",
        r"\bnot quite\b",
        r"\binstead\b",
        r"\bshould be\b",
        r"\bmeant to\b",
        r"\bi meant\b",
        r"\bdon'?t\b",
        r"\bnever\b",
        r"\bstop\b",
    ]

    TEMPORAL_PATTERNS = [
        r"\byesterday\b",
        r"\btoday\b",
        r"\btomorrow\b",
        r"\blast\s+(week|month|year)\b",
        r"\bnext\s+(week|month|year)\b",
        r"\bage\b",
        r"\brecently\b",
        r"\bdeadline\b",
        r"\breminder\b",
        r"\bschedule\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]

    FACTUAL_PATTERNS = [
        r"\bis\b", r"\bare\b", r"\bwas\b", r"\bwere\b",
        r"\bhas\b", r"\bhave\b", r"\bhad\b",
        r"\blocated\b", r"\bfound\b", r"\bbased\b", r"\blives\b",
    ]

    def __init__(self, use_llm: bool = False, model: str = "gpt-4o-mini"):
        self.use_llm = use_llm
        self.model = model

    def classify(self, content: str) -> dict:
        """Classify content into a category with importance.

        Returns dict with keys: category, importance
        """
        content_lower = content.lower()

        # Check preference first (multi-word patterns like "never use"
        # are more specific than correction's standalone "never")
        for pattern in self.PREFERENCE_PATTERNS:
            if re.search(pattern, content_lower):
                return {"category": "preference", "importance": "high"}

        # Check correction patterns
        for pattern in self.CORRECTION_PATTERNS:
            if re.search(pattern, content_lower):
                return {"category": "correction", "importance": "high"}

        # Check temporal patterns
        for pattern in self.TEMPORAL_PATTERNS:
            if re.search(pattern, content_lower):
                return {"category": "temporal", "importance": "medium"}

        # Check factual patterns
        for pattern in self.FACTUAL_PATTERNS:
            if re.search(pattern, content_lower):
                return {"category": "factual", "importance": "medium"}

        # General fallback
        return {"category": "general", "importance": "medium"}
