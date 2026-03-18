"""Tests for UsageService."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.core.config import TierSettings
from src.db.documents.usage_ledger import UsagePeriod, UsageTier
from src.services.usage_service import UsageService

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _make_ledger_entry(
    tokens=500,
    cost=0.005,
    feature_breakdown=None,
    model_breakdown=None,
    tier=UsageTier.FREE,
):
    entry = MagicMock()
    entry.total_tokens = tokens
    entry.total_cost_usd = cost
    entry.breakdown_by_feature = feature_breakdown or {"cover_letter": cost}
    entry.breakdown_by_model = model_breakdown or {"claude-sonnet-4-5-20250929": cost}
    entry.tier = tier
    return entry


class TestGetUsageSummary:
    async def test_fetches_all_periods(self):
        """get_usage_summary queries daily, weekly, and monthly entries."""
        repo = MagicMock()
        daily = _make_ledger_entry(tokens=100, cost=0.001)
        weekly = _make_ledger_entry(tokens=500, cost=0.005)
        monthly = _make_ledger_entry(tokens=2000, cost=0.02)

        async def mock_get_usage(user_id, period):
            return {
                UsagePeriod.DAILY: daily,
                UsagePeriod.WEEKLY: weekly,
                UsagePeriod.MONTHLY: monthly,
            }[period]

        repo.get_current_usage = AsyncMock(side_effect=mock_get_usage)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_usage_summary(USER_ID, UsageTier.FREE)

        assert result.daily.total_tokens == 100
        assert result.weekly.total_tokens == 500
        assert result.monthly.total_tokens == 2000
        assert result.tier == "free"
        assert repo.get_current_usage.await_count == 3

    async def test_resolves_tier_from_settings_not_ledger(self):
        """Tier limits come from TierSettings, not from stale ledger entries."""
        repo = MagicMock()
        # The ledger entry has stale tier info
        stale_entry = _make_ledger_entry(tokens=100, cost=0.001)
        stale_entry.tier = UsageTier.FREE
        stale_entry.tier_limit_usd = 0.50  # stale value
        repo.get_current_usage = AsyncMock(return_value=stale_entry)

        settings = TierSettings(pro_weekly_cost_usd=20.0, pro_weekly_tokens=10_000_000)
        service = UsageService(repo=repo, tier_settings=settings)
        result = await service.get_usage_summary(USER_ID, UsageTier.PRO)

        # Should use TierSettings values, not stale ledger values
        assert result.tier == "pro"
        assert result.tier_limit_usd == 20.0
        assert result.tier_limit_tokens == 10_000_000

    async def test_computes_usage_percentage(self):
        """usage_percentage = (weekly_cost / tier_limit_usd) * 100."""
        repo = MagicMock()
        weekly = _make_ledger_entry(tokens=500, cost=0.75)
        repo.get_current_usage = AsyncMock(return_value=weekly)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_usage_summary(USER_ID, UsageTier.FREE)

        # 0.75 / 1.50 * 100 = 50.0
        assert result.usage_percentage == 50.0

    async def test_handles_no_entries(self):
        """Returns zeroed totals when no ledger entries exist."""
        repo = MagicMock()
        repo.get_current_usage = AsyncMock(return_value=None)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_usage_summary(USER_ID, UsageTier.FREE)

        assert result.daily.total_tokens == 0
        assert result.daily.total_cost_usd == 0.0
        assert result.weekly.total_tokens == 0
        assert result.monthly.total_tokens == 0
        assert result.usage_percentage == 0.0
        assert result.tier == "free"
        assert result.tier_limit_usd == 1.50

    async def test_admin_tier_limits(self):
        """Admin tier gets unlimited limits."""
        repo = MagicMock()
        repo.get_current_usage = AsyncMock(return_value=None)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_usage_summary(USER_ID, UsageTier.ADMIN)

        assert result.tier == "admin"
        assert result.tier_limit_usd == 999999.0
        assert result.tier_limit_tokens == 999_999_999


class TestGetUsageBreakdown:
    async def test_returns_weekly_breakdown(self):
        """get_usage_breakdown returns weekly feature and model breakdowns."""
        repo = MagicMock()
        weekly = _make_ledger_entry(
            feature_breakdown={"cover_letter": 0.003, "interview_prep": 0.002},
            model_breakdown={"claude-sonnet-4-5-20250929": 0.005},
        )
        repo.get_current_usage = AsyncMock(return_value=weekly)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_usage_breakdown(USER_ID)

        assert result.breakdown_by_feature["cover_letter"] == 0.003
        assert result.breakdown_by_feature["interview_prep"] == 0.002
        assert result.breakdown_by_model["claude-sonnet-4-5-20250929"] == 0.005
        assert result.period_start is not None
        assert result.period_end is not None

    async def test_handles_no_weekly_entry(self):
        """Returns empty dicts when no weekly entry exists."""
        repo = MagicMock()
        repo.get_current_usage = AsyncMock(return_value=None)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_usage_breakdown(USER_ID)

        assert result.breakdown_by_feature == {}
        assert result.breakdown_by_model == {}
        assert result.period_start is not None
        assert result.period_end is not None
