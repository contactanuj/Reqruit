"""
OnboardingPlan document — 30-60-90 day onboarding plans for new hires.

Each user can have one active onboarding plan. Milestones are organized
into three phases: Days 1-30 (Learn & Listen), Days 31-60 (Contribute),
Days 61-90 (Lead Initiatives).
"""

from datetime import datetime

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from src.db.base_document import TimestampedDocument


class Milestone(BaseModel):
    """A single milestone within a 30-60-90 day plan."""

    title: str
    target_day: int  # 1-90
    description: str = ""
    completed: bool = False
    completed_at: datetime | None = None


class RelationshipTarget(BaseModel):
    """A key person to meet during onboarding."""

    role: str
    description: str
    conversation_starters: list[str] = Field(default_factory=list)
    optimal_timing: str = ""  # e.g., "Week 1", "Week 2-3"


class JoiningPrepItem(BaseModel):
    """A locale-specific joining preparation item."""

    category: str
    title: str
    description: str = ""
    checklist: list[str] = Field(default_factory=list)
    locale_specific: bool = True


class OnboardingPlan(TimestampedDocument):
    """
    30-60-90 day onboarding plan for a user.

    Fields:
        user_id: The user this plan belongs to.
        company_name: Target company name.
        role_title: The role the user is onboarding into.
        start_date: When the user starts.
        milestones: List of milestones organized across the 90-day period.
        progress_pct: Percentage of milestones completed (0.0-100.0).
        coaching_session_count: Number of coaching sessions conducted.
        skill_gaps: Identified skill gaps with learning actions.
        jd_text: Raw job description text (optional).
    """

    user_id: Indexed(PydanticObjectId)
    company_name: str
    role_title: str = ""
    start_date: datetime | None = None
    milestones: list[Milestone] = Field(default_factory=list)
    progress_pct: float = 0.0
    coaching_session_count: int = 0
    skill_gaps: list[dict] = Field(default_factory=list)
    jd_text: str | None = None
    relationship_targets: list[RelationshipTarget] = Field(default_factory=list)
    joining_prep: list[JoiningPrepItem] = Field(default_factory=list)
    locale: str = ""

    class Settings:
        name = "onboarding_plans"
