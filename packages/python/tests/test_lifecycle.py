from datetime import datetime, timedelta
from agentrecall.lifecycle import MemoryLifecycle
from agentrecall.models import Memory, MemoryType, MemoryPriority
from agentrecall.storage import SQLiteStorage

def test_expired_memory_removed():
    storage = SQLiteStorage(":memory:")
    m = Memory(
        agent_id="test", content="Appointment tomorrow",
        memory_type=MemoryType.TEMPORARY,
        expires_at=datetime.utcnow() - timedelta(days=1),
        created_at=datetime.utcnow() - timedelta(days=2),
        updated_at=datetime.utcnow() - timedelta(days=2),
    )
    storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:")
    # Point to the same DB
    lc.storage = storage
    removed = lc.cleanup_expired("test")
    assert removed == 1

def test_confidence_decay():
    lc = MemoryLifecycle(db_path=":memory:")
    m = Memory(agent_id="test", content="Old fact", confidence=1.0)
    new_conf = lc.decay_confidence(m, days=30)
    assert new_conf < 1.0
    assert new_conf > 0.5

def test_run_decay_removes_low_confidence():
    storage = SQLiteStorage(":memory:")
    # Create a memory that's 100 days old with default confidence
    m = Memory(
        agent_id="test", content="Very old fact", confidence=1.0,
        created_at=datetime.utcnow() - timedelta(days=100),
        updated_at=datetime.utcnow() - timedelta(days=100),
    )
    storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:", decay_rate=0.01, min_confidence=0.1)
    lc.storage = storage
    removed = lc.run_decay("test")
    # After 100 days: confidence = 1.0 - (0.01 * 100) = 0.0, below min_confidence
    assert removed == 1

def test_touch_updates_access():
    storage = SQLiteStorage(":memory:")
    m = Memory(agent_id="test", content="Frequently accessed")
    stored = storage.store(m)

    lc = MemoryLifecycle(db_path=":memory:")
    lc.storage = storage
    lc.touch(stored.id)

    updated = storage.get(stored.id)
    assert updated.access_count == 1
    assert updated.last_accessed is not None
