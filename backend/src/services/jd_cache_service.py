"""
JD cache service — fingerprinting and two-tier cache for job description analysis.

Implements:
- SHA-256 fingerprinting of normalized JD text for deduplication.
- Two-tier cache: Redis (fast, ephemeral) → MongoDB (durable, shared).
- Write-through: cache hits update both tiers, new entries written to both.
- Graceful degradation: Redis failures fall through to MongoDB tier.
"""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

import structlog

from src.db.documents.jd_analysis_cache import JDAnalysisCache
from src.repositories.jd_cache_repository import JDCacheRepository

logger = structlog.get_logger()

CACHE_TTL_DAYS = 30
REDIS_TTL_SECONDS = 86400  # 1 day in Redis


def normalize_text(text: str) -> str:
    """
    Normalize JD text for consistent fingerprinting.

    Strips whitespace, lowercases, and collapses multiple spaces.
    This ensures minor formatting differences don't create duplicate entries.
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def fingerprint(text: str) -> str:
    """Generate a SHA-256 hex digest of normalized text."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class JDCacheService:
    """Two-tier cache for JD analysis results (Redis → MongoDB → LLM fallback)."""

    def __init__(
        self,
        cache_repo: JDCacheRepository,
        redis_client=None,
    ) -> None:
        self._cache_repo = cache_repo
        self._redis = redis_client

    async def get_or_analyze(
        self,
        jd_text: str,
        analyze_fn=None,
    ) -> dict:
        """
        Return cached analysis or run analyze_fn and cache the result.

        Lookup order:
        1. Redis (fast, 1-day TTL)
        2. MongoDB (durable, 30-day TTL)
        3. analyze_fn fallback (LLM decode)

        Args:
            jd_text: Raw job description text.
            analyze_fn: Async callable that returns an analysis dict.
                       Called only on cache miss.

        Returns:
            Analysis dict with cache_hit indicator.
        """
        fp = fingerprint(jd_text)

        # Tier 1: Redis
        redis_result = await self._get_from_redis(fp)
        if redis_result is not None:
            logger.debug("jd_cache_hit", tier="redis", fingerprint=fp[:12])
            try:
                await self._cache_repo.increment_hit_count(fp)
            except Exception:
                logger.warning("hit_count_increment_failed", fingerprint=fp[:12])
            return {**redis_result, "cache_hit": True, "cache_tier": "redis"}

        # Tier 2: MongoDB
        mongo_entry = await self._cache_repo.get_by_fingerprint(fp)
        if mongo_entry is not None:
            logger.debug("jd_cache_hit", tier="mongodb", fingerprint=fp[:12])
            try:
                await self._cache_repo.increment_hit_count(fp)
            except Exception:
                logger.warning("hit_count_increment_failed", fingerprint=fp[:12])
            await self._set_in_redis(fp, mongo_entry.analysis)
            return {**mongo_entry.analysis, "cache_hit": True, "cache_tier": "mongodb"}

        # Tier 3: LLM decode (cache miss)
        if analyze_fn is None:
            return {"cache_hit": False, "error": "no_analyze_fn"}

        logger.info("jd_cache_miss", fingerprint=fp[:12])
        try:
            analysis = await analyze_fn(jd_text)
        except Exception:
            logger.exception("jd_analyze_fn_failed", fingerprint=fp[:12])
            raise

        token_count = analysis.get("token_count", 0)
        cost_usd = analysis.get("cost_usd", 0.0)
        cache_analysis = {k: v for k, v in analysis.items() if k not in ("token_count", "cost_usd")}

        # Write-through to both tiers (upsert to handle concurrent misses)
        try:
            existing = await self._cache_repo.get_by_fingerprint(fp)
            if existing is None:
                entry = JDAnalysisCache(
                    fingerprint=fp,
                    analysis=cache_analysis,
                    expires_at=datetime.now(UTC) + timedelta(days=CACHE_TTL_DAYS),
                    token_count=token_count,
                    cost_usd=cost_usd,
                )
                await self._cache_repo.create(entry)
        except Exception:
            logger.warning("jd_cache_write_failed", fingerprint=fp[:12])
        await self._set_in_redis(fp, cache_analysis)

        return {**cache_analysis, "cache_hit": False, "cache_tier": "none"}

    async def _get_from_redis(self, fp: str) -> dict | None:
        """Try to get cached analysis from Redis. Returns None on miss or error."""
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(f"jd_cache:{fp}")
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            logger.warning("redis_get_failed", fingerprint=fp[:12])
            return None

    async def _set_in_redis(self, fp: str, analysis: dict) -> None:
        """Write analysis to Redis with TTL. Failures are silently logged."""
        if self._redis is None:
            return
        try:
            await self._redis.set(
                f"jd_cache:{fp}",
                json.dumps(analysis),
                ex=REDIS_TTL_SECONDS,
            )
        except Exception:
            logger.warning("redis_set_failed", fingerprint=fp[:12])
