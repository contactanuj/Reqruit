"""
Application success tracker — records post-submission outcomes for analytics.

Separate from the Application document (which tracks pipeline state).
ApplicationSuccessTracker captures what happened after submission: employer
views, responses, interview scheduling, offers, rejections, or ghosting.
Optimized for analytics queries with dedicated indexes.
"""

from datetime import datetime

from beanie import Indexed, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument
from src.db.documents.enums import OutcomeStatus


class ApplicationSuccessTracker(TimestampedDocument):
    """
    Outcome tracking for a submitted application.

    Fields:
        user_id: The applicant (owner-scoped).
        application_id: Reference to the Application document (unique per tracker).
        outcome_status: Current outcome status.
        outcome_transitions: Timestamped history of status changes.
        resume_version_used: Version number of the resume used (from Application).
        cover_letter_version: Version number of the cover letter used.
        submission_method: How the application was submitted (e.g., "linkedin", "email").
        resume_strategy: Tailoring strategy used for the resume.
        cover_letter_strategy: Strategy used for the cover letter.
        submitted_at: When the application was submitted.
        last_updated: Last time this tracker was modified.
    """

    user_id: Indexed(PydanticObjectId)
    application_id: Indexed(PydanticObjectId, unique=True)
    outcome_status: OutcomeStatus = OutcomeStatus.APPLIED
    outcome_transitions: list[dict] = []
    resume_version_used: int | None = None
    cover_letter_version: int | None = None
    submission_method: str = ""
    resume_strategy: str = ""
    cover_letter_strategy: str = ""
    submitted_at: datetime | None = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "application_success_trackers"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("outcome_status", ASCENDING)],
                name="user_outcome_status_idx",
            ),
        ]
