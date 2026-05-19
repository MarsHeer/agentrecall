from agentrecall.classifier import MemoryClassifier


def test_classify_factual():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("User lives in Marbella")
    assert result["category"] == "factual"
    assert result["importance"] == "medium"


def test_classify_correction():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("Don't pretend to be me")
    assert result["category"] == "correction"
    assert result["importance"] == "high"


def test_classify_general():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("wget downloaded 23MB successfully")
    assert result["category"] == "general"


def test_classify_preference():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("I prefer concise responses")
    assert result["category"] == "preference"
    assert result["importance"] == "high"


def test_classify_temporal():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("Doctor appointment tomorrow")
    assert result["category"] == "temporal"
    assert result["importance"] == "medium"


def test_classify_correction_never():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("Never do that again")
    assert result["category"] == "correction"


def test_classify_preference_never_use():
    """'never use' should be preference, not correction via 'never'."""
    c = MemoryClassifier(use_llm=False)
    result = c.classify("I never use tabs, always spaces")
    assert result["category"] == "preference"
