"""
Repository for JDAnalysisCache documents — fingerprint-based cache lookups.

Provides methods for fingerprint-keyed cache reads, writes, and hit-count
incrementing for cost analytics.
"""

from src.db.documents.jd_analysis_cache import JDAnalysisCache
from src.repositories.base import BaseRepository


class JDCacheRepository(BaseRepository[JDAnalysisCache]):
    """CRUD operations for JDAnalysisCache with fingerprint-based lookups."""

    def __init__(self) -> None:
        super().__init__(JDAnalysisCache)

    async def get_by_fingerprint(self, fingerprint: str) -> JDAnalysisCache | None:
        """Return a cached analysis by its SHA-256 fingerprint."""
        return await self.find_one({"fingerprint": fingerprint})

    async def increment_hit_count(self, fingerprint: str) -> JDAnalysisCache | None:
        """Increment the hit_count for an existing cache entry."""
        entry = await self.get_by_fingerprint(fingerprint)
        if entry is None:
            return None
        await entry.set({"hit_count": entry.hit_count + 1})
        return entry

    async def get_analytics(self) -> dict:
        """Aggregate cache statistics: total entries, hits, cost savings."""
        all_entries = await self.find_many(filters={}, limit=10000)
        total_entries = len(all_entries)
        total_hits = sum(getattr(e, "hit_count", 0) for e in all_entries)
        total_cost_usd = sum(getattr(e, "cost_usd", 0.0) for e in all_entries)
        total_tokens = sum(getattr(e, "token_count", 0) for e in all_entries)
        # Each cache hit saves one LLM decode — estimated savings = hits * avg cost
        avg_cost = total_cost_usd / total_entries if total_entries > 0 else 0.0
        estimated_savings_usd = total_hits * avg_cost
        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "total_cost_usd": round(total_cost_usd, 4),
            "total_tokens": total_tokens,
            "avg_cost_per_entry_usd": round(avg_cost, 6),
            "estimated_savings_usd": round(estimated_savings_usd, 4),
            "hit_rate": round(total_hits / (total_hits + total_entries), 4) if (total_hits + total_entries) > 0 else 0.0,
        }
