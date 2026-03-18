"""
Outreach message routes (Stage 3: Apply — networking).

Endpoints for generating AI-crafted outreach messages, listing/retrieving
messages, editing drafts, and marking messages as sent.
"""

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel

from datetime import UTC, datetime

from src.api.dependencies import (
    get_application_repository,
    get_contact_repository,
    get_current_user,
    get_job_repository,
    get_outreach_message_repository,
)
from src.agents.outreach import OutreachComposer
from src.core.exceptions import BusinessValidationError, NotFoundError
from src.db.documents.enums import MessageType
from src.db.documents.outreach_message import OutreachMessage
from src.db.documents.user import User
from src.repositories.application_repository import ApplicationRepository
from src.repositories.contact_repository import ContactRepository
from src.repositories.job_repository import JobRepository
from src.repositories.outreach_repository import OutreachMessageRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/outreach", tags=["outreach"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class GenerateOutreachRequest(BaseModel):
    application_id: str
    contact_id: str
    message_type: MessageType = MessageType.GENERIC


class OutreachMessageResponse(BaseModel):
    id: str
    user_id: str
    application_id: str
    contact_id: str
    message_type: str
    content: str
    is_sent: bool
    sent_at: str | None
    created_at: str | None
    updated_at: str | None


class UpdateOutreachRequest(BaseModel):
    content: str | None = None
    message_type: MessageType | None = None


class MarkSentResponse(BaseModel):
    id: str
    is_sent: bool
    sent_at: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _message_to_response(msg: OutreachMessage) -> OutreachMessageResponse:
    return OutreachMessageResponse(
        id=str(msg.id),
        user_id=str(msg.user_id),
        application_id=str(msg.application_id),
        contact_id=str(msg.contact_id),
        message_type=msg.message_type,
        content=msg.content,
        is_sent=msg.is_sent,
        sent_at=msg.sent_at.isoformat() if msg.sent_at else None,
        created_at=msg.created_at.isoformat() if msg.created_at else None,
        updated_at=msg.updated_at.isoformat() if msg.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/generate", status_code=201, response_model=OutreachMessageResponse)
async def generate_outreach(
    body: GenerateOutreachRequest,
    current_user: User = Depends(get_current_user),
    outreach_repo: OutreachMessageRepository = Depends(get_outreach_message_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    contact_repo: ContactRepository = Depends(get_contact_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> OutreachMessageResponse:
    """Generate an AI outreach draft for a contact linked to an application."""
    application = await app_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(body.application_id)
    )
    if not application:
        raise NotFoundError("Application", body.application_id)

    contact = await contact_repo.get_by_id(PydanticObjectId(body.contact_id))
    if not contact:
        raise NotFoundError("Contact", body.contact_id)

    job = await job_repo.get_by_id(application.job_id)
    company_name = job.company_name if job else "Unknown"
    role_title = job.title if job else "Unknown"
    job_description = job.description if job else ""

    agent = OutreachComposer()
    config = {"configurable": {"user_id": str(current_user.id)}}
    result = await agent(
        {
            "role_title": role_title,
            "company_name": company_name,
            "contact_name": contact.name,
            "contact_role": contact.role,
            "message_type": body.message_type.value,
            "job_description": job_description,
        },
        config,
    )

    message = OutreachMessage(
        user_id=current_user.id,
        application_id=PydanticObjectId(body.application_id),
        contact_id=PydanticObjectId(body.contact_id),
        message_type=body.message_type,
        content=result["content"],
    )
    message = await outreach_repo.create(message)

    logger.info(
        "outreach_message_generated",
        user_id=str(current_user.id),
        message_id=str(message.id),
        contact_name=contact.name,
    )
    return _message_to_response(message)


@router.get("", response_model=list[OutreachMessageResponse])
async def list_outreach_messages(
    application_id: str | None = Query(None),
    contact_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    outreach_repo: OutreachMessageRepository = Depends(get_outreach_message_repository),
) -> list[OutreachMessageResponse]:
    """List outreach messages, optionally filtered by application_id or contact_id."""
    if application_id:
        messages = await outreach_repo.get_for_application(
            current_user.id, PydanticObjectId(application_id), skip=skip, limit=limit
        )
    elif contact_id:
        messages = await outreach_repo.find_many(
            {"user_id": current_user.id, "contact_id": PydanticObjectId(contact_id)},
            skip=skip,
            limit=limit,
            sort="-created_at",
        )
    else:
        messages = await outreach_repo.get_for_user(
            current_user.id, skip=skip, limit=limit
        )
    return [_message_to_response(m) for m in messages]


@router.get("/{message_id}", response_model=OutreachMessageResponse)
async def get_outreach_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    outreach_repo: OutreachMessageRepository = Depends(get_outreach_message_repository),
) -> OutreachMessageResponse:
    """Get a single outreach message by ID."""
    message = await outreach_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(message_id)
    )
    if not message:
        raise NotFoundError("OutreachMessage", message_id)
    return _message_to_response(message)


@router.patch("/{message_id}", response_model=OutreachMessageResponse)
async def update_outreach_message(
    message_id: str,
    body: UpdateOutreachRequest,
    current_user: User = Depends(get_current_user),
    outreach_repo: OutreachMessageRepository = Depends(get_outreach_message_repository),
) -> OutreachMessageResponse:
    """Edit an outreach message draft."""
    message = await outreach_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(message_id)
    )
    if not message:
        raise NotFoundError("OutreachMessage", message_id)

    update_data: dict = {}
    if body.content is not None:
        update_data["content"] = body.content
    if body.message_type is not None:
        update_data["message_type"] = body.message_type

    if update_data:
        update_data["updated_at"] = datetime.now(UTC)
        updated = await outreach_repo.update(PydanticObjectId(message_id), update_data)
        message = updated or message

    logger.info(
        "outreach_message_updated",
        user_id=str(current_user.id),
        message_id=message_id,
    )
    return _message_to_response(message)


@router.post("/{message_id}/send", response_model=MarkSentResponse)
async def mark_as_sent(
    message_id: str,
    current_user: User = Depends(get_current_user),
    outreach_repo: OutreachMessageRepository = Depends(get_outreach_message_repository),
) -> MarkSentResponse:
    """Mark an outreach message as sent."""
    message = await outreach_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(message_id)
    )
    if not message:
        raise NotFoundError("OutreachMessage", message_id)

    if message.is_sent:
        raise BusinessValidationError(
            "Message has already been sent.", error_code="ALREADY_SENT"
        )

    now = datetime.now(UTC)
    await outreach_repo.update(
        PydanticObjectId(message_id),
        {"is_sent": True, "sent_at": now},
    )

    logger.info(
        "outreach_message_sent",
        user_id=str(current_user.id),
        message_id=message_id,
    )
    return MarkSentResponse(
        id=message_id,
        is_sent=True,
        sent_at=now.isoformat(),
    )


@router.delete("/{message_id}", status_code=204)
async def delete_outreach_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    outreach_repo: OutreachMessageRepository = Depends(get_outreach_message_repository),
) -> Response:
    """Delete an outreach message."""
    message = await outreach_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(message_id)
    )
    if not message:
        raise NotFoundError("OutreachMessage", message_id)

    await outreach_repo.delete(PydanticObjectId(message_id))
    logger.info(
        "outreach_message_deleted",
        user_id=str(current_user.id),
        message_id=message_id,
    )
    return Response(status_code=204)
