from agentrecall.models import Memory, MemoryType

def test_memory_creation():
    m = Memory(agent_id="test", content="User lives in Marbella")
    assert m.agent_id == "test"
    assert m.content == "User lives in Marbella"
    assert m.memory_type == MemoryType.USER_FACT
    assert m.confidence == 1.0
