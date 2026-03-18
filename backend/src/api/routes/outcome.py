"""
Application outcome tracking routes.

POST /applications/{id}/outcome — Record outcome status
GET  /applications/outcomes — List user's outcome trackers with filters
"""

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.dependencies import (
    get_current_user,
    get_outcome_service,
    get_success_analytics_service,
)
from src.db.documents.enums import OutcomeStatus
from src.services.outcome_service import OutcomeService
from src.services.success_analytics import AnalyticsSummaryResponse, SuccessAnalyticsService

logger = structlog.get_logger()

router = APIRouter(prefix="/applications", tags=["outcomes"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RecordOutcomeRequest(BaseModel):
    """Request body for recording an application outcome."""

    outcome_status: OutcomeStatus
    submission_method: str | None = None
    resume_strategy: str | None = None
    cover_letter_strategy: str | None = None


class OutcomeTransitionResponse(BaseModel):
    """A single status transition record."""

    previous_status: str | None
    new_status: str
    timestamp: str


class OutcomeResponse(BaseModel):
    """Response for an outcome tracker."""

    id: str
    application_id: str
    outcome_status: str
    outcome_transitions: list[dict]
    resume_version_used: int | None = None
    cover_letter_version: int | None = None
    submission_method: str = ""
    resume_strategy: str = ""
    cover_letter_strategy: str = ""
    submitted_at: str | None = None
    last_updated: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary(
    user=Depends(get_current_user),
    analytics_service: SuccessAnalyticsService = Depends(get_success_analytics_service),
):
    """Get analytics summary of application outcomes."""
    return await analytics_service.get_summary(user.id)


@router.post("/{application_id}/outcome", response_model=OutcomeResponse)
async def record_outcome(
    application_id: PydanticObjectId,
    body: RecordOutcomeRequest,
    user=Depends(get_current_user),
    outcome_service: OutcomeService = Depends(get_outcome_service),
):
    """Record or update an application outcome status."""
    tracker = await outcome_service.create_or_update_tracker(
        user_id=user.id,
        application_id=application_id,
        new_status=body.outcome_status,
        submission_method=body.submission_method,
        resume_strategy=body.resume_strategy,
        cover_letter_strategy=body.cover_letter_strategy,
    )

    return OutcomeResponse(
        id=str(tracker.id),
        application_id=str(tracker.application_id),
        outcome_status=str(tracker.outcome_status),
        outcome_transitions=tracker.outcome_transitions,
        resume_version_used=tracker.resume_version_used,
        cover_letter_version=tracker.cover_letter_version,
        submission_method=tracker.submission_method,
        resume_strategy=tracker.resume_strategy,
        cover_letter_strategy=tracker.cover_letter_strategy,
        submitted_at=tracker.submitted_at.isoformat() if tracker.submitted_at else None,
        last_updated=tracker.last_updated.isoformat(),
    )


@router.get("/outcomes", response_model=list[OutcomeResponse])
async def list_outcomes(
    user=Depends(get_current_user),
    outcome_service: OutcomeService = Depends(get_outcome_service),
    status: OutcomeStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List user's outcome trackers with optional status filter."""
    filters = {}
    if status:
        filters["outcome_status"] = status

    trackers = await outcome_service.list_trackers(
        user_id=user.id,
        filters=filters if filters else None,
        skip=skip,
        limit=limit,
    )

    return [
        OutcomeResponse(
            id=str(t.id),
            application_id=str(t.application_id),
            outcome_status=str(t.outcome_status),
            outcome_transitions=t.outcome_transitions,
            resume_version_used=t.resume_version_used,
            cover_letter_version=t.cover_letter_version,
            submission_method=t.submission_method,
            resume_strategy=t.resume_strategy,
            cover_letter_strategy=t.cover_letter_strategy,
            submitted_at=t.submitted_at.isoformat() if t.submitted_at else None,
            last_updated=t.last_updated.isoformat(),
        )
        for t in trackers
    ]
