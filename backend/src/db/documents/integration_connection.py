"""
IntegrationConnection document — OAuth integration state for email/calendar providers.

Each document represents a single user-provider connection (e.g., user X connected
to Gmail). OAuth tokens are stored encrypted (AES-256-GCM) — the repository layer
handles encryption/decryption. Raw tokens never appear in this document's fields.
"""

from datetime import datetime
from enum import StrEnum

from beanie import PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class IntegrationProvider(StrEnum):
    """Supported third-party integration providers."""

    GMAIL = "gmail"
    OUTLOOK = "outlook"
    GOOGLE_CALENDAR = "google_calendar"
    MICROSOFT_CALENDAR = "microsoft_calendar"


class IntegrationStatus(StrEnum):
    """Lifecycle status of an integration connection."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    TOKEN_EXPIRED = "token_expired"
    REVOKED = "revoked"


class IntegrationConnection(TimestampedDocument):
    """
    Stores a user's OAuth connection to an external provider.

    Tokens are stored as encrypted bytes — only the repository layer
    decrypts them at the point of making API calls. The compound unique
    index on (user_id, provider) ensures one connection per provider per user.
    """

    user_id: PydanticObjectId
    provider: IntegrationProvider
    oauth_token_encrypted: bytes
    refresh_token_encrypted: bytes
    token_expires_at: datetime
    scopes: list[str] = Field(default_factory=list)
    connected_at: datetime
    last_synced_at: datetime | None = None
    sync_cursor: str | None = None
    status: IntegrationStatus = IntegrationStatus.CONNECTED

    class Settings:
        name = "integration_connections"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("provider", ASCENDING)],
                unique=True,
            ),
            IndexModel(
                [("status", ASCENDING), ("token_expires_at", ASCENDING)],
            ),
        ]
