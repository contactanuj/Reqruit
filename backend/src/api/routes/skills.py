"""
Skills routes: profile CRUD, JD decoding, and fit scoring.

These endpoints power the Professional Identity Engine (Phase 1).
All require JWT auth.
"""

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.agents.fit_scorer import FitScorer
from src.agents.jd_decoder import JDDecoder
from src.api.dependencies import get_current_user, get_skills_profile_repository
from src.core.exceptions import NotFoundError
from src.db.documents.skills_profile import Achievement, FitScore, Skill, SkillsProfile
from src.db.documents.user import User
from src.repositories.skills_profile_repository import SkillsProfileRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/skills", tags=["skills"])


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class SkillCreate(BaseModel):
    """Add a skill to the profile."""

    name: str
    category: str = ""
    proficiency: str = "INTERMEDIATE"
    years_experience: float = 0.0
    last_used: str = ""


class AchievementCreate(BaseModel):
    """Add an achievement to the profile."""

    title: str
    description: str = ""
    impact: str = ""
    skills_demonstrated: list[str] = []
    context: str = ""


class JDDecodeRequest(BaseModel):
    """Request to decode a job description."""

    job_description: str


class FitScoreRequest(BaseModel):
    """Request to score candidate-job fit."""

    job_description: str
    jd_analysis: dict | None = None


# ---------------------------------------------------------------------------
# Skills Profile CRUD
# ---------------------------------------------------------------------------


@router.get("/profile")
async def get_skills_profile(
    user: User = Depends(get_current_user),  # noqa: B008
    repo: SkillsProfileRepository = Depends(get_skills_profile_repository),  # noqa: B008
) -> dict:
    """Get the current user's skills profile."""
    profile = await repo.get_by_user(user.id)
    if not profile:
        raise NotFoundError("Skills profile")
    return profile.model_dump(by_alias=True)


@router.post("/profile", status_code=201)
async def create_skills_profile(
    user: User = Depends(get_current_user),  # noqa: B008
    repo: SkillsProfileRepository = Depends(get_skills_profile_repository),  # noqa: B008
) -> dict:
    """Create an empty skills profile for the current user."""
    existing = await repo.get_by_user(user.id)
    if existing:
        return existing.model_dump(by_alias=True)

    profile = SkillsProfile(user_id=user.id)
    created = await repo.create(profile)
    logger.info("skills_profile_created", user_id=str(user.id))
    return created.model_dump(by_alias=True)


@router.post("/profile/skills")
async def add_skill(
    body: SkillCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    repo: SkillsProfileRepository = Depends(get_skills_profile_repository),  # noqa: B008
) -> dict:
    """Add a skill to the user's profile."""
    profile = await repo.get_by_user(user.id)
    if not profile:
        raise NotFoundError("Skills profile")

    skill = Skill(
        name=body.name,
        category=body.category,
        proficiency=body.proficiency,
        years_experience=body.years_experience,
        last_used=body.last_used,
        source="manual",
    )
    profile.skills.append(skill)
    await repo.update(profile.id, {"skills": [s.model_dump() for s in profile.skills]})
    logger.info("skill_added", user_id=str(user.id), skill=body.name)
    return {"skill": skill.model_dump(), "total_skills": len(profile.skills)}


@router.post("/profile/achievements")
async def add_achievement(
    body: AchievementCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    repo: SkillsProfileRepository = Depends(get_skills_profile_repository),  # noqa: B008
) -> dict:
    """Add an achievement to the user's profile."""
    profile = await repo.get_by_user(user.id)
    if not profile:
        raise NotFoundError("Skills profile")

    achievement = Achievement(
        title=body.title,
        description=body.description,
        impact=body.impact,
        skills_demonstrated=body.skills_demonstrated,
        context=body.context,
        source="manual",
    )
    profile.achievements.append(achievement)
    await repo.update(
        profile.id,
        {"achievements": [a.model_dump() for a in profile.achievements]},
    )
    logger.info("achievement_added", user_id=str(user.id), title=body.title)
    return {"achievement": achievement.model_dump(), "total_achievements": len(profile.achievements)}


@router.delete("/profile")
async def delete_skills_profile(
    user: User = Depends(get_current_user),  # noqa: B008
    repo: SkillsProfileRepository = Depends(get_skills_profile_repository),  # noqa: B008
) -> dict:
    """Delete the user's skills profile."""
    profile = await repo.get_by_user(user.id)
    if not profile:
        raise NotFoundError("Skills profile")

    await repo.delete(profile.id)
    logger.info("skills_profile_deleted", user_id=str(user.id))
    return {"deleted": True}


# ---------------------------------------------------------------------------
# JD Decode endpoint
# ---------------------------------------------------------------------------


@router.post("/jd/decode")
async def decode_job_description(
    body: JDDecodeRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Decode a job description into structured requirements (no LLM — returns input for agent)."""
    decoder = JDDecoder()
    result = await decoder({"job_description": body.job_description})
    return result


# ---------------------------------------------------------------------------
# Fit Score endpoint
# ---------------------------------------------------------------------------


@router.post("/fit-score")
async def compute_fit_score(
    body: FitScoreRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    repo: SkillsProfileRepository = Depends(get_skills_profile_repository),  # noqa: B008
) -> dict:
    """Compute candidate-job fit score using skills profile and JD."""
    profile = await repo.get_by_user(user.id)
    if not profile:
        raise NotFoundError("Skills profile")

    skills_data = {
        "skills": [s.model_dump() for s in profile.skills],
        "achievements": [a.model_dump() for a in profile.achievements],
        "summary": profile.summary,
    }

    scorer = FitScorer()
    result = await scorer({
        "skills_profile": skills_data,
        "job_description": body.job_description,
        "jd_analysis": body.jd_analysis or "",
    })
    return result
