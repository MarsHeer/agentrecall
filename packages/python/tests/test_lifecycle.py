from datetime import datetime, timedelta, timezone
from agentrecall.lifecycle import MemoryLifecycle
from agentrecall.models import Memory
from agentrecall.storage import SQLiteStorage


def test_confidence_decay():
    lc = MemoryLifecycle(db_path=":memory:")
    m = Memory(agent="test", content="Old fact", confidence=1.0)
    new_conf = lc.decay_confidence(m, days=30)
    # Multiplicative: 1.0 * 0.99^30 ≈ 0.740
    assert new_conf < 1.0
    assert new_conf > 0.5


def test_run_decay_removes_low_confidence():
    storage = SQLiteStorage(":memory:")
    # Create a memory that's 250 days old with default confidence
    # 0.99^250 ≈ 0.081, below min_confidence of 0.1
    m = Memory(
        agent="test", content="Very old fact", confidence=1.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=250),
        updated_at=datetime.now(timezone.utc) - timedelta(days=250),
    )
    storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:", decay_rate=0.01, min_confidence=0.1)
    lc.storage = storage
    removed = lc.run_decay("test")
    assert removed == 1


def test_run_decay_keeps_relevant():
    storage = SQLiteStorage(":memory:")
    # Create a recent memory
    m = Memory(
        agent="test", content="Recent fact", confidence=1.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        updated_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:", decay_rate=0.01, min_confidence=0.1)
    lc.storage = storage
    removed = lc.run_decay("test")
    assert removed == 0
    fetched = storage.get(m.id)
    assert fetched is not None
    assert fetched.confidence > 0.9


def test_touch_updates_access():
    storage = SQLiteStorage(":memory:")
    m = Memory(agent="test", content="Frequently accessed")
    stored = storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:")
    lc.storage = storage
    lc.touch(stored.id)

    updated = storage.get(stored.id)
    assert updated.access_count == 1
