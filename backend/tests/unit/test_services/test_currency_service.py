"""Tests for CurrencyService."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.currency_service import CurrencyService


class TestGetRate:
    """Tests for CurrencyService.get_rate()."""

    async def test_same_currency_returns_one(self) -> None:
        service = CurrencyService()
        result = await service.get_rate("USD", "USD")
        assert result == {"rate": 1.0, "freshness": "fresh"}

    async def test_same_currency_inr(self) -> None:
        service = CurrencyService()
        result = await service.get_rate("INR", "INR")
        assert result["rate"] == 1.0

    async def test_fresh_cache_hit(self) -> None:
        service = CurrencyService()
        service._cache["USD/INR"] = (83.5, time.time())

        result = await service.get_rate("USD", "INR")

        assert result["rate"] == 83.5
        assert result["freshness"] == "fresh"

    async def test_expired_cache_triggers_fetch(self) -> None:
        service = CurrencyService()
        old_time = time.time() - 5 * 3600  # 5 hours ago (beyond 4h TTL)
        service._cache["USD/INR"] = (83.0, old_time)

        service._fetch_rate = AsyncMock(return_value=84.0)

        result = await service.get_rate("USD", "INR")

        assert result["rate"] == 84.0
        assert result["freshness"] == "fresh"
        service._fetch_rate.assert_called_once_with("USD", "INR")

    async def test_api_failure_falls_back_to_stale_cache(self) -> None:
        service = CurrencyService()
        stale_time = time.time() - 25 * 3600  # 25 hours (beyond stale threshold)
        service._cache["USD/INR"] = (82.0, stale_time)

        service._fetch_rate = AsyncMock(return_value=None)

        result = await service.get_rate("USD", "INR")

        assert result["rate"] == 82.0
        assert result["freshness"] == "stale"

    async def test_api_failure_with_recent_cache_returns_fresh(self) -> None:
        service = CurrencyService()
        # Cache is 6 hours old — past TTL but within stale threshold
        recent_time = time.time() - 6 * 3600
        service._cache["USD/INR"] = (83.0, recent_time)

        service._fetch_rate = AsyncMock(return_value=None)

        result = await service.get_rate("USD", "INR")

        assert result["rate"] == 83.0
        assert result["freshness"] == "fresh"

    async def test_no_cache_no_api_uses_fallback(self) -> None:
        service = CurrencyService()
        service._fetch_rate = AsyncMock(return_value=None)

        result = await service.get_rate("USD", "INR")

        assert result["rate"] == 83.0
        assert result["freshness"] == "stale"

    async def test_no_cache_no_api_no_fallback_raises(self) -> None:
        service = CurrencyService()
        service._fetch_rate = AsyncMock(return_value=None)

        with pytest.raises(RuntimeError, match="Cannot get exchange rate"):
            await service.get_rate("USD", "JPY")

    async def test_successful_fetch_updates_cache(self) -> None:
        service = CurrencyService()
        service._fetch_rate = AsyncMock(return_value=84.5)

        await service.get_rate("EUR", "INR")

        assert "EUR/INR" in service._cache
        assert service._cache["EUR/INR"][0] == 84.5


class TestConvert:
    """Tests for CurrencyService.convert()."""

    async def test_convert_basic(self) -> None:
        service = CurrencyService()
        service.get_rate = AsyncMock(return_value={"rate": 83.0, "freshness": "fresh"})

        result = await service.convert(1000, "USD", "INR")

        assert result["converted"] == 83000.0
        assert result["rate"] == 83.0
        assert result["freshness"] == "fresh"

    async def test_convert_same_currency(self) -> None:
        service = CurrencyService()

        result = await service.convert(500, "INR", "INR")

        assert result["converted"] == 500.0
        assert result["rate"] == 1.0

    async def test_convert_rounds_to_two_decimals(self) -> None:
        service = CurrencyService()
        service.get_rate = AsyncMock(return_value={"rate": 83.123, "freshness": "fresh"})

        result = await service.convert(100, "USD", "INR")

        assert result["converted"] == 8312.3


class TestFetchRate:
    """Tests for CurrencyService._fetch_rate() with mocked HTTP."""

    @patch("src.services.currency_service.httpx.AsyncClient")
    async def test_successful_fetch(self, mock_client_cls) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"INR": 83.5}}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_cls.return_value = mock_client

        service = CurrencyService()
        rate = await service._fetch_rate("USD", "INR")

        assert rate == 83.5

    @patch("src.services.currency_service.httpx.AsyncClient")
    async def test_all_retries_fail_returns_none(self, mock_client_cls) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_cls.return_value = mock_client

        service = CurrencyService()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            rate = await service._fetch_rate("USD", "JPY")

        assert rate is None


class TestFallbackRates:
    """Tests for hardcoded fallback rates."""

    async def test_usd_to_inr_fallback(self) -> None:
        service = CurrencyService()
        service._fetch_rate = AsyncMock(return_value=None)

        result = await service.get_rate("USD", "INR")
        assert result["rate"] == 83.0

    async def test_inr_to_usd_fallback(self) -> None:
        service = CurrencyService()
        service._fetch_rate = AsyncMock(return_value=None)

        result = await service.get_rate("INR", "USD")
        assert result["rate"] == 0.012

    async def test_eur_to_inr_fallback(self) -> None:
        service = CurrencyService()
        service._fetch_rate = AsyncMock(return_value=None)

        result = await service.get_rate("EUR", "INR")
        assert result["rate"] == 90.0

    async def test_gbp_to_inr_fallback(self) -> None:
        service = CurrencyService()
        service._fetch_rate = AsyncMock(return_value=None)

        result = await service.get_rate("GBP", "INR")
        assert result["rate"] == 105.0
