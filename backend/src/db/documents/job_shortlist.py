"""
JobShortlist document — daily curated job recommendations for each user.

Each shortlist contains 3-5 matched jobs with fit scores, ROI predictions,
and match reasons. Shortlists have a 30-day TTL via MongoDB TTL index.
ShortlistJob is an embedded model for individual job entries.
"""

from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class ShortlistJob(BaseModel):
    """A single job entry in a daily shortlist."""

    job_id: PydanticObjectId | None = None
    source: str = ""
    source_url: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    fit_score: float = 0.0
    roi_prediction: str = ""
    trust_score: float | None = None
    salary_range: str = ""
    match_reasons: list[str] = Field(default_factory=list)


class DiscoveryPreferences(BaseModel):
    """User's job discovery preferences."""

    roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    salary_min: int = 0
    salary_max: int = 0
    company_sizes: list[str] = Field(default_factory=list)
    remote_only: bool = False


class JobShortlist(TimestampedDocument):
    """
    Daily curated job shortlist for a user.

    Fields:
        user_id: The user this shortlist belongs to.
        date: Date this shortlist is for (normalized to midnight).
        jobs: List of matched jobs with scores.
        generation_cost_usd: LLM cost for generating this shortlist.
        preferences_snapshot: User preferences at generation time.
    """

    user_id: PydanticObjectId
    date: datetime
    jobs: list[ShortlistJob] = Field(default_factory=list)
    generation_cost_usd: float = 0.0
    preferences_snapshot: dict = Field(default_factory=dict)

    class Settings:
        name = "job_shortlists"
        indexes = [
            IndexModel(
                [(("user_id", ASCENDING)), ("date", DESCENDING)],
            ),
            IndexModel(
                [("date", ASCENDING)],
                expireAfterSeconds=2592000,  # 30-day TTL
            ),
        ]
