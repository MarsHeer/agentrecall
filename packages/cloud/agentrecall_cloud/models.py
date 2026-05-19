from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# --- Memory ---

class MemoryCreate(BaseModel):
    content: str
    agent_id: str
    category: Optional[str] = None
    importance: str = "medium"
    metadata: dict = Field(default_factory=dict)


class MemoryResponse(BaseModel):
    id: int
    agent_id: str
    content: str
    category: str
    importance: str
    confidence: float
    skipped: bool
    access_count: int
    created_at: str
    updated_at: str
    metadata: dict = Field(default_factory=dict)
    ai_processed: bool = False
    summary: str = ""
    keywords: list = Field(default_factory=list)
    entities: list = Field(default_factory=list)
    relationships: list = Field(default_factory=list)


class RecallResult(BaseModel):
    id: int
    agent_id: str
    content: str
    category: str
    importance: str
    confidence: float
    score: float
    created_at: str


# --- Agent ---

class MemoryUpdate(BaseModel):
    content: str


class AgentCreate(BaseModel):
    name: str


class AgentUpdate(BaseModel):
    name: str


class AgentResponse(BaseModel):
    id: str
    name: str
    memory_count: int
    created_at: str
    last_active_at: Optional[str] = None


# --- API Key ---

class ApiKeyCreate(BaseModel):
    name: str = "default"


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: str
    last_used_at: Optional[str] = None


class ApiKeyCreatedResponse(ApiKeyResponse):
    full_key: str  # Only returned on creation


# --- Billing ---

class CheckoutSession(BaseModel):
    url: str


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    stripe_customer_id: Optional[str] = None


class PortalResponse(BaseModel):
    url: str


# --- Usage ---

class UsageResponse(BaseModel):
    api_calls_today: int
    memories_stored: int
    memories_recalled: int
    plan: str
    limit: int


# --- Generic ---

class CountResponse(BaseModel):
    count: int


class MessageResponse(BaseModel):
    message: str
