from agentrecall.models import Memory


def test_memory_creation():
    m = Memory(agent="test", content="User lives in Marbella")
    assert m.agent == "test"
    assert m.content == "User lives in Marbella"
    assert m.category == "general"
    assert m.confidence == 1.0
    assert m.skipped is False
    assert m.importance == "medium"


def test_memory_with_category():
    m = Memory(agent="test", content="I prefer vim", category="preference", importance="high")
    assert m.category == "preference"
    assert m.importance == "high"
