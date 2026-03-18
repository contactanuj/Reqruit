"""
CalendarSignal document — interview events detected from calendar entries.

Each signal represents a detected interview event parsed from calendar data.
Non-interview events are never stored (privacy preservation). The unique
compound index on (user_id, event_id) ensures idempotent processing.
"""

from datetime import datetime

from beanie import PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument
from src.db.documents.integration_connection import IntegrationProvider


class CalendarSignal(TimestampedDocument):
    """
    An interview event detected from a connected calendar.

    Fields:
        user_id: The user this signal belongs to.
        provider: Integration provider (GOOGLE_CALENDAR, MICROSOFT_CALENDAR).
        event_id: Provider-specific event ID for dedup.
        company_name: Company name matched from organizer/attendee domains.
        matched_pattern: Always "calendar_interview" for now.
        event_date: Scheduled date/time of the interview.
        confidence: Confidence score (0.0-1.0) of the match.
        application_id: Linked application, if matched by company name.
        nudge_eligible: True if event is 3+ days in the future.
    """

    user_id: PydanticObjectId
    provider: IntegrationProvider
    event_id: str
    company_name: str = ""
    matched_pattern: str = "calendar_interview"
    event_date: datetime | None = None
    confidence: float = 0.0
    application_id: PydanticObjectId | None = None
    nudge_eligible: bool = Field(default=False)

    class Settings:
        name = "calendar_signals"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("event_id", ASCENDING)],
                unique=True,
            ),
            IndexModel(
                [("user_id", ASCENDING), ("event_date", ASCENDING)],
            ),
        ]
