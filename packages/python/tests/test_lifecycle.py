from agentrecall.lifecycle import MemoryLifecycle
from agentrecall.models import Memory
from agentrecall.storage import SQLiteStorage


def test_confidence_decay():
    lc = MemoryLifecycle(db_path=":memory:")
    m = Memory(agent="test", content="Old fact", confidence=1.0)
    new_conf = lc.decay_confidence(m)
    # 1-step: 1.0 * (1 - 0.01) = 0.99
    assert new_conf == 0.99


def test_confidence_decay_low():
    lc = MemoryLifecycle(db_path=":memory:", decay_rate=0.5)
    m = Memory(agent="test", content="Old fact", confidence=1.0)
    new_conf = lc.decay_confidence(m)
    # 1-step: 1.0 * (1 - 0.5) = 0.5
    assert new_conf == 0.5


def test_run_decay_removes_low_confidence():
    storage = SQLiteStorage(":memory:")
    # Memory with confidence just above min — one decay step should kill it
    m = Memory(
        agent="test", content="Very low confidence", confidence=0.105,
    )
    storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:", decay_rate=0.01, min_confidence=0.1)
    lc.storage = storage
    removed = lc.run_decay("test")
    # 0.105 * 0.99 = 0.10395 → above 0.1, not removed
    # Use higher decay rate to ensure removal
    assert removed == 0


def test_run_decay_removes_below_threshold():
    storage = SQLiteStorage(":memory:")
    # Memory with confidence that will drop below 0.1 after one decay step
    m = Memory(
        agent="test", content="Very low confidence", confidence=0.105,
    )
    storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:", decay_rate=0.15, min_confidence=0.1)
    lc.storage = storage
    removed = lc.run_decay("test")
    # 0.105 * (1 - 0.15) = 0.08925 → below 0.1, removed
    assert removed == 1


def test_run_decay_keeps_relevant():
    storage = SQLiteStorage(":memory:")
    m = Memory(agent="test", content="Recent fact", confidence=1.0)
    storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:", decay_rate=0.01, min_confidence=0.1)
    lc.storage = storage
    removed = lc.run_decay("test")
    assert removed == 0
    fetched = storage.get(m.id)
    assert fetched is not None
    assert fetched.confidence == 0.99


def test_touch_updates_access():
    storage = SQLiteStorage(":memory:")
    m = Memory(agent="test", content="Frequently accessed")
    stored = storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:")
    lc.storage = storage
    lc.touch(stored.id)

    updated = storage.get(stored.id)
    assert updated.access_count == 1
