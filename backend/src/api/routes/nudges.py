"""
Nudge routes — smart reminders for application follow-ups and ghost detection.

Routes:
    GET   /nudges          — List pending nudges for current user
    GET   /nudges/count    — Count of pending nudges (for badge display)
    PATCH /nudges/{id}/seen      — Mark a nudge as seen
    PATCH /nudges/{id}/dismiss   — Dismiss a nudge
    PATCH /nudges/{id}/acted-on  — Mark a nudge as acted upon
"""

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_user, get_nudge_repository
from src.core.exceptions import NotFoundError
from src.db.documents.user import User
from src.repositories.nudge_repository import NudgeRepository

router = APIRouter(prefix="/nudges", tags=["nudges"])


# ── Response schemas ─────────────────────────────────────────────────


class NudgeResponse(BaseModel):
    id: str
    application_id: str
    nudge_type: str
    status: str
    title: str
    message: str
    suggested_actions: list[str]
    trigger_date: str | None = None


class NudgeCountResponse(BaseModel):
    count: int


# ── Routes ───────────────────────────────────────────────────────────


@router.get("", response_model=list[NudgeResponse])
async def list_nudges(
    user: User = Depends(get_current_user),
    repo: NudgeRepository = Depends(get_nudge_repository),
):
    """List pending nudges for the current user."""
    nudges = await repo.get_pending_by_user(user.id)
    return [
        NudgeResponse(
            id=str(nudge.id),
            application_id=str(nudge.application_id),
            nudge_type=nudge.nudge_type,
            status=nudge.status,
            title=nudge.title,
            message=nudge.message,
            suggested_actions=nudge.suggested_actions,
            trigger_date=nudge.trigger_date.isoformat() if nudge.trigger_date else None,
        )
        for nudge in nudges
    ]


@router.get("/count", response_model=NudgeCountResponse)
async def nudge_count(
    user: User = Depends(get_current_user),
    repo: NudgeRepository = Depends(get_nudge_repository),
):
    """Return count of pending nudges for badge display."""
    count = await repo.count_pending_by_user(user.id)
    return NudgeCountResponse(count=count)


@router.patch("/{nudge_id}/seen", response_model=NudgeResponse)
async def mark_seen(
    nudge_id: PydanticObjectId,
    user: User = Depends(get_current_user),
    repo: NudgeRepository = Depends(get_nudge_repository),
):
    """Mark a nudge as seen."""
    nudge = await repo.find_by_id(nudge_id)
    if nudge is None or nudge.user_id != user.id:
        raise NotFoundError("Nudge")
    nudge = await repo.mark_seen(nudge_id)
    return NudgeResponse(
        id=str(nudge.id),
        application_id=str(nudge.application_id),
        nudge_type=nudge.nudge_type,
        status=nudge.status,
        title=nudge.title,
        message=nudge.message,
        suggested_actions=nudge.suggested_actions,
        trigger_date=nudge.trigger_date.isoformat() if nudge.trigger_date else None,
    )


@router.patch("/{nudge_id}/dismiss", response_model=NudgeResponse)
async def dismiss_nudge(
    nudge_id: PydanticObjectId,
    user: User = Depends(get_current_user),
    repo: NudgeRepository = Depends(get_nudge_repository),
):
    """Dismiss a nudge."""
    nudge = await repo.find_by_id(nudge_id)
    if nudge is None or nudge.user_id != user.id:
        raise NotFoundError("Nudge")
    nudge = await repo.mark_dismissed(nudge_id)
    return NudgeResponse(
        id=str(nudge.id),
        application_id=str(nudge.application_id),
        nudge_type=nudge.nudge_type,
        status=nudge.status,
        title=nudge.title,
        message=nudge.message,
        suggested_actions=nudge.suggested_actions,
        trigger_date=nudge.trigger_date.isoformat() if nudge.trigger_date else None,
    )


@router.patch("/{nudge_id}/acted-on", response_model=NudgeResponse)
async def acted_on_nudge(
    nudge_id: PydanticObjectId,
    user: User = Depends(get_current_user),
    repo: NudgeRepository = Depends(get_nudge_repository),
):
    """Mark a nudge as acted upon."""
    nudge = await repo.find_by_id(nudge_id)
    if nudge is None or nudge.user_id != user.id:
        raise NotFoundError("Nudge")
    nudge = await repo.mark_acted_on(nudge_id)
    return NudgeResponse(
        id=str(nudge.id),
        application_id=str(nudge.application_id),
        nudge_type=nudge.nudge_type,
        status=nudge.status,
        title=nudge.title,
        message=nudge.message,
        suggested_actions=nudge.suggested_actions,
        trigger_date=nudge.trigger_date.isoformat() if nudge.trigger_date else None,
    )
