"""
Integration routes — OAuth connection, disconnection, and status endpoints.

Routes:
    POST /integrations/gmail/connect      — Generate OAuth consent URL
    POST /integrations/gmail/callback     — Exchange code for tokens
    DELETE /integrations/gmail            — Disconnect Gmail integration
    POST /integrations/calendar/connect   — Generate Calendar OAuth consent URL
    POST /integrations/calendar/callback  — Exchange code for tokens
    DELETE /integrations/calendar         — Disconnect Calendar integration
    GET  /integrations/status             — List all integration statuses
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_user, get_integration_service
from src.db.documents.integration_connection import IntegrationProvider
from src.db.documents.user import User
from src.services.integration_service import IntegrationService

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ── Request / response schemas ────────────────────────────────────────


class ConnectResponse(BaseModel):
    redirect_url: str
    state: str


class CallbackRequest(BaseModel):
    code: str
    state: str


class CallbackResponse(BaseModel):
    provider: str
    status: str
    connected_at: datetime | None = None


class DisconnectRequest(BaseModel):
    purge: bool = False


class IntegrationStatusResponse(BaseModel):
    provider: str
    status: str
    connected_at: datetime | None = None
    last_synced_at: datetime | None = None
    scopes: list[str] = []


# ── Routes ────────────────────────────────────────────────────────────


@router.post("/gmail/connect", response_model=ConnectResponse)
async def gmail_connect(
    user: User = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service),
):
    """Generate a Google OAuth authorization URL for Gmail connection."""
    result = service.initiate_connection(user.id, IntegrationProvider.GMAIL)
    return ConnectResponse(**result)


@router.post("/gmail/callback", response_model=CallbackResponse, status_code=201)
async def gmail_callback(
    body: CallbackRequest,
    user: User = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service),
):
    """Complete the Gmail OAuth flow by exchanging the authorization code."""
    connection = await service.complete_connection(
        user_id=user.id,
        provider=IntegrationProvider.GMAIL,
        code=body.code,
        state=body.state,
    )
    return CallbackResponse(
        provider=connection.provider.value
        if hasattr(connection.provider, "value")
        else str(connection.provider),
        status=connection.status.value
        if hasattr(connection.status, "value")
        else str(connection.status),
        connected_at=connection.connected_at,
    )


@router.delete("/gmail", status_code=204)
async def gmail_disconnect(
    purge: bool = False,
    user: User = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service),
):
    """Disconnect the Gmail integration and optionally purge signals."""
    await service.disconnect(
        user_id=user.id,
        provider=IntegrationProvider.GMAIL,
        purge=purge,
    )


@router.post("/calendar/connect", response_model=ConnectResponse)
async def calendar_connect(
    user: User = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service),
):
    """Generate a Google OAuth authorization URL for Calendar connection."""
    result = service.initiate_connection(user.id, IntegrationProvider.GOOGLE_CALENDAR)
    return ConnectResponse(**result)


@router.post("/calendar/callback", response_model=CallbackResponse, status_code=201)
async def calendar_callback(
    body: CallbackRequest,
    user: User = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service),
):
    """Complete the Calendar OAuth flow by exchanging the authorization code."""
    connection = await service.complete_connection(
        user_id=user.id,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        code=body.code,
        state=body.state,
    )
    return CallbackResponse(
        provider=connection.provider.value
        if hasattr(connection.provider, "value")
        else str(connection.provider),
        status=connection.status.value
        if hasattr(connection.status, "value")
        else str(connection.status),
        connected_at=connection.connected_at,
    )


@router.delete("/calendar", status_code=204)
async def calendar_disconnect(
    purge: bool = False,
    user: User = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service),
):
    """Disconnect the Calendar integration and optionally purge signals."""
    await service.disconnect(
        user_id=user.id,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        purge=purge,
    )


@router.get("/status", response_model=list[IntegrationStatusResponse])
async def integration_status(
    user: User = Depends(get_current_user),
    service: IntegrationService = Depends(get_integration_service),
):
    """List all integration connections and their statuses."""
    statuses = await service.get_all_statuses(user.id)
    return [IntegrationStatusResponse(**s.model_dump()) for s in statuses]
