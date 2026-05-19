from dataclasses import dataclass, field


@dataclass
class AgentMemoryConfig:
    db_path: str = "agentrecall.db"
    embedding_model: str = "all-MiniLM-L6-v2"
    max_context_tokens: int = 500
    classification_model: str = "gpt-4o-mini"
    use_local_embeddings: bool = True
    decay_rate: float = 0.01   # confidence decay per day (multiplicative)
    min_confidence: float = 0.1  # below this, auto-delete
