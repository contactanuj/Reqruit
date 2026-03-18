"""Wellness routes — weekly strategy reviews and mental health features."""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_current_user
from src.db.documents.user import User
from src.repositories.user_activity_repository import UserActivityRepository
from src.services.streak_service import (
    WeeklyMetrics,
    aggregate_weekly_metrics,
    compute_week_comparison,
    detect_strategy_inflection,
    is_data_sufficient,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/wellness", tags=["wellness"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WeeklyMetricsResponse(BaseModel):
    applications_count: int
    interviews_count: int
    responses_count: int
    xp_earned: int
    action_breakdown: dict


class WeeklyReviewResponse(BaseModel):
    metrics: WeeklyMetricsResponse
    comparison_to_last_week: dict | None
    tactical_adjustments: list[str]
    next_week_goals: list[str]
    inflection_warning: str | None
    data_driven: bool
    encouragement: str


class BurnoutWarningResponse(BaseModel):
    signals: list[str]
    recommendation: str
    severity: str  # low, medium, high


class InterventionResponse(BaseModel):
    triggered_indicators: list[str]
    consecutive_negative_days: int
    recommendations: list[str]
    rest_suggestion: str | None


class MoraleDashboardResponse(BaseModel):
    response_rate_trend: str
    ghosting_frequency: int
    ghosting_percentage: float
    interview_conversion_rate: float
    time_since_last_positive_signal: int
    burnout_warning: BurnoutWarningResponse | None
    intervention: InterventionResponse | None


class ROIPredictRequest(BaseModel):
    job_id: str | None = None
    jd_text: str | None = None


class ROIContributingFactorsResponse(BaseModel):
    company_response_rate: float
    role_competition_level: float
    user_fit_score: float
    submission_timing: float


class ROIPredictResponse(BaseModel):
    probability_of_response: float
    classification: str
    contributing_factors: ROIContributingFactorsResponse
    personalized: bool
    confidence: str


class ScheduleRequest(BaseModel):
    daily_app_limit: int = 5
    available_hours_per_day: float = 6.0
    preferred_rest_days: list[str] = ["Sunday"]


class TimeBlockResponse(BaseModel):
    activity_type: str
    start_time: str
    duration_minutes: int
    description: str


class DailyScheduleResponse(BaseModel):
    day: str
    blocks: list[TimeBlockResponse]
    is_rest_day: bool


class WeeklyScheduleResponse(BaseModel):
    days: list[DailyScheduleResponse]
    season_boost: bool
    burnout_adjusted: bool
    notes: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/weekly-review", response_model=WeeklyReviewResponse)
async def generate_weekly_review(
    user: User = Depends(get_current_user),
) -> WeeklyReviewResponse:
    """Generate a weekly strategy review with tactical adjustments."""
    repo = UserActivityRepository()

    # Get this week's activity (Mon-Sun)
    now = datetime.now(UTC)
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    prev_week_start = week_start - timedelta(days=7)

    current_activities = await repo.get_history(user.id, week_start, now)
    previous_activities = await repo.get_history(user.id, prev_week_start, week_start - timedelta(days=1))

    current_metrics = aggregate_weekly_metrics(current_activities)
    previous_metrics = aggregate_weekly_metrics(previous_activities)

    data_driven = is_data_sufficient(current_metrics)

    # Comparison
    comparison = compute_week_comparison(current_metrics, previous_metrics)

    # Inflection detection
    inflection = detect_strategy_inflection(current_metrics, previous_metrics)
    inflection_warning = inflection.pivot_suggestion if inflection else None

    # Build state for agent
    agent_state = {
        "current_metrics": current_metrics.model_dump(),
        "previous_metrics": previous_metrics.model_dump(),
        "data_driven": data_driven,
    }
    if inflection_warning:
        agent_state["inflection_warning"] = inflection_warning

    # Call the WeeklyReviewAgent
    from src.agents.weekly_review import weekly_review_agent
    try:
        result = await weekly_review_agent(
            agent_state,
            {"configurable": {"user_id": str(user.id)}},
        )
    except Exception:
        logger.warning("weekly_review_agent_failed", user_id=str(user.id))
        result = {
            "summary": "Unable to generate review at this time.",
            "tactical_adjustments": ["Continue applying consistently", "Focus on quality over quantity"],
            "next_week_goals": ["Submit 5 applications", "Network with 2 contacts", "Practice 1 mock interview"],
            "encouragement": "Every step forward counts. Keep going!",
        }

    return WeeklyReviewResponse(
        metrics=WeeklyMetricsResponse(
            applications_count=current_metrics.applications_count,
            interviews_count=current_metrics.interviews_count,
            responses_count=current_metrics.responses_count,
            xp_earned=current_metrics.xp_earned,
            action_breakdown=current_metrics.action_breakdown,
        ),
        comparison_to_last_week=comparison.model_dump() if data_driven else None,
        tactical_adjustments=result.get("tactical_adjustments", []),
        next_week_goals=result.get("next_week_goals", []),
        inflection_warning=inflection_warning,
        data_driven=data_driven,
        encouragement=result.get("encouragement", "Keep going!"),
    )


@router.get("/morale", response_model=MoraleDashboardResponse)
async def get_morale_dashboard(
    user: User = Depends(get_current_user),
) -> MoraleDashboardResponse:
    """Return morale dashboard with 4 indicators, burnout warning, and intervention."""
    from src.services.morale_service import MoraleService

    repo = UserActivityRepository()
    service = MoraleService(user_activity_repo=repo)

    # Compute morale indicators
    morale = await service.compute_morale(user.id)

    # Run burnout detection
    burnout = await service.detect_burnout(user.id)
    burnout_warning = None
    if burnout.has_warning:
        burnout_warning = BurnoutWarningResponse(
            signals=[s.signal_type for s in burnout.signals],
            recommendation=burnout.recommendation,
            severity=burnout.overall_severity,
        )

    # Run intervention check
    intervention = await service.check_intervention_needed(user.id)
    intervention_resp = None
    if intervention:
        intervention_resp = InterventionResponse(
            triggered_indicators=intervention.triggered_indicators,
            consecutive_negative_days=intervention.consecutive_negative_days,
            recommendations=intervention.recommendations,
            rest_suggestion=intervention.rest_suggestion,
        )

    return MoraleDashboardResponse(
        response_rate_trend=morale.response_rate_trend,
        ghosting_frequency=morale.ghosting_frequency,
        ghosting_percentage=morale.ghosting_percentage,
        interview_conversion_rate=morale.interview_conversion_rate,
        time_since_last_positive_signal=morale.time_since_last_positive_signal,
        burnout_warning=burnout_warning,
        intervention=intervention_resp,
    )


@router.post("/roi-predict", response_model=ROIPredictResponse)
async def predict_application_roi(
    request: ROIPredictRequest,
    user: User = Depends(get_current_user),
) -> ROIPredictResponse:
    """Predict ROI (probability of hearing back) for a job application."""
    if not request.job_id and not request.jd_text:
        raise HTTPException(status_code=422, detail="At least one of job_id or jd_text is required")

    from src.services.effort_per_chance_engine import EffortPerChanceEngine

    repo = UserActivityRepository()
    engine = EffortPerChanceEngine(user_activity_repo=repo)

    # Defaults — in a full implementation these would come from DB lookups
    company_apps = 0
    company_responses = 0
    seniority_level = "mid"
    skill_overlap_pct = None
    days_since_posted = 7

    # If job_id provided, attempt to load job details
    if request.job_id:
        from src.repositories.job_repository import JobRepository
        from beanie import PydanticObjectId

        job_repo = JobRepository()
        try:
            job = await job_repo.find_by_id(PydanticObjectId(request.job_id))
            if job:
                seniority_level = getattr(job, "seniority_level", "mid") or "mid"
                posted_date = getattr(job, "posted_date", None)
                if posted_date:
                    days_since_posted = (datetime.now(UTC) - posted_date).days
        except Exception:
            pass  # Fall through to defaults

    # Get user's total application history for personalization
    all_activities = await repo.get_history(
        user.id,
        datetime.now(UTC) - timedelta(days=365),
        datetime.now(UTC),
    )
    total_apps = 0
    total_responses = 0
    for activity in all_activities:
        for action in activity.actions:
            if action.action_type == "application_submitted":
                total_apps += 1
            elif action.action_type == "mock_interview_completed":
                total_responses += 1

    prediction = engine.predict(
        company_apps=company_apps,
        company_responses=company_responses,
        seniority_level=seniority_level,
        skill_overlap_pct=skill_overlap_pct,
        days_since_posted=days_since_posted,
        total_user_apps=total_apps,
        total_user_responses=total_responses,
    )

    return ROIPredictResponse(
        probability_of_response=prediction.probability_of_response,
        classification=prediction.classification,
        contributing_factors=ROIContributingFactorsResponse(
            company_response_rate=prediction.contributing_factors.company_response_rate,
            role_competition_level=prediction.contributing_factors.role_competition_level,
            user_fit_score=prediction.contributing_factors.user_fit_score,
            submission_timing=prediction.contributing_factors.submission_timing,
        ),
        personalized=prediction.personalized,
        confidence=prediction.confidence,
    )


@router.post("/schedule", response_model=WeeklyScheduleResponse)
async def generate_schedule(
    request: ScheduleRequest,
    user: User = Depends(get_current_user),
) -> WeeklyScheduleResponse:
    """Generate a personalized weekly rhythm schedule."""
    from src.services.batch_and_breathe_scheduler import BatchAndBreatheScheduler
    from src.services.morale_service import MoraleService

    repo = UserActivityRepository()
    morale_svc = MoraleService(user_activity_repo=repo)
    scheduler = BatchAndBreatheScheduler(morale_service=morale_svc)

    # Detect locale from user profile if available
    locale = getattr(user, "locale", None)

    schedule = await scheduler.generate_schedule(
        user_id=user.id,
        daily_app_limit=request.daily_app_limit,
        available_hours_per_day=request.available_hours_per_day,
        preferred_rest_days=request.preferred_rest_days,
        locale=locale,
    )

    return WeeklyScheduleResponse(
        days=[
            DailyScheduleResponse(
                day=day.day,
                blocks=[
                    TimeBlockResponse(
                        activity_type=b.activity_type,
                        start_time=b.start_time,
                        duration_minutes=b.duration_minutes,
                        description=b.description,
                    )
                    for b in day.blocks
                ],
                is_rest_day=day.is_rest_day,
            )
            for day in schedule.days
        ],
        season_boost=schedule.season_boost,
        burnout_adjusted=schedule.burnout_adjusted,
        notes=schedule.notes,
    )
