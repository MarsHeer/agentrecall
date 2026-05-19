from agentrecall.models import Memory, RecallResult
from agentrecall.config import AgentMemoryConfig
from agentrecall.cloud import CloudClient

__version__ = "0.2.0"
__all__ = ["Memory", "RecallResult", "AgentMemoryConfig", "CloudClient"]


# Lazy import to avoid circular deps during init
def __getattr__(name):
    if name == "MemoryStore":
        from agentrecall.memory import MemoryStore
        return MemoryStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
