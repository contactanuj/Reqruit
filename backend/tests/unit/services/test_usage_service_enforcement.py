"""Tests for UsageService tier enforcement."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from src.core.config import TierSettings
from src.core.exceptions import DailyCapReachedError, TierLimitExceededError
from src.db.documents.usage_ledger import UsagePeriod, UsageTier
from src.services.usage_service import UsageService

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _make_entry(tokens=0, cost=0.0):
    entry = MagicMock()
    entry.total_tokens = tokens
    entry.total_cost_usd = cost
    return entry


class TestEnforceTierLimitWeekly:
    async def test_free_user_under_limit_allowed(self):
        repo = MagicMock()
        repo.get_current_usage = AsyncMock(
            return_value=_make_entry(tokens=100, cost=0.01)
        )
        service = UsageService(repo=repo, tier_settings=TierSettings())

        # Should not raise
        await service.enforce_tier_limit(USER_ID, UsageTier.FREE)

    async def test_free_user_over_cost_limit_raises(self):
        repo = MagicMock()
        weekly = _make_entry(tokens=100, cost=2.0)  # over $1.50
        daily = _make_entry(tokens=10, cost=0.01)

        async def mock_get(user_id, period):
            return weekly if period == UsagePeriod.WEEKLY else daily

        repo.get_current_usage = AsyncMock(side_effect=mock_get)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        with pytest.raises(TierLimitExceededError) as exc_info:
            await service.enforce_tier_limit(USER_ID, UsageTier.FREE)

        assert exc_info.value.tier_name == "FREE"
        assert exc_info.value.current_usage_usd == 2.0
        assert exc_info.value.limit_usd == 1.50
        assert exc_info.value.error_code == "TIER_LIMIT_EXCEEDED"
        assert exc_info.value.status_code == 429

    async def test_free_user_over_token_limit_raises(self):
        repo = MagicMock()
        weekly = _make_entry(tokens=600_000, cost=0.50)  # over 500K tokens
        repo.get_current_usage = AsyncMock(return_value=weekly)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        with pytest.raises(TierLimitExceededError) as exc_info:
            await service.enforce_tier_limit(USER_ID, UsageTier.FREE)

        assert exc_info.value.current_tokens == 600_000
        assert exc_info.value.limit_tokens == 500_000

    async def test_pro_user_under_limit_allowed(self):
        repo = MagicMock()
        weekly = _make_entry(tokens=1000, cost=5.0)
        daily = _make_entry(tokens=200, cost=1.0)  # under daily cap ($15/5 = $3)

        async def mock_get(user_id, period):
            return weekly if period == UsagePeriod.WEEKLY else daily

        repo.get_current_usage = AsyncMock(side_effect=mock_get)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        await service.enforce_tier_limit(USER_ID, UsageTier.PRO)

    async def test_pro_user_over_limit_raises(self):
        repo = MagicMock()
        weekly = _make_entry(tokens=1000, cost=20.0)  # over $15
        daily = _make_entry(tokens=200, cost=1.0)

        async def mock_get(user_id, period):
            return weekly if period == UsagePeriod.WEEKLY else daily

        repo.get_current_usage = AsyncMock(side_effect=mock_get)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        with pytest.raises(TierLimitExceededError) as exc_info:
            await service.enforce_tier_limit(USER_ID, UsageTier.PRO)

        assert exc_info.value.tier_name == "PRO"
        assert exc_info.value.limit_usd == 15.0

    async def test_tier_limit_error_has_upgrade_path(self):
        repo = MagicMock()
        weekly = _make_entry(tokens=100, cost=2.0)
        repo.get_current_usage = AsyncMock(return_value=weekly)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        with pytest.raises(TierLimitExceededError) as exc_info:
            await service.enforce_tier_limit(USER_ID, UsageTier.FREE)

        assert "Pro" in exc_info.value.upgrade_path


class TestEnforceDailyCap:
    async def test_daily_cap_is_weekly_divided_by_5(self):
        """Daily cap = weekly_limit / 5."""
        repo = MagicMock()
        # Weekly under limit, daily over cap ($1.50/5 = $0.30)
        weekly = _make_entry(tokens=100, cost=0.10)
        daily = _make_entry(tokens=50, cost=0.35)

        async def mock_get(user_id, period):
            return weekly if period == UsagePeriod.WEEKLY else daily

        repo.get_current_usage = AsyncMock(side_effect=mock_get)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        with pytest.raises(DailyCapReachedError) as exc_info:
            await service.enforce_tier_limit(USER_ID, UsageTier.FREE)

        assert exc_info.value.daily_cost_usd == 0.35
        assert exc_info.value.daily_cap_usd == pytest.approx(0.30)
        assert exc_info.value.error_code == "DAILY_CAP_REACHED"
        assert exc_info.value.status_code == 429

    async def test_daily_cap_includes_resets_at(self):
        repo = MagicMock()
        weekly = _make_entry(tokens=100, cost=0.10)
        daily = _make_entry(tokens=50, cost=0.35)

        async def mock_get(user_id, period):
            return weekly if period == UsagePeriod.WEEKLY else daily

        repo.get_current_usage = AsyncMock(side_effect=mock_get)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        with pytest.raises(DailyCapReachedError) as exc_info:
            await service.enforce_tier_limit(USER_ID, UsageTier.FREE)

        resets_at = exc_info.value.resets_at
        assert resets_at.hour == 0
        assert resets_at.minute == 0
        assert resets_at > datetime.now(UTC)

    async def test_daily_under_cap_allowed(self):
        repo = MagicMock()
        repo.get_current_usage = AsyncMock(
            return_value=_make_entry(tokens=10, cost=0.01)
        )
        service = UsageService(repo=repo, tier_settings=TierSettings())

        await service.enforce_tier_limit(USER_ID, UsageTier.FREE)

    async def test_checks_daily_even_if_weekly_ok(self):
        """Daily cap is checked even when weekly limit is not exceeded."""
        repo = MagicMock()
        weekly = _make_entry(tokens=100, cost=0.10)  # well under weekly
        daily = _make_entry(tokens=50, cost=0.50)  # over daily cap

        async def mock_get(user_id, period):
            return weekly if period == UsagePeriod.WEEKLY else daily

        repo.get_current_usage = AsyncMock(side_effect=mock_get)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        with pytest.raises(DailyCapReachedError):
            await service.enforce_tier_limit(USER_ID, UsageTier.FREE)


class TestAdminEnforcement:
    async def test_admin_always_allowed(self):
        repo = MagicMock()
        repo.get_current_usage = AsyncMock()
        service = UsageService(repo=repo, tier_settings=TierSettings())

        await service.enforce_tier_limit(USER_ID, UsageTier.ADMIN)

        # No database query for admin
        repo.get_current_usage.assert_not_awaited()


class TestFailOpen:
    async def test_db_error_allows_through(self):
        """Database read failure results in fail-open (request allowed)."""
        repo = MagicMock()
        repo.get_current_usage = AsyncMock(
            side_effect=RuntimeError("DB unavailable")
        )
        service = UsageService(repo=repo, tier_settings=TierSettings())

        # Should not raise — fail-open
        await service.enforce_tier_limit(USER_ID, UsageTier.FREE)


class TestNoUsageEntries:
    async def test_no_entries_allowed(self):
        """User with no usage entries is allowed through."""
        repo = MagicMock()
        repo.get_current_usage = AsyncMock(return_value=None)
        service = UsageService(repo=repo, tier_settings=TierSettings())

        await service.enforce_tier_limit(USER_ID, UsageTier.FREE)
