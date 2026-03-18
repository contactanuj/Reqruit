"""Tests for UsageService admin analytics and tier management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from src.core.config import TierSettings
from src.core.exceptions import NotFoundError
from src.db.documents.usage_ledger import UsageTier
from src.services.usage_service import (
    UsageService,
)

USER_A = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
USER_B = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
ADMIN_ID = PydanticObjectId("cccccccccccccccccccccccc")


def _make_entry(tokens=0, cost=0.0, tier=UsageTier.FREE, breakdown_by_model=None):
    entry = MagicMock()
    entry.total_tokens = tokens
    entry.total_cost_usd = cost
    entry.tier = tier
    entry.breakdown_by_model = breakdown_by_model or {}
    entry.breakdown_by_feature = {}
    entry.period_start = None
    return entry


class TestGetAdminSummary:
    async def test_aggregates_all_users(self):
        repo = MagicMock()
        repo.get_all_weekly_entries = AsyncMock(
            return_value=[
                _make_entry(tokens=1000, cost=1.0, tier=UsageTier.FREE),
                _make_entry(tokens=2000, cost=3.0, tier=UsageTier.PRO),
            ]
        )
        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_admin_summary()

        assert result.total_cost_this_week == 4.0
        assert result.per_user_average_usd == 2.0
        assert result.user_count_by_tier["FREE"] == 1
        assert result.user_count_by_tier["PRO"] == 1

    async def test_empty_week(self):
        repo = MagicMock()
        repo.get_all_weekly_entries = AsyncMock(return_value=[])
        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_admin_summary()

        assert result.total_cost_this_week == 0.0
        assert result.per_user_average_usd == 0.0
        assert result.user_count_by_tier == {}
        assert result.model_routing_distribution == {}

    async def test_model_distribution_as_percentages(self):
        repo = MagicMock()
        repo.get_all_weekly_entries = AsyncMock(
            return_value=[
                _make_entry(
                    cost=1.0,
                    breakdown_by_model={"claude-sonnet": 0.7, "claude-haiku": 0.3},
                ),
                _make_entry(
                    cost=1.0,
                    breakdown_by_model={"claude-sonnet": 0.5, "claude-haiku": 0.5},
                ),
            ]
        )
        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_admin_summary()

        # total: sonnet=1.2, haiku=0.8, grand=2.0
        assert result.model_routing_distribution["claude-sonnet"] == 60.0
        assert result.model_routing_distribution["claude-haiku"] == 40.0

    async def test_summary_has_period_timestamps(self):
        repo = MagicMock()
        repo.get_all_weekly_entries = AsyncMock(return_value=[])
        service = UsageService(repo=repo, tier_settings=TierSettings())
        result = await service.get_admin_summary()

        assert result.period_start is not None
        assert result.period_end is not None


class TestGetUsageAnomalies:
    async def test_cost_spike_detected(self):
        """User with 4x rolling average cost is flagged."""
        repo = MagicMock()
        repo.get_all_active_user_ids_this_week = AsyncMock(return_value=[USER_A])
        current = _make_entry(tokens=5000, cost=4.0)
        repo.get_current_usage = AsyncMock(return_value=current)
        # History: avg cost = 1.0
        history = [_make_entry(cost=1.0), _make_entry(cost=1.0)]
        # Set different period_start so they're not filtered out
        for h in history:
            h.period_start = "old"
        repo.get_user_weekly_history = AsyncMock(return_value=history)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        anomalies = await service.get_usage_anomalies()

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "cost_spike"
        assert anomalies[0].spike_multiplier == 4.0

    async def test_normal_usage_not_flagged(self):
        """User with 1.5x average is NOT flagged."""
        repo = MagicMock()
        repo.get_all_active_user_ids_this_week = AsyncMock(return_value=[USER_A])
        current = _make_entry(tokens=1500, cost=1.5)
        repo.get_current_usage = AsyncMock(return_value=current)
        history = [_make_entry(cost=1.0), _make_entry(cost=1.0)]
        for h in history:
            h.period_start = "old"
        repo.get_user_weekly_history = AsyncMock(return_value=history)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        anomalies = await service.get_usage_anomalies()

        assert len(anomalies) == 0

    async def test_frequency_spike_detected(self):
        """User with 3x rolling average tokens is flagged as frequency_spike."""
        repo = MagicMock()
        repo.get_all_active_user_ids_this_week = AsyncMock(return_value=[USER_A])
        # Cost not spiked (2x, below 3x threshold), but tokens are 3x
        current = _make_entry(tokens=6000, cost=2.0)
        repo.get_current_usage = AsyncMock(return_value=current)
        history = [_make_entry(tokens=2000, cost=1.0), _make_entry(tokens=2000, cost=1.0)]
        for h in history:
            h.period_start = "old"
        repo.get_user_weekly_history = AsyncMock(return_value=history)

        service = UsageService(repo=repo, tier_settings=TierSettings())
        anomalies = await service.get_usage_anomalies()

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "frequency_spike"
        assert anomalies[0].spike_multiplier == 3.0

    async def test_no_history_skipped(self):
        """Users with no history are skipped (no baseline)."""
        repo = MagicMock()
        repo.get_all_active_user_ids_this_week = AsyncMock(return_value=[USER_A])
        current = _make_entry(tokens=5000, cost=4.0)
        repo.get_current_usage = AsyncMock(return_value=current)
        repo.get_user_weekly_history = AsyncMock(return_value=[])

        service = UsageService(repo=repo, tier_settings=TierSettings())
        anomalies = await service.get_usage_anomalies()

        assert len(anomalies) == 0

    async def test_no_active_users(self):
        """No active users this week returns empty list."""
        repo = MagicMock()
        repo.get_all_active_user_ids_this_week = AsyncMock(return_value=[])

        service = UsageService(repo=repo, tier_settings=TierSettings())
        anomalies = await service.get_usage_anomalies()

        assert anomalies == []


class TestUpdateUserTier:
    async def test_updates_tier_successfully(self):
        mock_user = MagicMock()
        mock_user.id = USER_A
        mock_user.is_admin = False
        mock_user.usage_tier = "free"
        mock_user.save = AsyncMock()

        with patch("src.services.usage_service.User") as mock_user_cls:
            mock_user_cls.get = AsyncMock(return_value=mock_user)
            repo = MagicMock()
            service = UsageService(repo=repo, tier_settings=TierSettings())
            result = await service.update_user_tier(USER_A, UsageTier.PRO, ADMIN_ID)

        assert result.previous_tier == "free"
        assert result.new_tier == "pro"
        assert result.effective_immediately is True
        mock_user.save.assert_awaited_once()

    async def test_user_not_found_raises(self):
        with patch("src.services.usage_service.User") as mock_user_cls:
            mock_user_cls.get = AsyncMock(return_value=None)
            repo = MagicMock()
            service = UsageService(repo=repo, tier_settings=TierSettings())

            with pytest.raises(NotFoundError):
                await service.update_user_tier(USER_A, UsageTier.PRO, ADMIN_ID)

    async def test_upgrade_to_admin(self):
        mock_user = MagicMock()
        mock_user.id = USER_A
        mock_user.is_admin = False
        mock_user.usage_tier = "free"
        mock_user.save = AsyncMock()

        with patch("src.services.usage_service.User") as mock_user_cls:
            mock_user_cls.get = AsyncMock(return_value=mock_user)
            repo = MagicMock()
            service = UsageService(repo=repo, tier_settings=TierSettings())
            result = await service.update_user_tier(USER_A, UsageTier.ADMIN, ADMIN_ID)

        assert result.new_tier == "admin"
        assert mock_user.is_admin is True

    async def test_downgrade_from_admin(self):
        mock_user = MagicMock()
        mock_user.id = USER_A
        mock_user.is_admin = True
        mock_user.usage_tier = "admin"
        mock_user.save = AsyncMock()

        with patch("src.services.usage_service.User") as mock_user_cls:
            mock_user_cls.get = AsyncMock(return_value=mock_user)
            repo = MagicMock()
            service = UsageService(repo=repo, tier_settings=TierSettings())
            result = await service.update_user_tier(USER_A, UsageTier.FREE, ADMIN_ID)

        assert result.previous_tier == "admin"
        assert result.new_tier == "free"
        assert mock_user.is_admin is False


class TestHelperMethods:
    def test_compute_model_distribution(self):
        entries = [
            _make_entry(breakdown_by_model={"a": 3.0, "b": 1.0}),
            _make_entry(breakdown_by_model={"a": 2.0, "b": 4.0}),
        ]
        result = UsageService._compute_model_distribution(entries)
        # a=5, b=5, total=10 -> 50% each
        assert result["a"] == 50.0
        assert result["b"] == 50.0

    def test_compute_model_distribution_empty(self):
        result = UsageService._compute_model_distribution([])
        assert result == {}

    def test_count_users_by_tier(self):
        entries = [
            _make_entry(tier=UsageTier.FREE),
            _make_entry(tier=UsageTier.FREE),
            _make_entry(tier=UsageTier.PRO),
        ]
        result = UsageService._count_users_by_tier(entries)
        assert result["FREE"] == 2
        assert result["PRO"] == 1

    def test_compute_rolling_average(self):
        entries = [
            _make_entry(tokens=1000, cost=2.0),
            _make_entry(tokens=3000, cost=4.0),
        ]
        avg_cost, avg_tokens = UsageService._compute_rolling_average(entries)
        assert avg_cost == 3.0
        assert avg_tokens == 2000.0

    def test_compute_rolling_average_empty(self):
        avg_cost, avg_tokens = UsageService._compute_rolling_average([])
        assert avg_cost == 0.0
        assert avg_tokens == 0.0
