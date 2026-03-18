"""Tests for StreakService — XP calculation, streaks, leagues, and season boost."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from src.core.exceptions import BusinessValidationError
from src.db.documents.user_activity import ActivityEntry, UserActivity
from src.services.streak_service import (
    INDIA_SEASON_MULTIPLIER,
    MAX_BANKED_FREEZES,
    MILESTONE_BONUS_XP,
    STREAK_RESET_MESSAGE,
    ActionType,
    StreakService,
    XP_TABLE,
    determine_league,
    is_india_hiring_season,
    xp_to_next_league,
)


USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _make_activity(**kwargs):
    defaults = {
        "actions": [],
        "total_xp": 0,
        "streak_count": 0,
        "freeze_count": 0,
        "current_league": "bronze",
        "week_start_xp": 0,
    }
    defaults.update(kwargs)
    mock = MagicMock(spec=UserActivity)
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.save = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# XP Table
# ---------------------------------------------------------------------------


class TestXPTable:
    def test_mock_interview_completed(self):
        assert XP_TABLE["mock_interview_completed"] == 50

    def test_star_story_created(self):
        assert XP_TABLE["star_story_created"] == 40

    def test_application_submitted(self):
        assert XP_TABLE["application_submitted"] == 30

    def test_interview_prepped(self):
        assert XP_TABLE["interview_prepped"] == 25

    def test_skills_assessed(self):
        assert XP_TABLE["skills_assessed"] == 20

    def test_networking_done(self):
        assert XP_TABLE["networking_done"] == 15

    def test_job_saved(self):
        assert XP_TABLE["job_saved"] == 5

    def test_all_action_types_covered(self):
        for action in ActionType:
            assert action.value in XP_TABLE


# ---------------------------------------------------------------------------
# Award XP
# ---------------------------------------------------------------------------


class TestAwardXP:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = StreakService(self.repo)

    def test_returns_correct_xp(self):
        assert self.service.award_xp("application_submitted") == 30

    def test_unknown_action_raises(self):
        with pytest.raises(BusinessValidationError) as exc_info:
            self.service.award_xp("invalid_action")
        assert "Unknown action type" in str(exc_info.value.detail)

    def test_deterministic_no_randomness(self):
        """XP must be deterministic — same input always gives same output (NFR-P4-5)."""
        results = [self.service.award_xp("job_saved") for _ in range(100)]
        assert all(r == 5 for r in results)


# ---------------------------------------------------------------------------
# India Season Boost
# ---------------------------------------------------------------------------


class TestIndiaSeasonBoost:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = StreakService(self.repo)

    def test_is_india_hiring_season_january(self):
        assert is_india_hiring_season(datetime(2026, 1, 15, tzinfo=UTC)) is True

    def test_is_india_hiring_season_march(self):
        assert is_india_hiring_season(datetime(2026, 3, 31, tzinfo=UTC)) is True

    def test_not_india_hiring_season_april(self):
        assert is_india_hiring_season(datetime(2026, 4, 1, tzinfo=UTC)) is False

    def test_not_india_hiring_season_december(self):
        assert is_india_hiring_season(datetime(2026, 12, 1, tzinfo=UTC)) is False

    @patch("src.services.streak_service.datetime")
    def test_boost_applied_for_in_locale_in_season(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        xp = self.service.award_xp("job_saved", locale="IN")
        assert xp == int(5 * INDIA_SEASON_MULTIPLIER)  # 7

    @patch("src.services.streak_service.datetime")
    def test_no_boost_for_us_locale_in_season(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        xp = self.service.award_xp("job_saved", locale="US")
        assert xp == 5

    @patch("src.services.streak_service.datetime")
    def test_no_boost_for_in_locale_outside_season(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 7, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        xp = self.service.award_xp("job_saved", locale="IN")
        assert xp == 5

    @patch("src.services.streak_service.datetime")
    def test_boost_deterministic(self, mock_dt):
        """Even with boost, XP is deterministic (NFR-P4-5)."""
        mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        results = [self.service.award_xp("application_submitted", locale="IN") for _ in range(50)]
        assert all(r == 45 for r in results)  # 30 * 1.5 = 45


# ---------------------------------------------------------------------------
# Record Action
# ---------------------------------------------------------------------------


class TestRecordAction:
    def setup_method(self):
        self.repo = MagicMock()
        self.activity = _make_activity()
        self.repo.get_or_create_today = AsyncMock(return_value=self.activity)
        self.service = StreakService(self.repo)

    async def test_creates_entry_with_correct_xp(self):
        entry = await self.service.record_action(USER_ID, "application_submitted")
        assert entry.action_type == "application_submitted"
        assert entry.xp_earned == 30

    async def test_appends_to_activity(self):
        await self.service.record_action(USER_ID, "job_saved")
        assert len(self.activity.actions) == 1

    async def test_updates_total_xp(self):
        await self.service.record_action(USER_ID, "job_saved")
        assert self.activity.total_xp == 5

    async def test_updates_week_start_xp(self):
        await self.service.record_action(USER_ID, "job_saved")
        assert self.activity.week_start_xp == 5

    async def test_saves_activity(self):
        await self.service.record_action(USER_ID, "job_saved")
        self.activity.save.assert_called_once()

    async def test_passes_metadata(self):
        entry = await self.service.record_action(
            USER_ID, "job_saved", metadata={"job_id": "xyz"}
        )
        assert entry.metadata["job_id"] == "xyz"

    async def test_invalid_action_raises_before_db(self):
        with pytest.raises(BusinessValidationError):
            await self.service.record_action(USER_ID, "invalid_action")
        self.repo.get_or_create_today.assert_not_called()

    @patch("src.services.streak_service.datetime")
    async def test_season_boost_flag_in_metadata(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        entry = await self.service.record_action(USER_ID, "job_saved", locale="IN")
        assert entry.metadata.get("season_boost") is True


# ---------------------------------------------------------------------------
# League calculation
# ---------------------------------------------------------------------------


class TestLeagueCalculation:
    def test_bronze_at_0(self):
        assert determine_league(0) == "bronze"

    def test_bronze_at_99(self):
        assert determine_league(99) == "bronze"

    def test_silver_at_100(self):
        assert determine_league(100) == "silver"

    def test_silver_at_249(self):
        assert determine_league(249) == "silver"

    def test_gold_at_250(self):
        assert determine_league(250) == "gold"

    def test_gold_at_499(self):
        assert determine_league(499) == "gold"

    def test_platinum_at_500(self):
        assert determine_league(500) == "platinum"

    def test_platinum_at_999(self):
        assert determine_league(999) == "platinum"

    def test_diamond_at_1000(self):
        assert determine_league(1000) == "diamond"

    def test_diamond_at_5000(self):
        assert determine_league(5000) == "diamond"

    def test_xp_to_next_from_bronze(self):
        result = xp_to_next_league(50)
        assert result == 50  # 100 - 50

    def test_xp_to_next_from_diamond(self):
        result = xp_to_next_league(1500)
        assert result is None


# ---------------------------------------------------------------------------
# Streak check and update
# ---------------------------------------------------------------------------


class TestCheckAndUpdateStreak:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = StreakService(self.repo)

    async def test_continues_streak_from_yesterday(self):
        today = _make_activity(actions=[], streak_count=0)
        yesterday = _make_activity(
            actions=[MagicMock()], streak_count=3, freeze_count=0,
            current_league="silver", week_start_xp=100,
        )
        self.repo.get_or_create_today = AsyncMock(return_value=today)
        self.repo.find_one = AsyncMock(return_value=yesterday)

        result = await self.service.check_and_update_streak(USER_ID)

        assert result.streak_count == 4
        assert not result.was_frozen
        assert not result.was_reset

    async def test_streak_freeze_preserves_count(self):
        today = _make_activity(actions=[], streak_count=0)
        # No yesterday activity — look at recent
        self.repo.get_or_create_today = AsyncMock(return_value=today)
        self.repo.find_one = AsyncMock(return_value=None)  # no yesterday
        prev = _make_activity(streak_count=5, freeze_count=2, current_league="gold", week_start_xp=300)
        self.repo.find_many = AsyncMock(return_value=[prev])

        result = await self.service.check_and_update_streak(USER_ID)

        assert result.streak_count == 5
        assert result.freeze_count == 1
        assert result.was_frozen is True

    async def test_streak_freeze_awards_no_xp(self):
        """NFR-P4-7: Frozen day awards 0 XP."""
        today = _make_activity(actions=[], streak_count=0, total_xp=0)
        self.repo.get_or_create_today = AsyncMock(return_value=today)
        self.repo.find_one = AsyncMock(return_value=None)
        prev = _make_activity(streak_count=5, freeze_count=1)
        self.repo.find_many = AsyncMock(return_value=[prev])

        await self.service.check_and_update_streak(USER_ID)

        assert today.total_xp == 0

    async def test_streak_reset_when_no_freeze(self):
        today = _make_activity(actions=[], streak_count=0)
        self.repo.get_or_create_today = AsyncMock(return_value=today)
        self.repo.find_one = AsyncMock(return_value=None)
        prev = _make_activity(streak_count=10, freeze_count=0)
        self.repo.find_many = AsyncMock(return_value=[prev])

        result = await self.service.check_and_update_streak(USER_ID)

        assert result.streak_count == 0
        assert result.was_reset is True
        assert result.reset_message == STREAK_RESET_MESSAGE

    async def test_milestone_at_7_days(self):
        today = _make_activity(actions=[], streak_count=0)
        yesterday = _make_activity(
            actions=[MagicMock()], streak_count=6, freeze_count=0,
            current_league="bronze", week_start_xp=0,
        )
        self.repo.get_or_create_today = AsyncMock(return_value=today)
        self.repo.find_one = AsyncMock(return_value=yesterday)

        result = await self.service.check_and_update_streak(USER_ID)

        assert result.streak_count == 7
        assert result.milestone_reached == 7
        assert result.milestone_bonus_xp == MILESTONE_BONUS_XP[7]

    async def test_freeze_banked_at_7_day_streak(self):
        today = _make_activity(actions=[], streak_count=0, freeze_count=0)
        yesterday = _make_activity(
            actions=[MagicMock()], streak_count=6, freeze_count=0,
            current_league="bronze", week_start_xp=0,
        )
        self.repo.get_or_create_today = AsyncMock(return_value=today)
        self.repo.find_one = AsyncMock(return_value=yesterday)

        await self.service.check_and_update_streak(USER_ID)

        assert today.freeze_count == 1

    async def test_freeze_capped_at_max(self):
        today = _make_activity(actions=[], streak_count=0, freeze_count=0)
        yesterday = _make_activity(
            actions=[MagicMock()], streak_count=13, freeze_count=MAX_BANKED_FREEZES,
            current_league="bronze", week_start_xp=0,
        )
        self.repo.get_or_create_today = AsyncMock(return_value=today)
        self.repo.find_one = AsyncMock(return_value=yesterday)

        await self.service.check_and_update_streak(USER_ID)

        assert today.freeze_count == MAX_BANKED_FREEZES

    async def test_already_has_actions_skips_check(self):
        today = _make_activity(actions=[MagicMock()], streak_count=5, freeze_count=1)
        self.repo.get_or_create_today = AsyncMock(return_value=today)

        result = await self.service.check_and_update_streak(USER_ID)

        assert result.streak_count == 5
        self.repo.find_one.assert_not_called()


# ---------------------------------------------------------------------------
# Calculate streak info
# ---------------------------------------------------------------------------


class TestCalculateStreak:
    def setup_method(self):
        self.service = StreakService(MagicMock())

    def test_next_milestone_from_0(self):
        info = self.service.calculate_streak(0, 0)
        assert info.next_milestone == 7

    def test_next_milestone_from_7(self):
        info = self.service.calculate_streak(7, 0)
        assert info.next_milestone == 14

    def test_next_milestone_from_90(self):
        info = self.service.calculate_streak(90, 0)
        assert info.next_milestone is None

    def test_includes_freeze_count(self):
        info = self.service.calculate_streak(5, 2)
        assert info.freeze_count == 2


# ---------------------------------------------------------------------------
# League status
# ---------------------------------------------------------------------------


class TestLeagueStatus:
    def setup_method(self):
        self.service = StreakService(MagicMock())

    def test_returns_current_league(self):
        status = self.service.get_league_status(150, "silver")
        assert status.current_league == "silver"
        assert status.weekly_xp == 150

    @patch("src.services.streak_service.datetime")
    def test_season_boost_active_for_in(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        status = self.service.get_league_status(100, "silver", locale="IN")
        assert status.season_boost_active is True

    @patch("src.services.streak_service.datetime")
    def test_no_season_boost_for_us(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        status = self.service.get_league_status(100, "silver", locale="US")
        assert status.season_boost_active is False

    def test_xp_to_next_league(self):
        status = self.service.get_league_status(50, "bronze")
        assert status.xp_to_next_league == 50
