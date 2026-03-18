"""BatchAndBreatheScheduler — deterministic weekly rhythm scheduler.

Generates a personalized weekly schedule allocating time across 4 activity types:
apply, network, prep, rest. All scheduling is deterministic (no LLM).
"""

from datetime import UTC, datetime

import structlog
from beanie import PydanticObjectId
from pydantic import BaseModel

from src.services.morale_service import MoraleService

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MINUTES_PER_APPLICATION = 20

# Normal ratios
NORMAL_RATIOS = {"apply": 0.40, "network": 0.20, "prep": 0.25, "rest": 0.15}

# India hiring season ratios (Jan-Mar, locale=IN)
INDIA_SEASON_RATIOS = {"apply": 0.50, "network": 0.10, "prep": 0.30, "rest": 0.10}

# Burnout-adjusted ratios
BURNOUT_RATIOS = {"apply": 0.25, "network": 0.15, "prep": 0.20, "rest": 0.40}

MINIMUM_REST_BLOCK_MINUTES = 30
MINIMUM_BURNOUT_APP_LIMIT = 2


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class TimeBlock(BaseModel):
    activity_type: str
    start_time: str
    duration_minutes: int
    description: str


class DailySchedule(BaseModel):
    day: str
    blocks: list[TimeBlock]
    is_rest_day: bool


class WeeklySchedule(BaseModel):
    days: list[DailySchedule]
    season_boost: bool
    burnout_adjusted: bool
    notes: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_india_hiring_season(d: datetime) -> bool:
    """Returns True if date is January 1 through March 31."""
    return 1 <= d.month <= 3


def _build_time_blocks(
    ratios: dict[str, float],
    available_minutes: int,
    daily_app_limit: int,
    start_hour: int = 9,
    burnout_active: bool = False,
) -> list[TimeBlock]:
    """Build non-overlapping time blocks for an active day."""
    blocks: list[TimeBlock] = []
    current_minute = start_hour * 60  # start at 09:00 by default

    # Calculate raw allocations
    allocations: dict[str, int] = {}
    for activity, ratio in ratios.items():
        allocations[activity] = int(available_minutes * ratio)

    # Enforce daily app limit cap
    app_time_needed = daily_app_limit * MINUTES_PER_APPLICATION
    if app_time_needed < allocations.get("apply", 0):
        excess = allocations["apply"] - app_time_needed
        allocations["apply"] = app_time_needed
        # Redistribute excess: 60% network, 40% prep
        allocations["network"] = allocations.get("network", 0) + int(excess * 0.6)
        allocations["prep"] = allocations.get("prep", 0) + int(excess * 0.4)

    # Ensure minimum rest block
    if allocations.get("rest", 0) < MINIMUM_REST_BLOCK_MINUTES:
        allocations["rest"] = MINIMUM_REST_BLOCK_MINUTES

    # Build blocks in order: apply, network, prep, rest
    # If burnout, interleave rest between activities
    activity_order = ["apply", "network", "prep", "rest"]

    if burnout_active:
        # Interleave: apply, rest-mini, network, rest-mini, prep, rest
        rest_total = allocations.get("rest", 30)
        mini_rest = max(15, rest_total // 3)
        main_rest = rest_total - 2 * mini_rest

        for activity in ["apply", "network", "prep"]:
            duration = allocations.get(activity, 0)
            if duration > 0:
                h, m = divmod(current_minute, 60)
                blocks.append(TimeBlock(
                    activity_type=activity,
                    start_time=f"{h:02d}:{m:02d}",
                    duration_minutes=duration,
                    description=_description(activity, duration, daily_app_limit),
                ))
                current_minute += duration

                # Add mini rest between activities
                if activity != "prep":
                    h, m = divmod(current_minute, 60)
                    blocks.append(TimeBlock(
                        activity_type="rest",
                        start_time=f"{h:02d}:{m:02d}",
                        duration_minutes=mini_rest,
                        description="Break — step away, hydrate, decompress",
                    ))
                    current_minute += mini_rest

        # Final rest block
        if main_rest > 0:
            h, m = divmod(current_minute, 60)
            blocks.append(TimeBlock(
                activity_type="rest",
                start_time=f"{h:02d}:{m:02d}",
                duration_minutes=main_rest,
                description="Extended rest — recharge for tomorrow",
            ))
    else:
        for activity in activity_order:
            duration = allocations.get(activity, 0)
            if duration > 0:
                h, m = divmod(current_minute, 60)
                blocks.append(TimeBlock(
                    activity_type=activity,
                    start_time=f"{h:02d}:{m:02d}",
                    duration_minutes=duration,
                    description=_description(activity, duration, daily_app_limit),
                ))
                current_minute += duration

    return blocks


def _description(activity: str, duration: int, daily_app_limit: int) -> str:
    """Generate a human-readable description for a time block."""
    if activity == "apply":
        return f"Apply (max {daily_app_limit} targeted applications)"
    elif activity == "network":
        msgs = max(1, duration // 15)
        return f"Network ({msgs} outreach messages or LinkedIn connections)"
    elif activity == "prep":
        return "Prep (mock interview practice, STAR stories, or skill review)"
    elif activity == "rest":
        return "Rest — take a real break, no screens"
    return activity


def _build_rest_day(day_name: str, available_minutes: int) -> DailySchedule:
    """Build a rest day schedule with optional light networking."""
    blocks = [
        TimeBlock(
            activity_type="rest",
            start_time="09:00",
            duration_minutes=available_minutes - 30,
            description="Full rest day — recharge your energy",
        ),
        TimeBlock(
            activity_type="network",
            start_time="17:00",
            duration_minutes=30,
            description="Optional: light networking (1 casual message)",
        ),
    ]
    return DailySchedule(day=day_name, blocks=blocks, is_rest_day=True)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BatchAndBreatheScheduler:
    """Deterministic weekly rhythm scheduler."""

    def __init__(self, morale_service: MoraleService) -> None:
        self._morale = morale_service

    async def generate_schedule(
        self,
        user_id: PydanticObjectId,
        daily_app_limit: int = 5,
        available_hours_per_day: float = 6.0,
        preferred_rest_days: list[str] | None = None,
        locale: str | None = None,
    ) -> WeeklySchedule:
        """Generate a personalized weekly schedule."""
        if preferred_rest_days is None:
            preferred_rest_days = ["Sunday"]

        rest_days_lower = [d.lower() for d in preferred_rest_days]
        available_minutes = int(available_hours_per_day * 60)
        notes: list[str] = []

        # Check burnout
        burnout = await self._morale.detect_burnout(user_id)
        burnout_active = burnout.has_warning

        # Check India hiring season
        now = datetime.now(UTC)
        season_boost = (
            locale is not None
            and locale.upper() == "IN"
            and is_india_hiring_season(now)
        )

        # Select ratios — burnout takes priority over season (health > opportunity)
        if burnout_active:
            ratios = BURNOUT_RATIOS.copy()
            daily_app_limit = max(MINIMUM_BURNOUT_APP_LIMIT, daily_app_limit // 2)
            season_boost = False  # burnout overrides season
            notes.append(
                "Your morale indicators suggest pulling back. "
                "Quality over quantity this week"
            )
        elif season_boost:
            ratios = INDIA_SEASON_RATIOS.copy()
            notes.append(
                "Appraisal season — companies are actively hiring. "
                "This is your highest-ROI window"
            )
        else:
            ratios = NORMAL_RATIOS.copy()

        # Build daily schedules
        days: list[DailySchedule] = []
        for day_name in DAYS_OF_WEEK:
            if day_name.lower() in rest_days_lower:
                days.append(_build_rest_day(day_name, available_minutes))
            else:
                blocks = _build_time_blocks(
                    ratios=ratios,
                    available_minutes=available_minutes,
                    daily_app_limit=daily_app_limit,
                    burnout_active=burnout_active,
                )
                days.append(DailySchedule(
                    day=day_name,
                    blocks=blocks,
                    is_rest_day=False,
                ))

        return WeeklySchedule(
            days=days,
            season_boost=season_boost,
            burnout_adjusted=burnout_active,
            notes=notes,
        )
