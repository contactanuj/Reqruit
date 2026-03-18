"""Tests for JDCacheService — fingerprinting and two-tier cache."""

import json
from unittest.mock import AsyncMock, MagicMock

from src.services.jd_cache_service import (
    REDIS_TTL_SECONDS,
    JDCacheService,
    fingerprint,
    normalize_text,
)


class TestNormalizeText:
    def test_strips_and_lowercases(self):
        assert normalize_text("  Hello World  ") == "hello world"

    def test_collapses_whitespace(self):
        assert normalize_text("hello   world\n\tfoo") == "hello world foo"

    def test_empty_string(self):
        assert normalize_text("") == ""


class TestFingerprint:
    def test_deterministic(self):
        fp1 = fingerprint("Senior Backend Engineer")
        fp2 = fingerprint("Senior Backend Engineer")
        assert fp1 == fp2

    def test_normalized_variants_match(self):
        fp1 = fingerprint("Senior  Backend  Engineer")
        fp2 = fingerprint("senior backend engineer")
        assert fp1 == fp2

    def test_different_text_different_fingerprint(self):
        fp1 = fingerprint("Backend Engineer")
        fp2 = fingerprint("Frontend Engineer")
        assert fp1 != fp2

    def test_returns_hex_string(self):
        fp = fingerprint("test")
        assert len(fp) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in fp)


class TestGetOrAnalyzeRedisHit:
    async def test_returns_from_redis_on_hit(self):
        cache_repo = MagicMock()
        cache_repo.increment_hit_count = AsyncMock()
        redis = AsyncMock()
        analysis = {"role": "Engineer", "skills": ["Python"]}
        redis.get = AsyncMock(return_value=json.dumps(analysis))

        service = JDCacheService(cache_repo=cache_repo, redis_client=redis)
        result = await service.get_or_analyze("Some JD text")

        assert result["cache_hit"] is True
        assert result["cache_tier"] == "redis"
        assert result["role"] == "Engineer"
        cache_repo.increment_hit_count.assert_awaited_once()

    async def test_redis_failure_falls_through(self):
        cache_repo = MagicMock()
        cache_repo.get_by_fingerprint = AsyncMock(return_value=None)
        cache_repo.create = AsyncMock()
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        redis.set = AsyncMock()

        analyze_fn = AsyncMock(return_value={"role": "Engineer", "token_count": 100, "cost_usd": 0.01})

        service = JDCacheService(cache_repo=cache_repo, redis_client=redis)
        result = await service.get_or_analyze("Some JD text", analyze_fn=analyze_fn)

        assert result["cache_hit"] is False
        assert result["cache_tier"] == "none"


class TestGetOrAnalyzeMongoHit:
    async def test_returns_from_mongo_on_redis_miss(self):
        analysis = {"role": "Engineer", "skills": ["Go"]}
        mongo_entry = MagicMock()
        mongo_entry.analysis = analysis

        cache_repo = MagicMock()
        cache_repo.get_by_fingerprint = AsyncMock(return_value=mongo_entry)
        cache_repo.increment_hit_count = AsyncMock()
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()

        service = JDCacheService(cache_repo=cache_repo, redis_client=redis)
        result = await service.get_or_analyze("Some JD text")

        assert result["cache_hit"] is True
        assert result["cache_tier"] == "mongodb"
        assert result["role"] == "Engineer"
        # Should back-fill Redis
        redis.set.assert_awaited_once()

    async def test_backfills_redis_on_mongo_hit(self):
        analysis = {"role": "Engineer"}
        mongo_entry = MagicMock()
        mongo_entry.analysis = analysis

        cache_repo = MagicMock()
        cache_repo.get_by_fingerprint = AsyncMock(return_value=mongo_entry)
        cache_repo.increment_hit_count = AsyncMock()
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()

        service = JDCacheService(cache_repo=cache_repo, redis_client=redis)
        await service.get_or_analyze("Some JD text")

        fp = fingerprint("Some JD text")
        redis.set.assert_awaited_once_with(
            f"jd_cache:{fp}",
            json.dumps(analysis),
            ex=REDIS_TTL_SECONDS,
        )


class TestGetOrAnalyzeCacheMiss:
    async def test_calls_analyze_fn_on_miss(self):
        cache_repo = MagicMock()
        cache_repo.get_by_fingerprint = AsyncMock(return_value=None)
        cache_repo.create = AsyncMock()

        analyze_fn = AsyncMock(return_value={
            "role": "Backend Engineer",
            "token_count": 200,
            "cost_usd": 0.005,
        })

        service = JDCacheService(cache_repo=cache_repo, redis_client=None)
        result = await service.get_or_analyze("New JD", analyze_fn=analyze_fn)

        assert result["cache_hit"] is False
        assert result["cache_tier"] == "none"
        assert result["role"] == "Backend Engineer"
        analyze_fn.assert_awaited_once_with("New JD")
        cache_repo.create.assert_awaited_once()

    async def test_writes_through_to_both_tiers(self):
        cache_repo = MagicMock()
        cache_repo.get_by_fingerprint = AsyncMock(return_value=None)
        cache_repo.create = AsyncMock()
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()

        analyze_fn = AsyncMock(return_value={
            "role": "SRE",
            "token_count": 150,
            "cost_usd": 0.003,
        })

        service = JDCacheService(cache_repo=cache_repo, redis_client=redis)
        await service.get_or_analyze("New JD", analyze_fn=analyze_fn)

        cache_repo.create.assert_awaited_once()
        redis.set.assert_awaited_once()

    async def test_returns_error_when_no_analyze_fn(self):
        cache_repo = MagicMock()
        cache_repo.get_by_fingerprint = AsyncMock(return_value=None)

        service = JDCacheService(cache_repo=cache_repo, redis_client=None)
        result = await service.get_or_analyze("JD text")

        assert result["cache_hit"] is False
        assert result["error"] == "no_analyze_fn"

    async def test_strips_token_count_and_cost_from_cached_analysis(self):
        cache_repo = MagicMock()
        cache_repo.get_by_fingerprint = AsyncMock(return_value=None)
        cache_repo.create = AsyncMock()

        analyze_fn = AsyncMock(return_value={
            "role": "DevOps",
            "token_count": 300,
            "cost_usd": 0.01,
        })

        service = JDCacheService(cache_repo=cache_repo, redis_client=None)
        await service.get_or_analyze("JD text", analyze_fn=analyze_fn)

        # token_count and cost_usd should be stripped from the analysis dict
        # (they go to JDAnalysisCache fields, not into the analysis blob)
        created_entry = cache_repo.create.call_args[0][0]
        assert "token_count" not in created_entry.analysis
        assert "cost_usd" not in created_entry.analysis
        assert created_entry.token_count == 300
        assert created_entry.cost_usd == 0.01


class TestNoRedis:
    async def test_works_without_redis(self):
        analysis = {"role": "Tester"}
        mongo_entry = MagicMock()
        mongo_entry.analysis = analysis

        cache_repo = MagicMock()
        cache_repo.get_by_fingerprint = AsyncMock(return_value=mongo_entry)
        cache_repo.increment_hit_count = AsyncMock()

        service = JDCacheService(cache_repo=cache_repo, redis_client=None)
        result = await service.get_or_analyze("JD text")

        assert result["cache_hit"] is True
        assert result["cache_tier"] == "mongodb"
