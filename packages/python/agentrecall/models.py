from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional


class Memory(BaseModel):
    """Memory data model matching the unified API spec."""
    id: Optional[int] = None
    content: str
    category: str = "general"          # preference, correction, temporal, factual, general
    agent: str = "default"
    importance: str = "medium"          # high, medium, low
    confidence: float = 1.0
    skipped: bool = False
    access_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)
    embedding: Optional[list[float]] = None
    ai_processed: bool = False
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)


class RecallResult(Memory):
    """Memory with a composite relevance score. Flattened — access result.content directly."""
    score: float = 0.0
