"""
EmailSignal document — job-related signals extracted from email metadata.

Each signal represents a detected event (interview invitation, rejection, offer, etc.)
parsed from email subject lines and sender domains. Full email body content is NEVER
stored (NFR-6.9). The unique compound index on (user_id, message_id) ensures
idempotent processing — the same email cannot produce duplicate signals.
"""

from datetime import datetime

from beanie import PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.db.base_document import TimestampedDocument
from src.db.documents.integration_connection import IntegrationProvider


class EmailSignal(TimestampedDocument):
    """
    A job-related signal detected from email metadata.

    Fields:
        user_id: The user this signal belongs to.
        provider: Integration provider the email came from.
        message_id: Provider-specific message ID (Gmail message ID) for dedup.
        sender_domain: Domain of the email sender.
        matched_pattern: Type of signal detected (interview_invitation, rejection, etc.).
        event_date: Extracted date from the email subject, if present.
        company_name: Company name extracted from sender domain.
        confidence: Confidence score (0.0-1.0) of the pattern match.
        application_id: Linked application, if matched by company name.
        source: Origin of the signal — "integration" (auto-detected) or "user-reported".
    """

    user_id: PydanticObjectId
    provider: IntegrationProvider
    message_id: str
    sender_domain: str
    matched_pattern: str
    event_date: datetime | None = None
    company_name: str = ""
    confidence: float = 0.0
    application_id: PydanticObjectId | None = None
    source: str = Field(default="integration")

    class Settings:
        name = "email_signals"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("message_id", ASCENDING)],
                unique=True,
            ),
            IndexModel(
                [("user_id", ASCENDING), ("matched_pattern", ASCENDING)],
            ),
            IndexModel(
                [("user_id", ASCENDING), ("created_at", DESCENDING)],
            ),
        ]
