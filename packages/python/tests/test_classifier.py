from agentrecall.classifier import MemoryClassifier
from agentrecall.models import MemoryType, MemoryPriority

def test_classify_user_fact():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("User lives in Marbella")
    assert result["memory_type"] == MemoryType.USER_FACT
    assert result["priority"] == MemoryPriority.MEDIUM

def test_classify_correction():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("Don't pretend to be me")
    assert result["memory_type"] == MemoryType.CORRECTION
    assert result["priority"] == MemoryPriority.HIGH

def test_classify_skip():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("wget downloaded 23MB successfully")
    assert result["memory_type"] == MemoryType.SKIP

def test_classify_preference():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("I prefer concise responses")
    assert result["memory_type"] == MemoryType.PREFERENCE
    assert result["priority"] == MemoryPriority.HIGH

def test_classify_temporal():
    c = MemoryClassifier(use_llm=False)
    result = c.classify("Doctor appointment tomorrow")
    assert result["memory_type"] == MemoryType.TEMPORARY
    assert result["ttl_seconds"] == 604800  # 7 days in seconds
