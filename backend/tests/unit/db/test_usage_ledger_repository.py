"""Tests for UsageLedgerRepository and helpers."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId

from src.core.config import TierSettings
from src.db.documents.usage_ledger import UsageLedger, UsagePeriod, UsageTier
from src.repositories.usage_ledger_repository import (
    UsageLedgerRepository,
    _compute_period_start,
    _resolve_tier_limits,
)

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


# ── Enum tests ──────────────────────────────────────────────────────────


class TestUsagePeriodEnum:
    def test_daily_value(self):
        assert UsagePeriod.DAILY == "daily"

    def test_weekly_value(self):
        assert UsagePeriod.WEEKLY == "weekly"

    def test_monthly_value(self):
        assert UsagePeriod.MONTHLY == "monthly"


class TestUsageTierEnum:
    def test_free_value(self):
        assert UsageTier.FREE == "free"

    def test_pro_value(self):
        assert UsageTier.PRO == "pro"

    def test_admin_value(self):
        assert UsageTier.ADMIN == "admin"


# ── Model tests ─────────────────────────────────────────────────────────


class TestUsageLedgerModel:
    def test_defaults(self):
        ledger = UsageLedger(
            user_id=USER_ID,
            period=UsagePeriod.DAILY,
            period_start=datetime(2026, 3, 16, tzinfo=UTC),
        )
        assert ledger.total_tokens == 0
        assert ledger.total_cost_usd == 0.0
        assert ledger.breakdown_by_feature == {}
        assert ledger.breakdown_by_model == {}
        assert ledger.tier == UsageTier.FREE
        assert ledger.tier_limit_usd == 1.50
        assert ledger.tier_limit_tokens == 500_000

    def test_all_fields(self):
        ledger = UsageLedger(
            user_id=USER_ID,
            period=UsagePeriod.WEEKLY,
            period_start=datetime(2026, 3, 16, tzinfo=UTC),
            total_tokens=1000,
            total_cost_usd=0.05,
            breakdown_by_feature={"cover_letter": 0.03, "interview_prep": 0.02},
            breakdown_by_model={"claude-sonnet-4-5-20250929": 0.05},
            tier=UsageTier.PRO,
            tier_limit_usd=15.0,
            tier_limit_tokens=5_000_000,
        )
        assert ledger.total_tokens == 1000
        assert ledger.breakdown_by_feature["cover_letter"] == 0.03
        assert ledger.tier == UsageTier.PRO

    def test_collection_name(self):
        assert UsageLedger.Settings.name == "usage_ledgers"


# ── Helper function tests ───────────────────────────────────────────────


class TestComputePeriodStart:
    def test_daily_returns_midnight(self):
        result = _compute_period_start(UsagePeriod.DAILY)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_weekly_returns_monday(self):
        result = _compute_period_start(UsagePeriod.WEEKLY)
        assert result.weekday() == 0  # Monday
        assert result.hour == 0
        assert result.minute == 0

    def test_monthly_returns_first_of_month(self):
        result = _compute_period_start(UsagePeriod.MONTHLY)
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0


class TestResolveTierLimits:
    def test_free_tier(self):
        settings = TierSettings()
        usd, tokens = _resolve_tier_limits(UsageTier.FREE, settings)
        assert usd == 1.50
        assert tokens == 500_000

    def test_pro_tier(self):
        settings = TierSettings()
        usd, tokens = _resolve_tier_limits(UsageTier.PRO, settings)
        assert usd == 15.0
        assert tokens == 5_000_000

    def test_admin_tier(self):
        settings = TierSettings()
        usd, tokens = _resolve_tier_limits(UsageTier.ADMIN, settings)
        assert usd == 999999.0
        assert tokens == 999_999_999


# ── TierSettings tests ──────────────────────────────────────────────────


class TestTierSettings:
    def test_defaults(self):
        settings = TierSettings()
        assert settings.free_weekly_cost_usd == 1.50
        assert settings.free_weekly_tokens == 500_000
        assert settings.pro_weekly_cost_usd == 15.0
        assert settings.pro_weekly_tokens == 5_000_000
        assert settings.admin_unlimited is True


# ── Repository tests ────────────────────────────────────────────────────


class TestIncrementUsage:
    async def test_creates_entry_via_upsert(self):
        """increment_usage calls find_one_and_update with upsert=True."""
        repo = UsageLedgerRepository()
        tier_settings = TierSettings()

        mock_result = {
            "_id": PydanticObjectId("cccccccccccccccccccccccc"),
            "user_id": USER_ID,
            "period": "daily",
            "period_start": datetime(2026, 3, 16, tzinfo=UTC),
            "total_tokens": 150,
            "total_cost_usd": 0.001,
            "breakdown_by_feature": {"cover_letter": 0.001},
            "breakdown_by_model": {"claude-sonnet-4-5-20250929": 0.001},
            "tier": "free",
            "tier_limit_usd": 1.50,
            "tier_limit_tokens": 500_000,
            "created_at": datetime(2026, 3, 16, tzinfo=UTC),
            "updated_at": datetime(2026, 3, 16, tzinfo=UTC),
        }

        mock_collection = MagicMock()
        mock_collection.find_one_and_update = AsyncMock(return_value=mock_result)

        with patch.object(
            UsageLedger, "get_motor_collection", create=True, return_value=mock_collection
        ):
            result = await repo.increment_usage(
                user_id=USER_ID,
                tokens=150,
                cost_usd=0.001,
                feature="cover_letter",
                model_name="claude-sonnet-4-5-20250929",
                tier=UsageTier.FREE,
                tier_settings=tier_settings,
            )

        mock_collection.find_one_and_update.assert_awaited_once()
        call_args = mock_collection.find_one_and_update.call_args
        # Check the $inc operator
        update = call_args[0][1]
        assert update["$inc"]["total_tokens"] == 150
        assert update["$inc"]["total_cost_usd"] == 0.001
        assert update["$inc"]["breakdown_by_feature.cover_letter"] == 0.001
        assert update["$inc"]["breakdown_by_model.claude-sonnet-4-5-20250929"] == 0.001
        # Check upsert=True
        assert call_args[1]["upsert"] is True
        assert result.total_tokens == 150

    async def test_sets_tier_on_insert(self):
        """$setOnInsert includes tier and limits."""
        repo = UsageLedgerRepository()
        tier_settings = TierSettings()

        mock_result = {
            "_id": PydanticObjectId("cccccccccccccccccccccccc"),
            "user_id": USER_ID,
            "period": "daily",
            "period_start": datetime(2026, 3, 16, tzinfo=UTC),
            "total_tokens": 100,
            "total_cost_usd": 0.001,
            "breakdown_by_feature": {},
            "breakdown_by_model": {},
            "tier": "pro",
            "tier_limit_usd": 15.0,
            "tier_limit_tokens": 5_000_000,
            "created_at": datetime(2026, 3, 16, tzinfo=UTC),
            "updated_at": datetime(2026, 3, 16, tzinfo=UTC),
        }

        mock_collection = MagicMock()
        mock_collection.find_one_and_update = AsyncMock(return_value=mock_result)

        with patch.object(
            UsageLedger, "get_motor_collection", create=True, return_value=mock_collection
        ):
            await repo.increment_usage(
                user_id=USER_ID,
                tokens=100,
                cost_usd=0.001,
                feature="interview_prep",
                model_name="gpt-4o-mini",
                tier=UsageTier.PRO,
                tier_settings=tier_settings,
            )

        call_args = mock_collection.find_one_and_update.call_args
        set_on_insert = call_args[0][1]["$setOnInsert"]
        assert set_on_insert["tier"] == "pro"
        assert set_on_insert["tier_limit_usd"] == 15.0
        assert set_on_insert["tier_limit_tokens"] == 5_000_000


class TestGetCurrentUsage:
    async def test_returns_entry(self):
        repo = UsageLedgerRepository()
        mock_entry = MagicMock(spec=UsageLedger)
        repo.find_one = AsyncMock(return_value=mock_entry)

        result = await repo.get_current_usage(USER_ID, UsagePeriod.DAILY)
        assert result is mock_entry

    async def test_returns_none_when_empty(self):
        repo = UsageLedgerRepository()
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.get_current_usage(USER_ID, UsagePeriod.WEEKLY)
        assert result is None


class TestGetDailyEntriesForPeriod:
    async def test_returns_entries_in_range(self):
        repo = UsageLedgerRepository()
        mock_entries = [MagicMock(spec=UsageLedger), MagicMock(spec=UsageLedger)]
        repo.find_many = AsyncMock(return_value=mock_entries)

        start = datetime(2026, 3, 10, tzinfo=UTC)
        end = datetime(2026, 3, 16, tzinfo=UTC)
        result = await repo.get_daily_entries_for_period(USER_ID, start, end)

        assert len(result) == 2
        repo.find_many.assert_awaited_once()
        call_kwargs = repo.find_many.call_args[1]
        assert call_kwargs["filters"]["user_id"] == USER_ID
        assert call_kwargs["filters"]["period"] == "daily"


class TestUpsertRollup:
    async def test_upserts_weekly_rollup(self):
        repo = UsageLedgerRepository()

        mock_result = {
            "_id": PydanticObjectId("cccccccccccccccccccccccc"),
            "user_id": USER_ID,
            "period": "weekly",
            "period_start": datetime(2026, 3, 16, tzinfo=UTC),
            "total_tokens": 5000,
            "total_cost_usd": 0.5,
            "breakdown_by_feature": {"cover_letter": 0.3, "interview_prep": 0.2},
            "breakdown_by_model": {"claude-sonnet-4-5-20250929": 0.5},
            "tier": "free",
            "tier_limit_usd": 1.50,
            "tier_limit_tokens": 500_000,
            "created_at": datetime(2026, 3, 16, tzinfo=UTC),
            "updated_at": datetime(2026, 3, 16, tzinfo=UTC),
        }

        mock_collection = MagicMock()
        mock_collection.find_one_and_update = AsyncMock(return_value=mock_result)

        with patch.object(
            UsageLedger, "get_motor_collection", create=True, return_value=mock_collection
        ):
            result = await repo.upsert_rollup(
                user_id=USER_ID,
                period=UsagePeriod.WEEKLY,
                period_start=datetime(2026, 3, 16, tzinfo=UTC),
                total_tokens=5000,
                total_cost_usd=0.5,
                breakdown_by_feature={"cover_letter": 0.3, "interview_prep": 0.2},
                breakdown_by_model={"claude-sonnet-4-5-20250929": 0.5},
                tier=UsageTier.FREE,
                tier_limit_usd=1.50,
                tier_limit_tokens=500_000,
            )

        assert result.total_tokens == 5000
        call_args = mock_collection.find_one_and_update.call_args
        update = call_args[0][1]
        assert update["$set"]["total_tokens"] == 5000
        assert update["$set"]["total_cost_usd"] == 0.5


class TestGetDistinctUserIds:
    async def test_returns_user_ids(self):
        repo = UsageLedgerRepository()
        user_ids = [USER_ID, PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")]

        mock_collection = MagicMock()
        mock_collection.distinct = AsyncMock(return_value=user_ids)

        with patch.object(
            UsageLedger, "get_motor_collection", create=True, return_value=mock_collection
        ):
            start = datetime(2026, 3, 10, tzinfo=UTC)
            end = datetime(2026, 3, 16, tzinfo=UTC)
            result = await repo.get_distinct_user_ids_in_range(start, end)

        assert len(result) == 2
        mock_collection.distinct.assert_awaited_once()
