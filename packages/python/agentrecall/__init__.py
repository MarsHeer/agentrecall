from agentrecall.models import Memory, MemoryType, MemoryPriority, RecallResult
from agentrecall.config import AgentMemoryConfig

__version__ = "0.1.0"
__all__ = ["Memory", "MemoryType", "MemoryPriority", "RecallResult", "AgentMemoryConfig"]

# Lazy import to avoid circular deps during init
def __getattr__(name):
    if name == "MemoryStore":
        from agentrecall.memory import MemoryStore
        return MemoryStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
