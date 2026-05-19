from agentrecall.storage import SQLiteStorage
from agentrecall.models import Memory

import pytest

@pytest.fixture
def storage():
    return SQLiteStorage(":memory:")

def test_store_and_retrieve(storage):
    m = Memory(agent_id="test", content="User lives in Marbella")
    stored = storage.store(m)
    assert stored.id is not None

def test_search(storage):
    m = Memory(agent_id="test", content="User lives in Marbella")
    storage.store(m)
    results = storage.search("test", "Marbella")
    assert len(results) >= 1
    assert "Marbella" in results[0].content

def test_delete(storage):
    m = Memory(agent_id="test", content="Temporary fact")
    stored = storage.store(m)
    storage.delete(stored.id)
    results = storage.search("test", "Temporary")
    assert len(results) == 0

def test_get(storage):
    m = Memory(agent_id="test", content="Important fact")
    stored = storage.store(m)
    fetched = storage.get(stored.id)
    assert fetched is not None
    assert fetched.content == "Important fact"

def test_list_all(storage):
    for i in range(3):
        storage.store(Memory(agent_id="test", content=f"Fact {i}"))
    results = storage.list_all("test")
    assert len(results) == 3
