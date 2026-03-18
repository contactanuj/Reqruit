"""
Locale tools routes: regional resume guidance, scam detection, visa navigation,
and cultural coaching.

These endpoints provide locale-aware tools that leverage both rule-based
services and LLM agents. All require JWT auth.

Endpoints
---------
    POST /locale/tools/resume-review      — Regional resume formatting guidance
    POST /locale/tools/scam-check         — Job posting scam analysis
    POST /locale/tools/visa-check         — Visa eligibility comparison
    POST /locale/tools/cultural-prep      — Culture-calibrated interview prep
"""

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_user, get_locale_service, get_market_config_repository
from src.core.exceptions import BusinessValidationError, NotFoundError
from src.db.documents.user import User
from src.repositories.market_config_repository import MarketConfigRepository
from src.services.locale_service import LocaleService
from src.services.scam_detection_service import ScamDetectionService

logger = structlog.get_logger()

router = APIRouter(prefix="/locale/tools", tags=["locale-tools"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ResumeReviewRequest(BaseModel):
    """Request for regional resume review."""

    resume_content: str
    target_market: str = "US"


class ScamCheckRequest(BaseModel):
    """Request for scam analysis of a job posting."""

    title: str = ""
    description: str = ""
    company_name: str = ""
    company_email: str = ""
    salary_min: float = 0
    salary_max: float = 0
    contact_method: str = ""


class VisaCheckRequest(BaseModel):
    """Request for visa eligibility comparison."""

    nationality: str
    target_market: str
    visa_type: str = ""
    qualifications: list[str] = []
    years_experience: int = 0


class CulturalPrepRequest(BaseModel):
    """Request for cultural interview preparation."""

    target_market: str
    role_type: str = ""
    interview_stage: str = ""
    specific_concerns: str = ""


# ---------------------------------------------------------------------------
# Resume review endpoint
# ---------------------------------------------------------------------------


@router.post("/resume-review")
async def review_resume_for_market(
    body: ResumeReviewRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> dict:
    """Get market-specific resume formatting guidance."""
    if not body.resume_content.strip():
        raise BusinessValidationError(
            detail="resume_content must not be empty",
            error_code="INVALID_RESUME_CONTENT",
        )

    config = await market_repo.get_by_region(body.target_market.upper())
    if not config:
        raise NotFoundError(f"MarketConfig for region '{body.target_market}'")

    return {
        "target_market": body.target_market.upper(),
        "resume_conventions": config.resume_conventions.model_dump(),
        "cultural_context": config.cultural.model_dump(),
        "guidance_note": (
            "Use the resume conventions and cultural context above to format "
            "your resume for this market. Key points are highlighted in the conventions."
        ),
    }


# ---------------------------------------------------------------------------
# Scam check endpoint
# ---------------------------------------------------------------------------


@router.post("/scam-check")
async def check_for_scam(
    body: ScamCheckRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Analyze a job posting for scam red flags."""
    if not body.title and not body.description:
        raise BusinessValidationError(
            detail="At least title or description must be provided",
            error_code="INVALID_JOB_DATA",
        )

    service = ScamDetectionService()
    result = service.analyze(body.model_dump())
    return result


# ---------------------------------------------------------------------------
# Visa check endpoint
# ---------------------------------------------------------------------------


@router.post("/visa-check")
async def check_visa_eligibility(
    body: VisaCheckRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> dict:
    """Get visa information for a target market."""
    config = await market_repo.get_by_region(body.target_market.upper())
    if not config:
        raise NotFoundError(f"MarketConfig for region '{body.target_market}'")

    return {
        "target_market": body.target_market.upper(),
        "nationality": body.nationality.upper(),
        "visa_requirements": config.legal.visa_requirements,
        "non_compete_enforceable": config.legal.non_compete_enforceable,
        "worker_protections": config.legal.worker_protections,
    }


# ---------------------------------------------------------------------------
# Cultural prep endpoint
# ---------------------------------------------------------------------------


@router.post("/cultural-prep")
async def get_cultural_prep(
    body: CulturalPrepRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> dict:
    """Get culture-calibrated interview preparation guidance."""
    config = await market_repo.get_by_region(body.target_market.upper())
    if not config:
        raise NotFoundError(f"MarketConfig for region '{body.target_market}'")

    return {
        "target_market": body.target_market.upper(),
        "cultural_context": config.cultural.model_dump(),
        "hiring_process": config.hiring_process.model_dump(),
        "interview_style": config.cultural.interview_style,
        "formality_level": config.cultural.formality_level,
        "languages": config.cultural.languages,
    }
