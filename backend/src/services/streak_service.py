"""Streak service — XP calculation, streaks, leagues, and season boost.

XP values are DETERMINISTIC (NFR-P4-5): pure dict lookup, no LLM, no randomness.
Streak freeze awards NO XP (NFR-P4-7).
"""

from datetime import UTC, datetime, timedelta
from enum import StrEnum

import structlog
from beanie import PydanticObjectId
from pydantic import BaseModel

from src.core.exceptions import BusinessValidationError
from src.db.documents.user_activity import ActivityEntry
from src.repositories.user_activity_repository import UserActivityRepository

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Action types and XP table
# ---------------------------------------------------------------------------


class ActionType(StrEnum):
    """Valid trackable action types."""

    MOCK_INTERVIEW_COMPLETED = "mock_interview_completed"
    STAR_STORY_CREATED = "star_story_created"
    APPLICATION_SUBMITTED = "application_submitted"
    INTERVIEW_PREPPED = "interview_prepped"
    SKILLS_ASSESSED = "skills_assessed"
    NETWORKING_DONE = "networking_done"
    JOB_SAVED = "job_saved"


XP_TABLE: dict[str, int] = {
    ActionType.MOCK_INTERVIEW_COMPLETED: 50,
    ActionType.STAR_STORY_CREATED: 40,
    ActionType.APPLICATION_SUBMITTED: 30,
    ActionType.INTERVIEW_PREPPED: 25,
    ActionType.SKILLS_ASSESSED: 20,
    ActionType.NETWORKING_DONE: 15,
    ActionType.JOB_SAVED: 5,
}


# ---------------------------------------------------------------------------
# Streak constants
# ---------------------------------------------------------------------------

STREAK_MILESTONES: list[int] = [7, 14, 30, 60, 90]

MILESTONE_BONUS_XP: dict[int, int] = {
    7: 25,
    14: 50,
    30: 100,
    60: 200,
    90: 500,
}

FREEZE_EARN_INTERVAL = 7
MAX_BANKED_FREEZES = 3

STREAK_RESET_MESSAGE = "Streaks reset, but your skills don't. Start fresh!"


# ---------------------------------------------------------------------------
# League constants
# ---------------------------------------------------------------------------

LEAGUE_THRESHOLDS: list[tuple[str, int, int | None]] = [
    ("bronze", 0, 99),
    ("silver", 100, 249),
    ("gold", 250, 499),
    ("platinum", 500, 999),
    ("diamond", 1000, None),
]

INDIA_SEASON_MULTIPLIER = 1.5


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class StreakInfo(BaseModel):
    streak_count: int
    freeze_count: int
    next_milestone: int | None
    milestone_reached: int | None = None
    milestone_bonus_xp: int = 0


class StreakResult(BaseModel):
    streak_count: int
    freeze_count: int
    was_frozen: bool = False
    was_reset: bool = False
    reset_message: str | None = None
    milestone_reached: int | None = None
    milestone_bonus_xp: int = 0


class LeagueStatus(BaseModel):
    current_league: str
    weekly_xp: int
    xp_to_next_league: int | None
    season_boost_active: bool = False


# ---------------------------------------------------------------------------
# Season boost
# ---------------------------------------------------------------------------


def is_india_hiring_season(d: datetime) -> bool:
    """Returns True if date is January 1 through March 31."""
    return 1 <= d.month <= 3


def determine_league(weekly_xp: int) -> str:
    """Determine league from weekly XP total."""
    for name, low, high in LEAGUE_THRESHOLDS:
        if high is None or weekly_xp <= high:
            if weekly_xp >= low:
                return name
    return "bronze"


def xp_to_next_league(weekly_xp: int) -> int | None:
    """Return XP needed to reach next league, or None if already Diamond."""
    for i, (name, low, high) in enumerate(LEAGUE_THRESHOLDS):
        if high is None:
            return None  # Diamond — no next league
        if weekly_xp <= high:
            if i + 1 < len(LEAGUE_THRESHOLDS):
                return LEAGUE_THRESHOLDS[i + 1][1] - weekly_xp
            return None
    return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class StreakService:
    """Tracks daily actions, streaks, leagues, and awards deterministic XP."""

    def __init__(self, user_activity_repo: UserActivityRepository) -> None:
        self._repo = user_activity_repo

    def award_xp(self, action_type: str, locale: str | None = None) -> int:
        """Look up XP for an action type with optional India season boost.

        Raises BusinessValidationError for unknown types.
        XP remains deterministic (NFR-P4-5) — multiplier is a static rule.
        """
        if action_type not in XP_TABLE:
            raise BusinessValidationError(
                detail=f"Unknown action type: {action_type}",
                error_code="INVALID_ACTION_TYPE",
            )
        base_xp = XP_TABLE[action_type]
        if locale and locale.upper() == "IN" and is_india_hiring_season(datetime.now(UTC)):
            return int(base_xp * INDIA_SEASON_MULTIPLIER)
        return base_xp

    async def record_action(
        self,
        user_id: PydanticObjectId,
        action_type: str,
        metadata: dict | None = None,
        locale: str | None = None,
    ) -> ActivityEntry:
        """Validate action, award XP, append to today's activity, return the entry."""
        xp = self.award_xp(action_type, locale=locale)

        entry_metadata = dict(metadata or {})
        if locale and locale.upper() == "IN" and is_india_hiring_season(datetime.now(UTC)):
            entry_metadata["season_boost"] = True

        entry = ActivityEntry(
            action_type=action_type,
            xp_earned=xp,
            timestamp=datetime.now(UTC),
            metadata=entry_metadata,
        )

        activity = await self._repo.get_or_create_today(user_id)
        activity.actions.append(entry)
        activity.total_xp += xp
        activity.week_start_xp += xp

        # Check league promotion on every action
        activity.current_league = determine_league(activity.week_start_xp)

        await activity.save()

        logger.info(
            "action_tracked",
            user_id=str(user_id),
            action_type=action_type,
            xp_earned=xp,
            daily_total_xp=activity.total_xp,
        )

        return entry

    async def check_and_update_streak(
        self, user_id: PydanticObjectId
    ) -> StreakResult:
        """Called on first action of the day: check yesterday, increment/freeze/reset."""
        today = await self._repo.get_or_create_today(user_id)

        # If already has actions today, streak was already checked
        if today.actions:
            return StreakResult(
                streak_count=today.streak_count,
                freeze_count=today.freeze_count,
            )

        # Find yesterday's activity
        yesterday = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_activity = await self._repo.find_one(
            {"user_id": user_id, "date": yesterday}
        )

        if yesterday_activity and yesterday_activity.actions:
            # Continue streak
            new_streak = yesterday_activity.streak_count + 1
            freeze_count = yesterday_activity.freeze_count

            # Bank a freeze every 7-day streak
            if new_streak > 0 and new_streak % FREEZE_EARN_INTERVAL == 0:
                freeze_count = min(freeze_count + 1, MAX_BANKED_FREEZES)

            today.streak_count = new_streak
            today.freeze_count = freeze_count
            today.current_league = yesterday_activity.current_league
            today.week_start_xp = yesterday_activity.week_start_xp

            # Check milestone
            milestone_reached = None
            milestone_bonus = 0
            if new_streak in STREAK_MILESTONES:
                milestone_reached = new_streak
                milestone_bonus = MILESTONE_BONUS_XP.get(new_streak, 0)
                today.total_xp += milestone_bonus
                today.week_start_xp += milestone_bonus

            await today.save()

            return StreakResult(
                streak_count=new_streak,
                freeze_count=freeze_count,
                milestone_reached=milestone_reached,
                milestone_bonus_xp=milestone_bonus,
            )

        elif yesterday_activity is None or not yesterday_activity.actions:
            # Missed yesterday — try to find most recent activity
            recent = await self._repo.find_many(
                filters={"user_id": user_id, "date": {"$lt": yesterday}},
                sort="-date",
                limit=1,
            )
            prev = recent[0] if recent else None
            prev_streak = prev.streak_count if prev else 0
            prev_freeze = prev.freeze_count if prev else 0
            prev_league = prev.current_league if prev else "bronze"
            prev_week_xp = prev.week_start_xp if prev else 0

            if prev_freeze > 0:
                # Apply freeze — preserve streak, NO XP (NFR-P4-7)
                today.streak_count = prev_streak
                today.freeze_count = prev_freeze - 1
                today.current_league = prev_league
                today.week_start_xp = prev_week_xp
                await today.save()

                return StreakResult(
                    streak_count=prev_streak,
                    freeze_count=prev_freeze - 1,
                    was_frozen=True,
                )
            else:
                # Reset streak
                today.streak_count = 0
                today.freeze_count = 0
                today.current_league = prev_league
                today.week_start_xp = prev_week_xp
                await today.save()

                return StreakResult(
                    streak_count=0,
                    freeze_count=0,
                    was_reset=True,
                    reset_message=STREAK_RESET_MESSAGE,
                )

    def calculate_streak(self, streak_count: int, freeze_count: int) -> StreakInfo:
        """Return streak info with next milestone."""
        next_milestone = None
        for m in STREAK_MILESTONES:
            if streak_count < m:
                next_milestone = m
                break

        return StreakInfo(
            streak_count=streak_count,
            freeze_count=freeze_count,
            next_milestone=next_milestone,
        )

    def check_league_promotion(self, weekly_xp: int) -> str:
        """Compute league from weekly XP."""
        return determine_league(weekly_xp)

    def get_league_status(
        self, weekly_xp: int, current_league: str, locale: str | None = None
    ) -> LeagueStatus:
        """Return current league, weekly XP, XP to next league."""
        boost_active = (
            locale is not None
            and locale.upper() == "IN"
            and is_india_hiring_season(datetime.now(UTC))
        )
        return LeagueStatus(
            current_league=current_league,
            weekly_xp=weekly_xp,
            xp_to_next_league=xp_to_next_league(weekly_xp),
            season_boost_active=boost_active,
        )

# ---------------------------------------------------------------------------
# Weekly metrics and inflection detection
# ---------------------------------------------------------------------------

INFLECTION_THRESHOLD = 0.30  # 30% decline triggers inflection warning
MIN_APPLICATIONS_FOR_DATA = 5


class WeeklyMetrics(BaseModel):
    applications_count: int = 0
    interviews_count: int = 0
    responses_count: int = 0
    xp_earned: int = 0
    action_breakdown: dict = {}


class WeekComparison(BaseModel):
    current: WeeklyMetrics
    previous: WeeklyMetrics
    applications_change_pct: float = 0.0
    interviews_change_pct: float = 0.0
    responses_change_pct: float = 0.0
    xp_change_pct: float = 0.0


class InflectionResult(BaseModel):
    metric_name: str
    previous_value: float
    current_value: float
    decline_pct: float
    pivot_suggestion: str


def aggregate_weekly_metrics(activities: list) -> WeeklyMetrics:
    """Aggregate activity records into weekly metrics."""
    total_xp = 0
    breakdown: dict[str, int] = {}

    for activity in activities:
        total_xp += activity.total_xp
        for action in activity.actions:
            breakdown[action.action_type] = breakdown.get(action.action_type, 0) + 1

    return WeeklyMetrics(
        applications_count=breakdown.get("application_submitted", 0),
        interviews_count=breakdown.get("interview_prepped", 0),
        responses_count=breakdown.get("mock_interview_completed", 0),
        xp_earned=total_xp,
        action_breakdown=breakdown,
    )


def compute_week_comparison(current: WeeklyMetrics, previous: WeeklyMetrics) -> WeekComparison:
    """Compare two weeks of metrics with percentage changes."""
    def pct_change(curr: int, prev: int) -> float:
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return round(((curr - prev) / prev) * 100, 1)

    return WeekComparison(
        current=current,
        previous=previous,
        applications_change_pct=pct_change(current.applications_count, previous.applications_count),
        interviews_change_pct=pct_change(current.interviews_count, previous.interviews_count),
        responses_change_pct=pct_change(current.responses_count, previous.responses_count),
        xp_change_pct=pct_change(current.xp_earned, previous.xp_earned),
    )


def detect_strategy_inflection(
    current: WeeklyMetrics, previous: WeeklyMetrics
) -> InflectionResult | None:
    """Detect >30% decline in response rate (responses/applications)."""
    if previous.applications_count < MIN_APPLICATIONS_FOR_DATA:
        return None
    if current.applications_count < MIN_APPLICATIONS_FOR_DATA:
        return None

    prev_rate = previous.responses_count / previous.applications_count
    curr_rate = current.responses_count / current.applications_count

    if prev_rate == 0:
        return None

    decline = (prev_rate - curr_rate) / prev_rate
    if decline > INFLECTION_THRESHOLD:
        prev_pct = round(prev_rate * 100, 1)
        curr_pct = round(curr_rate * 100, 1)
        return InflectionResult(
            metric_name="response_rate",
            previous_value=prev_pct,
            current_value=curr_pct,
            decline_pct=round(decline * 100, 1),
            pivot_suggestion=(
                f"Your response rate dropped from {prev_pct}% to {curr_pct}%. "
                "Consider: switching to quantified-achievement resume, targeting "
                "different company sizes, or adjusting submission timing"
            ),
        )

    return None


def is_data_sufficient(metrics: WeeklyMetrics) -> bool:
    """Returns True if enough applications to be data-driven."""
    return metrics.applications_count >= MIN_APPLICATIONS_FOR_DATA
