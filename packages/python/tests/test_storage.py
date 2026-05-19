from agentrecall.storage import SQLiteStorage
from agentrecall.models import Memory

import pytest


@pytest.fixture
def storage():
    return SQLiteStorage(":memory:")


def test_store_and_retrieve(storage):
    m = Memory(agent="test", content="User lives in Marbella")
    stored = storage.store(m)
    assert stored.id is not None


def test_search(storage):
    m = Memory(agent="test", content="User lives in Marbella")
    storage.store(m)
    results = storage.search("test", "Marbella")
    assert len(results) >= 1
    assert "Marbella" in results[0].content


def test_delete(storage):
    m = Memory(agent="test", content="Temporary fact")
    stored = storage.store(m)
    storage.delete(stored.id)
    results = storage.search("test", "Temporary")
    assert len(results) == 0


def test_get(storage):
    m = Memory(agent="test", content="Important fact")
    stored = storage.store(m)
    fetched = storage.get(stored.id)
    assert fetched is not None
    assert fetched.content == "Important fact"


def test_list_all(storage):
    for i in range(3):
        storage.store(Memory(agent="test", content=f"Fact {i}"))
    results = storage.list_all("test")
    assert len(results) == 3


def test_count(storage):
    for i in range(3):
        storage.store(Memory(agent="test", content=f"Fact {i}"))
    assert storage.count("test") == 3
    assert storage.count() == 3


def test_wipe(storage):
    for i in range(3):
        storage.store(Memory(agent="test", content=f"Fact {i}"))
    storage.store(Memory(agent="other", content="Other fact"))
    storage.wipe(agent="test")
    assert storage.count("test") == 0
    assert storage.count("other") == 1


def test_skip_unskip(storage):
    m = storage.store(Memory(agent="test", content="Skippable fact"))
    storage.skip(m.id)
    fetched = storage.get(m.id)
    assert fetched.skipped is True
    storage.unskip(m.id)
    fetched = storage.get(m.id)
    assert fetched.skipped is False


def test_embedding_storage(storage):
    m = storage.store(Memory(agent="test", content="With embedding"))
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    storage.store_embedding(m.id, embedding)
    retrieved = storage.get_embedding(m.id)
    assert retrieved is not None
    assert len(retrieved) == 5
    for a, b in zip(retrieved, embedding):
        assert abs(a - b) < 1e-6
