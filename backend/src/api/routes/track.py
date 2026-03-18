"""
Application pipeline tracking routes (Stage 5: Track).

Design decisions
----------------
Why state machine validation at the route level:
    Invalid status transitions (e.g., ACCEPTED -> APPLIED) represent business
    logic errors, not data validation errors. Catching them at the route level
    with BusinessValidationError returns a clean 422 with INVALID_STATUS_TRANSITION
    error_code. The frontend can handle this specifically (e.g., show "Can't move
    an accepted offer back to applied").

Why /track/kanban returns all applications at once:
    A personal job tracker rarely has more than 50-100 active applications.
    Returning all grouped data in one call is simpler and faster for the
    frontend than 7 separate status-filtered requests. MongoDB can handle
    500 documents in a single query trivially.

Why notes are updated separately from status:
    Notes are free-form text that users write independently of status
    transitions. Combining them into a single PATCH would require the
    client to always send both, risking accidental overwrites of notes
    when updating status. Separate endpoints prevent this.
"""

from datetime import UTC, datetime

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
    get_job_repository,
)
from src.core.exceptions import BusinessValidationError, NotFoundError
from src.db.documents.enums import ApplicationStatus
from src.db.documents.user import User
from src.repositories.application_repository import ApplicationRepository
from src.repositories.job_repository import JobRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/track", tags=["track"])

# ---------------------------------------------------------------------------
# Status classification
# ---------------------------------------------------------------------------

TERMINAL_STATUSES = (
    ApplicationStatus.ACCEPTED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
)

ACTIVE_STATUSES = (
    ApplicationStatus.SAVED,
    ApplicationStatus.APPLIED,
    ApplicationStatus.INTERVIEWING,
    ApplicationStatus.OFFERED,
)

# ---------------------------------------------------------------------------
# State machine: valid transitions
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.SAVED: {ApplicationStatus.APPLIED, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.APPLIED: {
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEWING: {
        ApplicationStatus.OFFERED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFERED: {
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.ACCEPTED: set(),   # terminal
    ApplicationStatus.REJECTED: set(),   # terminal
    ApplicationStatus.WITHDRAWN: set(),  # terminal
}

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class KanbanItem(BaseModel):
    application_id: str
    job_id: str
    job_title: str
    company_name: str
    status: str
    applied_at: str | None
    notes: str
    created_at: str | None


class UpdateStatusRequest(BaseModel):
    status: ApplicationStatus


class UpdateNotesRequest(BaseModel):
    notes: str


class StatusTransitionResponse(BaseModel):
    application_id: str
    old_status: str
    new_status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/kanban")
async def get_kanban(
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> dict:
    """
    Return all applications grouped by status for the kanban board.
    Single DB call pattern: fetch all applications, batch-load jobs.
    """
    applications = await app_repo.get_kanban(
        current_user.id, exclude_statuses=list(TERMINAL_STATUSES)
    )
    if not applications:
        return {s.value: [] for s in ACTIVE_STATUSES}

    job_ids = [app.job_id for app in applications]
    jobs = await job_repo.find_by_ids(job_ids)
    job_map = {str(j.id): j for j in jobs}

    kanban: dict[str, list] = {s.value: [] for s in ACTIVE_STATUSES}
    for app in applications:
        job = job_map.get(str(app.job_id))
        item = KanbanItem(
            application_id=str(app.id),
            job_id=str(app.job_id),
            job_title=job.title if job else "Unknown",
            company_name=job.company_name if job else "Unknown",
            status=app.status,
            applied_at=app.applied_at.isoformat() if app.applied_at else None,
            notes=app.notes,
            created_at=app.created_at.isoformat() if app.created_at else None,
        )
        if app.status in kanban:
            kanban[app.status].append(item.model_dump())

    return kanban


@router.get("/applications", response_model=list[KanbanItem])
async def list_applications(
    status: ApplicationStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> list[KanbanItem]:
    """List applications with optional status filter. Two-query pattern (no N+1)."""
    applications = await app_repo.get_for_user(
        current_user.id, skip=skip, limit=limit, status=status
    )
    if not applications:
        return []

    jobs = await job_repo.find_by_ids([app.job_id for app in applications])
    job_map = {str(j.id): j for j in jobs}

    return [
        KanbanItem(
            application_id=str(app.id),
            job_id=str(app.job_id),
            job_title=job_map[str(app.job_id)].title
            if str(app.job_id) in job_map
            else "Unknown",
            company_name=job_map[str(app.job_id)].company_name
            if str(app.job_id) in job_map
            else "Unknown",
            status=app.status,
            applied_at=app.applied_at.isoformat() if app.applied_at else None,
            notes=app.notes,
            created_at=app.created_at.isoformat() if app.created_at else None,
        )
        for app in applications
    ]


@router.get("/applications/archive", response_model=list[KanbanItem])
async def get_archive(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> list[KanbanItem]:
    """List archived (terminal-status) applications, paginated, newest first."""
    applications = await app_repo.get_for_user_by_statuses(
        current_user.id, statuses=list(TERMINAL_STATUSES), skip=skip, limit=limit
    )
    if not applications:
        return []

    jobs = await job_repo.find_by_ids([app.job_id for app in applications])
    job_map = {str(j.id): j for j in jobs}

    return [
        KanbanItem(
            application_id=str(app.id),
            job_id=str(app.job_id),
            job_title=job_map[str(app.job_id)].title
            if str(app.job_id) in job_map
            else "Unknown",
            company_name=job_map[str(app.job_id)].company_name
            if str(app.job_id) in job_map
            else "Unknown",
            status=app.status,
            applied_at=app.applied_at.isoformat() if app.applied_at else None,
            notes=app.notes,
            created_at=app.created_at.isoformat() if app.created_at else None,
        )
        for app in applications
    ]


@router.patch(
    "/applications/{application_id}/status",
    response_model=StatusTransitionResponse,
)
async def update_application_status(
    application_id: str,
    body: UpdateStatusRequest,
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
) -> StatusTransitionResponse:
    """
    Transition an application to a new status.
    Validates the transition is legal (e.g., can't go ACCEPTED -> APPLIED).
    """
    application = await app_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(application_id)
    )
    if not application:
        raise NotFoundError("Application", application_id)

    old_status = ApplicationStatus(application.status)
    new_status = body.status

    if new_status not in _VALID_TRANSITIONS.get(old_status, set()):
        raise BusinessValidationError(
            f"Cannot transition from {old_status} to {new_status}",
            error_code="INVALID_STATUS_TRANSITION",
        )

    update_data: dict = {"status": new_status}
    if new_status == ApplicationStatus.APPLIED and not application.applied_at:
        update_data["applied_at"] = datetime.now(UTC)

    await app_repo.update(application.id, update_data)
    logger.info(
        "application_status_updated",
        user_id=str(current_user.id),
        application_id=application_id,
        old_status=old_status,
        new_status=new_status,
    )
    return StatusTransitionResponse(
        application_id=application_id,
        old_status=old_status,
        new_status=new_status,
    )


@router.patch("/applications/{application_id}/notes")
async def update_application_notes(
    application_id: str,
    body: UpdateNotesRequest,
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
) -> dict:
    """Update personal notes on an application."""
    application = await app_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(application_id)
    )
    if not application:
        raise NotFoundError("Application", application_id)

    await app_repo.update(application.id, {"notes": body.notes})
    return {"application_id": application_id, "notes": body.notes}
