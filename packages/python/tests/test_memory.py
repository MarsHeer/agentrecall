import pytest
from agentrecall.memory import MemoryStore

@pytest.fixture
def store():
    return MemoryStore(":memory:")

def test_save_and_recall(store):
    store.save("test_agent", "User lives in Marbella, Spain")
    results = store.recall("test_agent", "where does the user live?")
    assert len(results) >= 1
    assert "Marbella" in results[0].memory.content

def test_skip_irrelevant(store):
    store.save("test_agent", "wget downloaded 23MB file successfully")
    results = store.recall("test_agent", "what did wget do?")
    # Should still be stored but classified as SKIP
    # so retrieval should deprioritize it
    assert len(results) == 0 or results[0].memory.memory_type.value == "skip"

def test_correction_high_priority(store):
    store.save("test_agent", "Don't pretend to be the user")
    results = store.recall("test_agent", "how should the agent behave?")
    assert len(results) >= 1
    assert results[0].memory.priority.value == "high"

def test_preference_saved(store):
    store.save("test_agent", "I prefer concise responses")
    results = store.recall("test_agent", "what are the user's communication preferences?")
    assert len(results) >= 1
    assert results[0].memory.memory_type.value == "preference"

def test_save_returns_none_for_skip(store):
    result = store.save("test_agent", "pip install completed successfully")
    assert result is None

def test_count(store):
    store.save("test_agent", "Fact one")
    store.save("test_agent", "Fact two")
    assert store.count("test_agent") == 2
