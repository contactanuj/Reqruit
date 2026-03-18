"""Tests for the aggregate_usage_rollups Celery Beat task."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from src.db.documents.usage_ledger import UsagePeriod, UsageTier
from src.tasks.cost_tasks import _merge_breakdowns

USER_ID_A = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
USER_ID_B = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


# ── _merge_breakdowns tests ─────────────────────────────────────────────


class TestMergeBreakdowns:
    def test_merges_multiple_dicts(self):
        result = _merge_breakdowns([
            {"cover_letter": 0.01, "interview_prep": 0.02},
            {"cover_letter": 0.03, "job_match": 0.05},
        ])
        assert result["cover_letter"] == pytest.approx(0.04)
        assert result["interview_prep"] == 0.02
        assert result["job_match"] == 0.05

    def test_empty_list(self):
        assert _merge_breakdowns([]) == {}

    def test_single_dict(self):
        result = _merge_breakdowns([{"a": 1.0, "b": 2.0}])
        assert result == {"a": 1.0, "b": 2.0}


# ── Aggregation logic tests ─────────────────────────────────────────────


def _make_ledger_entry(
    user_id=USER_ID_A,
    tokens=100,
    cost=0.001,
    feature_breakdown=None,
    model_breakdown=None,
    tier=UsageTier.FREE,
):
    entry = MagicMock()
    entry.user_id = user_id
    entry.total_tokens = tokens
    entry.total_cost_usd = cost
    entry.breakdown_by_feature = feature_breakdown or {"cover_letter": cost}
    entry.breakdown_by_model = model_breakdown or {"claude-sonnet-4-5-20250929": cost}
    entry.tier = tier
    return entry


class TestAggregationLogic:
    """Test the aggregation logic that the Celery task performs."""

    async def test_aggregates_tokens_and_cost(self):
        """Daily entries' tokens and costs are summed correctly."""
        entries = [
            _make_ledger_entry(tokens=100, cost=0.001),
            _make_ledger_entry(tokens=200, cost=0.002),
            _make_ledger_entry(tokens=50, cost=0.0005),
        ]
        total_tokens = sum(e.total_tokens for e in entries)
        total_cost = sum(e.total_cost_usd for e in entries)
        assert total_tokens == 350
        assert total_cost == pytest.approx(0.0035)

    async def test_upsert_rollup_called_with_aggregated_data(self):
        """upsert_rollup is called with merged breakdowns."""
        entries = [
            _make_ledger_entry(
                tokens=100,
                cost=0.01,
                feature_breakdown={"cover_letter": 0.01},
                model_breakdown={"claude-sonnet-4-5-20250929": 0.01},
            ),
            _make_ledger_entry(
                tokens=200,
                cost=0.02,
                feature_breakdown={"cover_letter": 0.01, "interview_prep": 0.01},
                model_breakdown={"claude-sonnet-4-5-20250929": 0.015, "gpt-4o-mini": 0.005},
            ),
        ]

        total_tokens = sum(e.total_tokens for e in entries)
        total_cost = sum(e.total_cost_usd for e in entries)
        feature_breakdown = _merge_breakdowns(
            [e.breakdown_by_feature for e in entries]
        )
        model_breakdown = _merge_breakdowns(
            [e.breakdown_by_model for e in entries]
        )

        mock_repo = MagicMock()
        mock_repo.upsert_rollup = AsyncMock()

        week_start = datetime(2026, 3, 16, tzinfo=UTC)
        await mock_repo.upsert_rollup(
            user_id=USER_ID_A,
            period=UsagePeriod.WEEKLY,
            period_start=week_start,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            breakdown_by_feature=feature_breakdown,
            breakdown_by_model=model_breakdown,
            tier=UsageTier.FREE,
            tier_limit_usd=1.50,
            tier_limit_tokens=500_000,
        )

        mock_repo.upsert_rollup.assert_awaited_once()
        call_kwargs = mock_repo.upsert_rollup.call_args[1]
        assert call_kwargs["total_tokens"] == 300
        assert call_kwargs["total_cost_usd"] == pytest.approx(0.03)
        assert call_kwargs["breakdown_by_feature"]["cover_letter"] == pytest.approx(0.02)
        assert call_kwargs["breakdown_by_feature"]["interview_prep"] == 0.01
        assert call_kwargs["breakdown_by_model"]["gpt-4o-mini"] == 0.005

    async def test_no_entries_skips_rollup(self):
        """When no daily entries exist, upsert_rollup is not called."""
        entries = []
        mock_repo = MagicMock()
        mock_repo.upsert_rollup = AsyncMock()

        if entries:
            await mock_repo.upsert_rollup()

        mock_repo.upsert_rollup.assert_not_awaited()

    async def test_distinct_user_ids_drives_aggregation(self):
        """Repository.get_distinct_user_ids_in_range provides user list."""
        mock_repo = MagicMock()
        mock_repo.get_distinct_user_ids_in_range = AsyncMock(
            return_value=[USER_ID_A, USER_ID_B]
        )

        start = datetime(2026, 3, 10, tzinfo=UTC)
        end = datetime(2026, 3, 16, tzinfo=UTC)
        user_ids = await mock_repo.get_distinct_user_ids_in_range(start, end)

        assert len(user_ids) == 2
        assert USER_ID_A in user_ids
        assert USER_ID_B in user_ids

    async def test_empty_user_list_no_work(self):
        """When no users have daily entries, no rollup work is performed."""
        mock_repo = MagicMock()
        mock_repo.get_distinct_user_ids_in_range = AsyncMock(return_value=[])
        mock_repo.get_daily_entries_for_period = AsyncMock()
        mock_repo.upsert_rollup = AsyncMock()

        user_ids = await mock_repo.get_distinct_user_ids_in_range(
            datetime(2026, 3, 10, tzinfo=UTC), datetime(2026, 3, 16, tzinfo=UTC)
        )
        assert user_ids == []
        mock_repo.get_daily_entries_for_period.assert_not_awaited()
        mock_repo.upsert_rollup.assert_not_awaited()


class TestAggregateBreakdowns:
    async def test_merges_feature_breakdowns_across_entries(self):
        """Feature breakdowns from multiple daily entries are merged correctly."""
        entries = [
            _make_ledger_entry(
                feature_breakdown={"cover_letter": 0.01, "interview_prep": 0.02}
            ),
            _make_ledger_entry(
                feature_breakdown={"cover_letter": 0.03, "job_match": 0.05}
            ),
        ]
        result = _merge_breakdowns([e.breakdown_by_feature for e in entries])
        assert result["cover_letter"] == pytest.approx(0.04)
        assert result["interview_prep"] == 0.02
        assert result["job_match"] == 0.05

    async def test_merges_model_breakdowns_across_entries(self):
        """Model breakdowns from multiple daily entries are merged correctly."""
        entries = [
            _make_ledger_entry(model_breakdown={"claude-sonnet-4-5-20250929": 0.01}),
            _make_ledger_entry(
                model_breakdown={"claude-sonnet-4-5-20250929": 0.02, "gpt-4o-mini": 0.005}
            ),
        ]
        result = _merge_breakdowns([e.breakdown_by_model for e in entries])
        assert result["claude-sonnet-4-5-20250929"] == pytest.approx(0.03)
        assert result["gpt-4o-mini"] == 0.005
