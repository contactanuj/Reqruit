"""Tests for BatchAndBreatheScheduler — deterministic weekly rhythm scheduler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from src.services.batch_and_breathe_scheduler import (
    BURNOUT_RATIOS,
    DAYS_OF_WEEK,
    INDIA_SEASON_RATIOS,
    MINIMUM_REST_BLOCK_MINUTES,
    NORMAL_RATIOS,
    BatchAndBreatheScheduler,
    _build_time_blocks,
)
from src.services.morale_service import BurnoutResult, BurnoutSignal, MoraleService


USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _no_burnout():
    return BurnoutResult(
        signals=[], has_warning=False, overall_severity="low",
        recommendation="No burnout signals detected.",
    )


def _has_burnout():
    return BurnoutResult(
        signals=[BurnoutSignal(signal_type="high_volume_burst", description="test", recommendation="test", severity="high")],
        has_warning=True, overall_severity="high",
        recommendation="Take a break.",
    )


def _make_scheduler(burnout_result=None):
    morale = MagicMock(spec=MoraleService)
    morale.detect_burnout = AsyncMock(return_value=burnout_result or _no_burnout())
    return BatchAndBreatheScheduler(morale_service=morale)


# ---------------------------------------------------------------------------
# Default schedule
# ---------------------------------------------------------------------------


class TestDefaultSchedule:
    async def test_7_days_in_schedule(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(USER_ID)
        assert len(result.days) == 7

    async def test_4_activity_types_present(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(USER_ID)

        all_types = set()
        for day in result.days:
            for block in day.blocks:
                all_types.add(block.activity_type)

        assert {"apply", "network", "prep", "rest"} == all_types

    async def test_mandatory_rest_on_active_days(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(USER_ID)

        for day in result.days:
            if not day.is_rest_day:
                rest_blocks = [b for b in day.blocks if b.activity_type == "rest"]
                assert len(rest_blocks) >= 1
                total_rest = sum(b.duration_minutes for b in rest_blocks)
                assert total_rest >= MINIMUM_REST_BLOCK_MINUTES

    async def test_rest_day_marked_correctly(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(
            USER_ID, preferred_rest_days=["Sunday"]
        )

        sunday = [d for d in result.days if d.day == "Sunday"][0]
        assert sunday.is_rest_day is True

    async def test_no_burnout_no_season(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(USER_ID)
        assert result.season_boost is False
        assert result.burnout_adjusted is False


# ---------------------------------------------------------------------------
# Daily app limit
# ---------------------------------------------------------------------------


class TestDailyAppLimit:
    async def test_cap_at_3_redistributes_time(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(USER_ID, daily_app_limit=3)

        for day in result.days:
            if not day.is_rest_day:
                apply_blocks = [b for b in day.blocks if b.activity_type == "apply"]
                for block in apply_blocks:
                    assert "max 3" in block.description

    async def test_apply_block_limited_by_cap(self):
        # 3 apps * 20 min = 60 min. With 6 hours, normal apply would be 144 min.
        blocks = _build_time_blocks(NORMAL_RATIOS, 360, daily_app_limit=3)
        apply_blocks = [b for b in blocks if b.activity_type == "apply"]
        total_apply = sum(b.duration_minutes for b in apply_blocks)
        assert total_apply == 60  # 3 * 20 min


# ---------------------------------------------------------------------------
# Preferred rest days
# ---------------------------------------------------------------------------


class TestPreferredRestDays:
    async def test_sunday_is_rest_day(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(
            USER_ID, preferred_rest_days=["Sunday"]
        )
        sunday = [d for d in result.days if d.day == "Sunday"][0]
        assert sunday.is_rest_day is True
        # Should have mostly rest blocks
        rest_minutes = sum(
            b.duration_minutes for b in sunday.blocks if b.activity_type == "rest"
        )
        assert rest_minutes > 0

    async def test_multiple_rest_days(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(
            USER_ID, preferred_rest_days=["Saturday", "Sunday"]
        )
        rest_days = [d for d in result.days if d.is_rest_day]
        assert len(rest_days) == 2

    async def test_rest_day_has_optional_networking(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(
            USER_ID, preferred_rest_days=["Sunday"]
        )
        sunday = [d for d in result.days if d.day == "Sunday"][0]
        network_blocks = [b for b in sunday.blocks if b.activity_type == "network"]
        assert len(network_blocks) >= 1
        assert "optional" in network_blocks[0].description.lower()


# ---------------------------------------------------------------------------
# India hiring season boost
# ---------------------------------------------------------------------------


class TestIndiaSeasonBoost:
    @patch("src.services.batch_and_breathe_scheduler.datetime")
    async def test_season_boost_active(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(USER_ID, locale="IN")

        assert result.season_boost is True
        assert any("appraisal season" in n.lower() for n in result.notes)

    @patch("src.services.batch_and_breathe_scheduler.datetime")
    async def test_no_season_boost_outside_jan_mar(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 6, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(USER_ID, locale="IN")

        assert result.season_boost is False


# ---------------------------------------------------------------------------
# Burnout adjustment
# ---------------------------------------------------------------------------


class TestBurnoutAdjustment:
    async def test_burnout_switches_ratios(self):
        scheduler = _make_scheduler(_has_burnout())
        result = await scheduler.generate_schedule(USER_ID)

        assert result.burnout_adjusted is True
        assert any("quality over quantity" in n.lower() for n in result.notes)

    async def test_burnout_reduces_app_limit(self):
        scheduler = _make_scheduler(_has_burnout())
        result = await scheduler.generate_schedule(USER_ID, daily_app_limit=6)

        # App limit should be halved: 6 // 2 = 3
        for day in result.days:
            if not day.is_rest_day:
                apply_blocks = [b for b in day.blocks if b.activity_type == "apply"]
                for block in apply_blocks:
                    assert "max 3" in block.description

    async def test_burnout_minimum_app_limit(self):
        scheduler = _make_scheduler(_has_burnout())
        # With daily_app_limit=2, halved = 1, but minimum is 2
        result = await scheduler.generate_schedule(USER_ID, daily_app_limit=2)

        for day in result.days:
            if not day.is_rest_day:
                apply_blocks = [b for b in day.blocks if b.activity_type == "apply"]
                for block in apply_blocks:
                    assert "max 2" in block.description

    async def test_burnout_has_extra_rest_blocks(self):
        scheduler = _make_scheduler(_has_burnout())
        result = await scheduler.generate_schedule(USER_ID)

        for day in result.days:
            if not day.is_rest_day:
                rest_blocks = [b for b in day.blocks if b.activity_type == "rest"]
                # Burnout interleaves rest → should have multiple rest blocks
                assert len(rest_blocks) >= 2


# ---------------------------------------------------------------------------
# Burnout + India season: burnout takes priority
# ---------------------------------------------------------------------------


class TestBurnoutPriority:
    @patch("src.services.batch_and_breathe_scheduler.datetime")
    async def test_burnout_overrides_season(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        scheduler = _make_scheduler(_has_burnout())
        result = await scheduler.generate_schedule(USER_ID, locale="IN")

        assert result.burnout_adjusted is True
        # Season boost should be False when burnout is active
        assert result.season_boost is False
        assert any("quality over quantity" in n.lower() for n in result.notes)


# ---------------------------------------------------------------------------
# Available hours
# ---------------------------------------------------------------------------


class TestAvailableHours:
    async def test_4_hours_produces_smaller_blocks(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(
            USER_ID, available_hours_per_day=4.0
        )

        for day in result.days:
            if not day.is_rest_day:
                total = sum(b.duration_minutes for b in day.blocks)
                # Should be around 240 minutes
                assert 200 <= total <= 280

    async def test_blocks_dont_overlap(self):
        scheduler = _make_scheduler()
        result = await scheduler.generate_schedule(USER_ID)

        for day in result.days:
            if not day.is_rest_day:
                for i in range(len(day.blocks) - 1):
                    curr = day.blocks[i]
                    nxt = day.blocks[i + 1]
                    # Parse start times
                    ch, cm = map(int, curr.start_time.split(":"))
                    nh, nm = map(int, nxt.start_time.split(":"))
                    curr_end = ch * 60 + cm + curr.duration_minutes
                    next_start = nh * 60 + nm
                    assert curr_end <= next_start
