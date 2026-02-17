"""
Application document model — tracks a job application through the pipeline.

An Application connects a User to a Job and tracks the status as it moves
through the pipeline: Saved -> Applied -> Interviewing -> Offered -> Accepted.
This is the core entity in the Track workflow (Stage 5).

Design decisions
----------------
Why a separate collection (not embedded in Job or User):
    Applications have their own lifecycle, status transitions, and metadata
    (match_score, applied_at, notes). They reference both User and Job,
    forming the many-to-many relationship at the center of the data model.

    Embedding in User would mean loading all applications every time we
    fetch the user. Embedding in Job would lose the user association.
    A separate collection is the correct choice for a join entity.

Why match_score as a float (not an int):
    The JobMatcher agent produces a 0.0-100.0 similarity score based on
    profile-to-job matching. Storing as float preserves the agent's precision
    for ranking. The UI can round for display.

Why compound index on (user_id, status):
    The most common dashboard query is "show me all applications with status X
    for this user." A compound index serves both "all applications for user"
    and "all applications with status Y for user" efficiently.
"""

from datetime import datetime

from beanie import Indexed, PydanticObjectId
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument
from src.db.documents.enums import ApplicationStatus


class Application(TimestampedDocument):
    """
    Job application pipeline entry.

    Fields:
        user_id: The applicant.
        job_id: The target job listing.
        status: Current pipeline stage (default: saved).
        match_score: 0.0-100.0 similarity score from JobMatcher agent.
        match_reasoning: Brief explanation of why this score was given.
        applied_at: Timestamp when the user actually applied (not when saved).
        notes: User's personal notes about this application.
    """

    user_id: Indexed(PydanticObjectId)
    job_id: PydanticObjectId
    status: ApplicationStatus = ApplicationStatus.SAVED
    match_score: float | None = None
    match_reasoning: str = ""
    applied_at: datetime | None = None
    notes: str = ""

    class Settings:
        name = "applications"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("status", ASCENDING)],
                name="user_status_idx",
            ),
            IndexModel(
                [("job_id", ASCENDING)],
                name="job_idx",
            ),
        ]
