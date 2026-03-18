"""
Currency conversion service using the Frankfurter API (ECB data).

Provides exchange rate lookups and currency conversion with in-memory
caching and resilience (timeout, retry, stale fallback).

Design decisions
----------------
Why Frankfurter API (not a paid service):
    Free, no API key required, backed by European Central Bank data.
    Rate limit of ~1000 requests/day is more than sufficient. Rates are
    updated daily by ECB — not real-time, but accurate enough for salary
    comparison (not trading).

Why in-memory cache (not Redis):
    Single-instance MVP. Currency rates change slowly (daily). A dict with
    TTL is the simplest correct solution. If we scale to multiple instances,
    switch to Redis.
"""

import asyncio
import time

import httpx
import structlog

logger = structlog.get_logger()

_DEFAULT_BASE_URL = "https://api.frankfurter.app"
_CACHE_TTL_SECONDS = 4 * 3600  # 4 hours
_STALE_THRESHOLD_SECONDS = 24 * 3600  # 24 hours
_TIMEOUT_SECONDS = 10
_MAX_RETRIES = 3


class CurrencyService:
    """Exchange rate lookups and currency conversion."""

    def __init__(self, base_url: str = _DEFAULT_BASE_URL) -> None:
        self._base_url = base_url
        self._cache: dict[str, tuple[float, float]] = {}  # "FROM/TO" -> (rate, timestamp)

    async def get_rate(self, from_currency: str, to_currency: str) -> dict:
        """
        Get exchange rate between two currencies.

        Returns:
            {"rate": float, "freshness": "fresh"|"stale"}
        """
        if from_currency == to_currency:
            return {"rate": 1.0, "freshness": "fresh"}

        cache_key = f"{from_currency}/{to_currency}"
        cached = self._cache.get(cache_key)
        now = time.time()

        # Return cached if within TTL
        if cached and (now - cached[1]) < _CACHE_TTL_SECONDS:
            return {"rate": cached[0], "freshness": "fresh"}

        # Fetch fresh rate
        rate = await self._fetch_rate(from_currency, to_currency)
        if rate is not None:
            self._cache[cache_key] = (rate, now)
            return {"rate": rate, "freshness": "fresh"}

        # Fall back to stale cache
        if cached:
            freshness = "stale" if (now - cached[1]) > _STALE_THRESHOLD_SECONDS else "fresh"
            logger.warning(
                "currency_rate_fallback_to_cache",
                from_currency=from_currency,
                to_currency=to_currency,
                cache_age_hours=round((now - cached[1]) / 3600, 1),
            )
            return {"rate": cached[0], "freshness": freshness}

        # No cache, no API — use hardcoded fallback for critical pairs
        fallback = _FALLBACK_RATES.get(cache_key)
        if fallback:
            return {"rate": fallback, "freshness": "stale"}

        raise RuntimeError(f"Cannot get exchange rate for {from_currency}/{to_currency}")

    async def convert(self, amount: float, from_currency: str, to_currency: str) -> dict:
        """
        Convert an amount between currencies.

        Returns:
            {"converted": float, "rate": float, "freshness": str}
        """
        result = await self.get_rate(from_currency, to_currency)
        return {
            "converted": round(amount * result["rate"], 2),
            "rate": result["rate"],
            "freshness": result["freshness"],
        }

    async def _fetch_rate(self, from_currency: str, to_currency: str) -> float | None:
        """Fetch rate from Frankfurter API with retries."""
        url = f"{self._base_url}/latest?from={from_currency}&to={to_currency}"
        delay = 1.0

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    return data["rates"][to_currency]
            except Exception:
                logger.warning(
                    "currency_fetch_failed",
                    attempt=attempt + 1,
                    from_currency=from_currency,
                    to_currency=to_currency,
                    exc_info=True,
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
        return None


# Hardcoded fallback rates for critical pairs when API is completely down
_FALLBACK_RATES: dict[str, float] = {
    "USD/INR": 83.0,
    "INR/USD": 0.012,
    "EUR/INR": 90.0,
    "INR/EUR": 0.011,
    "GBP/INR": 105.0,
    "INR/GBP": 0.0095,
}
