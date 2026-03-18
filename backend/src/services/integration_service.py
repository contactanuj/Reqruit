"""
Integration lifecycle service — connect, disconnect, and status for OAuth providers.

Orchestrates the OAuth flow: CSRF state generation/validation, token exchange
via provider clients, encrypted storage via the repository, and sync dispatch
via Celery. Tokens are never logged in plaintext.
"""

import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta

import structlog
from beanie import PydanticObjectId
from pydantic import BaseModel

from src.core.exceptions import BusinessValidationError, ConflictError, NotFoundError
from src.db.documents.integration_connection import (
    IntegrationProvider,
    IntegrationStatus,
)
from src.integrations.gmail_client import GmailClient
from src.integrations.google_calendar_client import GoogleCalendarClient
from src.repositories.calendar_signal_repository import CalendarSignalRepository
from src.repositories.email_signal_repository import EmailSignalRepository
from src.repositories.integration_connection_repository import (
    IntegrationConnectionRepository,
)

logger = structlog.get_logger()

STATE_TTL_SECONDS = 300  # 5 minutes


class IntegrationStatusResponse(BaseModel):
    """Sanitized integration status — never exposes token data."""

    provider: str
    status: str
    connected_at: datetime | None = None
    last_synced_at: datetime | None = None
    scopes: list[str] = []


class IntegrationService:
    """Manages OAuth connection lifecycle for all integration providers."""

    def __init__(
        self,
        repo: IntegrationConnectionRepository,
        gmail_client: GmailClient,
        encryption_key: bytes,
        signal_repo: EmailSignalRepository | None = None,
        calendar_client: GoogleCalendarClient | None = None,
        calendar_signal_repo: CalendarSignalRepository | None = None,
    ) -> None:
        self._repo = repo
        self._gmail_client = gmail_client
        self._signing_key = hashlib.sha256(b"csrf-signing:" + encryption_key).digest()
        self._signal_repo = signal_repo
        self._calendar_client = calendar_client
        self._calendar_signal_repo = calendar_signal_repo

    def initiate_connection(
        self, user_id: PydanticObjectId, provider: IntegrationProvider
    ) -> dict:
        """Generate OAuth authorization URL with CSRF state for the provider."""
        logger.info(
            "integration_initiating",
            user_id=str(user_id),
            provider=provider.value,
        )
        state = self._generate_state(user_id)
        if provider == IntegrationProvider.GMAIL:
            auth_url = self._gmail_client.generate_auth_url(state)
        elif provider == IntegrationProvider.GOOGLE_CALENDAR:
            if self._calendar_client is None:
                raise BusinessValidationError(
                    detail="Calendar client not configured"
                )
            auth_url = self._calendar_client.generate_auth_url(state)
        else:
            raise BusinessValidationError(
                detail=f"Provider {provider.value} not supported for connection"
            )
        return {"redirect_url": auth_url, "state": state}

    async def complete_connection(
        self,
        user_id: PydanticObjectId,
        provider: IntegrationProvider,
        code: str,
        state: str,
    ):
        """Validate CSRF state, exchange code for tokens, store encrypted connection."""
        if not self.validate_csrf_state(state, user_id):
            raise BusinessValidationError(
                detail="Invalid or expired OAuth state parameter"
            )

        existing = await self._repo.get_by_user_provider(user_id, provider)
        if existing and existing.status == IntegrationStatus.CONNECTED:
            raise ConflictError(detail=f"Provider {provider.value} already connected")

        logger.info(
            "integration_completing",
            user_id=str(user_id),
            provider=provider.value,
            oauth_token="[ENCRYPTED]",
        )

        if provider == IntegrationProvider.GMAIL:
            token_response = await self._gmail_client.exchange_code(code)
        elif provider == IntegrationProvider.GOOGLE_CALENDAR:
            if self._calendar_client is None:
                raise BusinessValidationError(
                    detail="Calendar client not configured"
                )
            token_response = await self._calendar_client.exchange_code(code)
        else:
            raise BusinessValidationError(
                detail=f"Provider {provider.value} not supported"
            )

        expires_at = datetime.now(UTC) + timedelta(seconds=token_response.expires_in)
        scopes = token_response.scope.split(" ") if token_response.scope else []

        if existing:
            # Reconnecting — update existing record
            connection = await self._repo.update_tokens(
                existing.id,
                token_response.access_token,
                token_response.refresh_token or "",
                expires_at,
            )
        else:
            connection = await self._repo.create_connection(
                user_id=user_id,
                provider=provider,
                oauth_token=token_response.access_token,
                refresh_token=token_response.refresh_token or "",
                token_expires_at=expires_at,
                scopes=scopes,
            )

        logger.info(
            "integration_connected",
            user_id=str(user_id),
            provider=provider.value,
        )
        return connection

    async def disconnect(
        self,
        user_id: PydanticObjectId,
        provider: IntegrationProvider,
        purge: bool = False,
    ) -> None:
        """Disconnect an integration: revoke token, purge tokens, optionally purge signals."""
        connection = await self._repo.get_by_user_provider(user_id, provider)
        if connection is None:
            raise NotFoundError("IntegrationConnection")

        logger.info(
            "integration_disconnecting",
            user_id=str(user_id),
            provider=provider.value,
            purge=purge,
        )

        # Best-effort token revocation at the provider
        if connection.status == IntegrationStatus.CONNECTED:
            try:
                oauth_token, _ = self._repo.decrypt_tokens(connection)
                if provider == IntegrationProvider.GMAIL:
                    await self._gmail_client.revoke_token(oauth_token)
                elif provider == IntegrationProvider.GOOGLE_CALENDAR and self._calendar_client:
                    await self._calendar_client.revoke_token(oauth_token)
            except Exception:
                logger.warning(
                    "integration_revoke_failed",
                    user_id=str(user_id),
                    provider=provider.value,
                )

        # Always purge tokens on disconnect
        await self._repo.disconnect(connection.id, purge_tokens=True)

        # Handle email signals: purge or re-attribute
        if self._signal_repo is not None:
            if purge:
                deleted = await self._signal_repo.delete_by_user_and_provider(
                    user_id, provider
                )
                logger.info(
                    "integration_signals_purged",
                    user_id=str(user_id),
                    provider=provider.value,
                    deleted_count=deleted,
                )
            else:
                updated = await self._signal_repo.update_source_to_user_reported(
                    user_id, provider
                )
                logger.info(
                    "integration_signals_reattributed",
                    user_id=str(user_id),
                    provider=provider.value,
                    updated_count=updated,
                )

        # Handle calendar signals: purge on disconnect
        if self._calendar_signal_repo is not None and purge:
            deleted = await self._calendar_signal_repo.delete_by_user_and_provider(
                user_id, provider
            )
            logger.info(
                "integration_calendar_signals_purged",
                user_id=str(user_id),
                provider=provider.value,
                deleted_count=deleted,
            )

        logger.info(
            "integration_disconnected",
            user_id=str(user_id),
            provider=provider.value,
            purge=purge,
        )

    async def get_all_statuses(
        self, user_id: PydanticObjectId
    ) -> list[IntegrationStatusResponse]:
        """Return sanitized status for all integrations — no token data exposed."""
        connections = await self._repo.get_all_by_user(user_id)
        return [
            IntegrationStatusResponse(
                provider=conn.provider.value,
                status=conn.status.value,
                connected_at=conn.connected_at,
                last_synced_at=conn.last_synced_at,
                scopes=conn.scopes,
            )
            for conn in connections
        ]

    async def link_signal_to_application(
        self,
        signal_id: PydanticObjectId,
        application_id: PydanticObjectId,
    ) -> None:
        """Link an email signal to a tracked application."""
        if self._signal_repo is None:
            raise BusinessValidationError(
                detail="Signal repository not configured"
            )
        signal = await self._signal_repo.get_by_id(signal_id)
        if signal is None:
            raise NotFoundError("EmailSignal")
        await self._signal_repo.update(signal_id, {"application_id": application_id})
        logger.info(
            "signal_linked_to_application",
            signal_id=str(signal_id),
            application_id=str(application_id),
        )

    async def get_signals_for_user(
        self,
        user_id: PydanticObjectId,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """Return email signals for a user."""
        if self._signal_repo is None:
            return []
        return await self._signal_repo.get_by_user(user_id, limit=limit, offset=offset)

    def _generate_state(self, user_id: PydanticObjectId) -> str:
        """Generate a signed CSRF state token with user binding and expiry."""
        payload = json.dumps({
            "user_id": str(user_id),
            "exp": time.time() + STATE_TTL_SECONDS,
            "nonce": secrets.token_hex(8),
        })
        encoded = urlsafe_b64encode(payload.encode()).decode()
        signature = hmac.new(
            self._signing_key, encoded.encode(), hashlib.sha256
        ).hexdigest()
        return f"{encoded}.{signature}"

    def validate_csrf_state(
        self, state: str, user_id: PydanticObjectId
    ) -> bool:
        """Verify state token: signature, user binding, and expiry."""
        try:
            parts = state.split(".")
            if len(parts) != 2:
                return False
            encoded, signature = parts
            expected_sig = hmac.new(
                self._signing_key, encoded.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_sig):
                return False
            payload = json.loads(urlsafe_b64decode(encoded).decode())
            if payload.get("user_id") != str(user_id):
                return False
            return not payload.get("exp", 0) < time.time()
        except Exception:
            return False
