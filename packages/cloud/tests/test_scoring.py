"""Tests for AgentRecall Cloud scoring/classification."""

import pytest
from datetime import datetime, timezone, timedelta
from agentrecall_cloud.scoring import classify, should_skip, compute_score, decay_confidence


class TestClassify:
    def test_correction(self):
        assert classify("Actually, that's wrong") == "correction"
        assert classify("You should use Python instead") == "correction"

    def test_preference(self):
        assert classify("I prefer dark mode") == "preference"
        assert classify("I love TypeScript") == "preference"

    def test_temporal(self):
        assert classify("Meeting tomorrow at 3pm") == "temporal"
        assert classify("Deadline is 2026-05-20") == "temporal"

    def test_factual(self):
        assert classify("The server is in Frankfurt") == "factual"
        assert classify("User lives in Marbella") == "factual"

    def test_general_fallback(self):
        assert classify("Some random note") == "general"
        assert classify("Remember to check the logs") == "general"


class TestShouldSkip:
    def test_skip_noise(self):
        assert should_skip("wget download completed") is True
        assert should_skip("apt-get install succeeded") is True
        assert should_skip("pip install finished") is True

    def test_no_skip_normal(self):
        assert should_skip("User prefers dark mode") is False
        assert should_skip("Meeting tomorrow") is False


class TestComputeScore:
    def test_basic_score(self):
        now = datetime.now(timezone.utc)
        score = compute_score(
            similarity=0.8,
            confidence=1.0,
            importance="medium",
            created_at=now,
            skipped=False,
        )
        assert 0.7 < score < 0.9

    def test_high_importance_boost(self):
        now = datetime.now(timezone.utc)
        score = compute_score(
            similarity=0.8,
            confidence=1.0,
            importance="high",
            created_at=now,
            skipped=False,
        )
        assert score > 0.8  # 1.3x boost

    def test_skipped_penalty(self):
        now = datetime.now(timezone.utc)
        score = compute_score(
            similarity=0.8,
            confidence=1.0,
            importance="medium",
            created_at=now,
            skipped=True,
        )
        assert score < 0.2  # 0.2x penalty

    def test_old_memory_decay(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)
        score_old = compute_score(0.8, 1.0, "medium", old, False)
        score_new = compute_score(0.8, 1.0, "medium", now, False)
        assert score_old < score_new


class TestDecayConfidence:
    def test_decay(self):
        assert decay_confidence(1.0) == pytest.approx(0.99)
        assert decay_confidence(0.5) == pytest.approx(0.495)

    def test_minimum(self):
        assert decay_confidence(0.01) == pytest.approx(0.0099, abs=0.001)
