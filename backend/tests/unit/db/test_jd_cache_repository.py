"""Tests for JDCacheRepository — fingerprint-based cache lookups."""

from unittest.mock import AsyncMock, MagicMock, patch

from src.repositories.jd_cache_repository import JDCacheRepository


def _make_cache_entry(**overrides):
    defaults = {
        "fingerprint": "abc123def456",
        "analysis": {"role": "Backend Engineer", "skills": ["Python"]},
        "hit_count": 0,
        "token_count": 500,
        "cost_usd": 0.01,
    }
    defaults.update(overrides)
    entry = MagicMock()
    for k, v in defaults.items():
        setattr(entry, k, v)
    entry.set = AsyncMock()
    return entry


class TestGetByFingerprint:
    async def test_returns_entry_when_found(self):
        repo = JDCacheRepository()
        expected = _make_cache_entry()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=expected):
            result = await repo.get_by_fingerprint("abc123def456")
        assert result == expected

    async def test_returns_none_when_missing(self):
        repo = JDCacheRepository()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None):
            result = await repo.get_by_fingerprint("nonexistent")
        assert result is None


class TestIncrementHitCount:
    async def test_increments_and_returns_entry(self):
        repo = JDCacheRepository()
        entry = _make_cache_entry(hit_count=3)
        with patch.object(repo, "get_by_fingerprint", new_callable=AsyncMock, return_value=entry):
            result = await repo.increment_hit_count("abc123def456")
        assert result == entry
        entry.set.assert_awaited_once_with({"hit_count": 4})

    async def test_returns_none_when_missing(self):
        repo = JDCacheRepository()
        with patch.object(repo, "get_by_fingerprint", new_callable=AsyncMock, return_value=None):
            result = await repo.increment_hit_count("nonexistent")
        assert result is None


class TestGetAnalytics:
    async def test_aggregates_stats(self):
        repo = JDCacheRepository()
        entries = [
            _make_cache_entry(hit_count=10, cost_usd=0.02, token_count=400),
            _make_cache_entry(hit_count=5, cost_usd=0.01, token_count=200),
        ]
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=entries):
            stats = await repo.get_analytics()
        assert stats["total_entries"] == 2
        assert stats["total_hits"] == 15
        assert stats["total_cost_usd"] == 0.03
        assert stats["total_tokens"] == 600
        assert stats["avg_cost_per_entry_usd"] == 0.015
        # estimated_savings = 15 hits * 0.015 avg cost = 0.225
        assert stats["estimated_savings_usd"] == 0.225

    async def test_empty_cache_returns_zeros(self):
        repo = JDCacheRepository()
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=[]):
            stats = await repo.get_analytics()
        assert stats["total_entries"] == 0
        assert stats["total_hits"] == 0
        assert stats["total_cost_usd"] == 0.0
        assert stats["estimated_savings_usd"] == 0.0
        assert stats["hit_rate"] == 0.0
