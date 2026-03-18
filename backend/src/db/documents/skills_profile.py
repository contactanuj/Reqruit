"""
Skills profile document model — user's professional skills and achievements.

The SkillsProfile is the core of the Professional Identity Engine (Phase 1).
It aggregates skills extracted from resumes, achievements mined from work
history, and proficiency assessments from the SkillsAnalyst agent.

Design decisions
----------------
Why a separate collection (not embedded in User):
    SkillsProfile can grow large — a senior engineer might have 50+ skills
    and 20+ achievements with detailed descriptions. Embedding this in the
    User document would bloat every user read (auth, middleware, etc.) with
    data that's only needed during skills-related operations.

    The Profile document follows the same pattern — it's a separate collection
    referenced by user_id, not embedded in User.

Why user_id is unique-indexed:
    Each user has exactly one skills profile. The unique index prevents
    accidental duplicates and enables fast lookup by user_id.

Why skills and achievements are embedded lists (not separate collections):
    Skills and achievements have no independent lifecycle — they're always
    accessed and modified through the parent SkillsProfile. A user will
    never query "all achievements across all users." Embedding avoids
    unnecessary joins and follows MongoDB's access-pattern-driven design.

Why source tracking on Skill and Achievement:
    Skills can come from multiple sources: resume parsing, achievement mining,
    manual entry, or inference. Tracking the source helps the UI show
    provenance and lets the user prioritize manually-verified entries over
    AI-inferred ones.
"""

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel

from src.db.base_document import TimestampedDocument


# ---------------------------------------------------------------------------
# Embedded models
# ---------------------------------------------------------------------------


class Skill(BaseModel):
    """
    A single skill with proficiency and metadata.

    Proficiency levels follow a standard 4-tier model:
    BEGINNER -> INTERMEDIATE -> ADVANCED -> EXPERT
    """

    name: str
    category: str = ""  # e.g., "Programming Language", "Framework", "Cloud", "Soft Skill"
    proficiency: str = "INTERMEDIATE"  # BEGINNER/INTERMEDIATE/ADVANCED/EXPERT
    years_experience: float = 0.0
    source: str = ""  # "resume", "manual", "mined", "inferred"
    last_used: str = ""  # e.g., "2025"
    confidence: float = 0.0  # AI confidence score 0.0-1.0


class Achievement(BaseModel):
    """
    A quantified professional achievement mined from work history.

    Achievements follow the CAR format: Context, Action, Result.
    The AchievementMiner agent extracts these from resume text and
    work descriptions.
    """

    title: str
    description: str = ""
    impact: str = ""  # quantified result, e.g., "Reduced latency by 40%"
    skills_demonstrated: list[str] = []
    context: str = ""  # role/company where this happened
    source: str = ""  # "resume", "mined", "manual"


class FitScore(BaseModel):
    """
    Job-specific fit assessment comparing user skills against requirements.

    Computed by the FitScorer agent when a user views a job listing.
    Stored on the Job document for quick access without re-computation.
    """

    overall: float = 0.0  # 0-100 composite score
    skills_match: float = 0.0  # 0-100
    experience_match: float = 0.0  # 0-100
    matching_skills: list[str] = []
    missing_skills: list[str] = []
    bonus_skills: list[str] = []  # user has but job didn't ask for
    explanation: str = ""


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class SkillsProfile(TimestampedDocument):
    """
    User's aggregated skills and professional achievements.

    Fields:
        user_id: Reference to the User document. One profile per user.
        skills: Embedded list of skills with proficiency and metadata.
        achievements: Embedded list of professional achievements (CAR format).
        summary: AI-generated narrative summary of the user's skill set.
        analysis_version: Incremented each time the profile is re-analyzed.
    """

    user_id: Indexed(PydanticObjectId, unique=True)
    skills: list[Skill] = []
    achievements: list[Achievement] = []
    summary: str = ""
    analysis_version: int = 0

    class Settings:
        name = "skills_profiles"
