import pytest
from agentrecall.memory import MemoryStore


@pytest.fixture
def store():
    return MemoryStore(":memory:")


def test_remember_and_recall(store):
    store.remember("User lives in Marbella, Spain", agent="test_agent")
    results = store.recall("where does the user live?", agent="test_agent")
    assert len(results) >= 1
    assert "Marbella" in results[0].content


def test_skip_deprioritizes(store):
    """Skipped memories should score lower than non-skipped."""
    m = store.remember("User lives in Marbella", agent="test_agent")
    results_before = store.recall("Marbella", agent="test_agent")
    score_before = results_before[0].score

    store.skip(m.id)

    results_after = store.recall("Marbella", agent="test_agent")
    score_after = results_after[0].score
    assert score_after < score_before


def test_correction_high_importance(store):
    store.remember("Don't pretend to be the user", agent="test_agent")
    results = store.recall("how should the agent behave?", agent="test_agent")
    assert len(results) >= 1
    assert results[0].importance == "high"


def test_preference_category(store):
    store.remember("I prefer concise responses", agent="test_agent")
    results = store.recall(
        "what are the user's communication preferences?",
        agent="test_agent",
    )
    assert len(results) >= 1
    assert results[0].category == "preference"


def test_remember_returns_memory(store):
    """remember() always returns a Memory, even for skip-pattern content."""
    result = store.remember("pip install completed successfully", agent="test_agent")
    assert result is not None
    assert result.content == "pip install completed successfully"


def test_count(store):
    store.remember("Fact one", agent="test_agent")
    store.remember("Fact two", agent="test_agent")
    assert store.count("test_agent") == 2


def test_get(store):
    m = store.remember("Retrievable fact", agent="test_agent")
    fetched = store.get(m.id)
    assert fetched is not None
    assert fetched.content == "Retrievable fact"


def test_get_not_found(store):
    assert store.get(999999) is None


def test_update(store):
    m = store.remember("Original content", agent="test_agent")
    store.update(m.id, "Updated content")
    fetched = store.get(m.id)
    assert fetched.content == "Updated content"


def test_delete(store):
    m = store.remember("To be deleted", agent="test_agent")
    store.delete(m.id)
    assert store.get(m.id) is None


def test_skip_and_unskip(store):
    m = store.remember("Skippable memory", agent="test_agent")
    store.skip(m.id)
    fetched = store.get(m.id)
    assert fetched.skipped is True
    store.unskip(m.id)
    fetched = store.get(m.id)
    assert fetched.skipped is False


def test_wipe(store):
    store.remember("Fact one", agent="test_agent")
    store.remember("Fact two", agent="other_agent")
    store.wipe(agent="test_agent")
    assert store.count("test_agent") == 0
    assert store.count("other_agent") == 1


def test_wipe_all(store):
    store.remember("Fact one", agent="test_agent")
    store.remember("Fact two", agent="other_agent")
    store.wipe()
    assert store.count() == 0


def test_empty_content_raises(store):
    with pytest.raises(ValueError):
        store.remember("", agent="test_agent")
    with pytest.raises(ValueError):
        store.remember("   ", agent="test_agent")


def test_context_manager():
    with MemoryStore(":memory:") as store:
        store.remember("Test", agent="test_agent")
        assert store.count("test_agent") == 1
    # After exiting, store should be closed
    assert store._closed is True


def test_category_filter(store):
    store.remember("I prefer dark mode", agent="test_agent")
    store.remember("User lives in Berlin", agent="test_agent")
    results_pref = store.recall("preferences", agent="test_agent", category="preference")
    results_fact = store.recall("where does user live", agent="test_agent", category="factual")
    # Each category filter should return relevant results
    if results_pref:
        assert results_pref[0].category == "preference"
    if results_fact:
        assert results_fact[0].category == "factual"
