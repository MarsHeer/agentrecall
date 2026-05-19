from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional

class MemoryType(str, Enum):
    USER_FACT = "user_fact"
    PREFERENCE = "preference"
    CORRECTION = "correction"
    ENVIRONMENT = "environment"
    TEMPORARY = "temporary"
    SKIP = "skip"

class MemoryPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Memory(BaseModel):
    id: Optional[str] = None
    agent_id: str
    content: str
    memory_type: MemoryType = MemoryType.USER_FACT
    priority: MemoryPriority = MemoryPriority.MEDIUM
    tags: list[str] = []
    confidence: float = 1.0
    ttl_seconds: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None

class RecallResult(BaseModel):
    memory: Memory
    score: float
    source: str  # "semantic" | "keyword" | "recency" | "graph"
