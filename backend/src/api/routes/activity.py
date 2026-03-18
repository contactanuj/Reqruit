"""Activity tracking routes — daily actions, XP, streaks, and leagues."""

from datetime import date, datetime, UTC

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.db.documents.user import User
from src.repositories.user_activity_repository import UserActivityRepository
from src.services.streak_service import StreakService

logger = structlog.get_logger()
router = APIRouter(prefix="/activity", tags=["activity"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class TrackActionRequest(BaseModel):
    action_type: str
    metadata: dict = Field(default_factory=dict)
    locale: str | None = None


class TrackActionResponse(BaseModel):
    action_type: str
    xp_earned: int
    timestamp: str
    daily_total_xp: int
    streak_count: int
    season_boost: bool = False


class TodayActivityResponse(BaseModel):
    actions: list[dict]
    total_xp: int
    streak_count: int
    current_league: str


class DailySummary(BaseModel):
    date: str
    actions: list[dict]
    total_xp: int


class StreakResponse(BaseModel):
    streak_count: int
    freeze_count: int
    next_milestone: int | None
    milestone_history: list[int]


class LeagueResponse(BaseModel):
    current_league: str
    weekly_xp: int
    xp_to_next_league: int | None
    season_boost_active: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/track", response_model=TrackActionResponse)
async def track_action(
    request: TrackActionRequest,
    user: User = Depends(get_current_user),
) -> TrackActionResponse:
    """Track a completed action and award XP."""
    repo = UserActivityRepository()
    service = StreakService(repo)

    # Check and update streak on first action of the day
    await service.check_and_update_streak(user.id)

    entry = await service.record_action(
        user_id=user.id,
        action_type=request.action_type,
        metadata=request.metadata,
        locale=request.locale,
    )

    activity = await repo.get_today(user.id)

    return TrackActionResponse(
        action_type=entry.action_type,
        xp_earned=entry.xp_earned,
        timestamp=entry.timestamp.isoformat(),
        daily_total_xp=activity.total_xp if activity else entry.xp_earned,
        streak_count=activity.streak_count if activity else 0,
        season_boost=entry.metadata.get("season_boost", False),
    )


@router.get("/today", response_model=TodayActivityResponse)
async def get_today_activity(
    user: User = Depends(get_current_user),
) -> TodayActivityResponse:
    """Get today's activity summary."""
    repo = UserActivityRepository()
    activity = await repo.get_today(user.id)

    if not activity:
        return TodayActivityResponse(
            actions=[],
            total_xp=0,
            streak_count=0,
            current_league="bronze",
        )

    return TodayActivityResponse(
        actions=[a.model_dump() for a in activity.actions],
        total_xp=activity.total_xp,
        streak_count=activity.streak_count,
        current_league=activity.current_league,
    )


@router.get("/history", response_model=list[DailySummary])
async def get_activity_history(
    from_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    to_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    user: User = Depends(get_current_user),
) -> list[DailySummary]:
    """Get activity history for a date range (max 90 days)."""
    delta = (to_date - from_date).days
    if delta < 0:
        raise HTTPException(status_code=422, detail="from_date must be before to_date")
    if delta > 90:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 90 days")

    repo = UserActivityRepository()
    from_dt = datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC)
    to_dt = datetime(to_date.year, to_date.month, to_date.day, tzinfo=UTC)

    records = await repo.get_history(user.id, from_dt, to_dt)

    return [
        DailySummary(
            date=r.date.strftime("%Y-%m-%d"),
            actions=[a.model_dump() for a in r.actions],
            total_xp=r.total_xp,
        )
        for r in records
    ]


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    user: User = Depends(get_current_user),
) -> StreakResponse:
    """Get current streak status."""
    repo = UserActivityRepository()
    activity = await repo.get_today(user.id)

    streak_count = activity.streak_count if activity else 0
    freeze_count = activity.freeze_count if activity else 0

    service = StreakService(repo)
    info = service.calculate_streak(streak_count, freeze_count)

    # Build milestone history from streak count
    from src.services.streak_service import STREAK_MILESTONES
    milestone_history = [m for m in STREAK_MILESTONES if m <= streak_count]

    return StreakResponse(
        streak_count=info.streak_count,
        freeze_count=info.freeze_count,
        next_milestone=info.next_milestone,
        milestone_history=milestone_history,
    )


@router.get("/league", response_model=LeagueResponse)
async def get_league(
    locale: str | None = Query(None, description="User locale (e.g. IN, US)"),
    user: User = Depends(get_current_user),
) -> LeagueResponse:
    """Get current league status."""
    repo = UserActivityRepository()
    activity = await repo.get_today(user.id)

    weekly_xp = activity.week_start_xp if activity else 0
    current_league = activity.current_league if activity else "bronze"

    service = StreakService(repo)
    status = service.get_league_status(weekly_xp, current_league, locale=locale)

    return LeagueResponse(
        current_league=status.current_league,
        weekly_xp=status.weekly_xp,
        xp_to_next_league=status.xp_to_next_league,
        season_boost_active=status.season_boost_active,
    )
