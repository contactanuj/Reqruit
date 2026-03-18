"""Effort-Per-Chance Engine — deterministic ROI prediction for job applications.

All calculations are deterministic (no LLM). Probability is a weighted sum of
4 signal factors. Personalization is calibrated from user's historical data.
"""

from enum import StrEnum

import structlog
from beanie import PydanticObjectId
from pydantic import BaseModel

from src.repositories.user_activity_repository import UserActivityRepository

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Classification thresholds (percentage)
HIGH_ROI_THRESHOLD = 40
WORTH_A_SHOT_THRESHOLD = 15

# Factor weights (sum to 1.0)
WEIGHT_COMPANY_RESPONSE = 0.30
WEIGHT_ROLE_COMPETITION = 0.20
WEIGHT_USER_FIT = 0.35
WEIGHT_SUBMISSION_TIMING = 0.15

# Personalization tiers
FULL_PERSONALIZATION_THRESHOLD = 50
PARTIAL_PERSONALIZATION_THRESHOLD = 10

# Default general market response rate
DEFAULT_RESPONSE_RATE = 0.15


# ---------------------------------------------------------------------------
# Enums and models
# ---------------------------------------------------------------------------


class Classification(StrEnum):
    HIGH_ROI = "HIGH_ROI"
    WORTH_A_SHOT = "WORTH_A_SHOT"
    SKIP_IT = "SKIP_IT"


class ContributingFactors(BaseModel):
    company_response_rate: float
    role_competition_level: float
    user_fit_score: float
    submission_timing: float


class CalibrationResult(BaseModel):
    personalized: bool
    confidence: str  # high, medium, low
    calibration_multiplier: float
    tracked_applications: int


class ROIPrediction(BaseModel):
    probability_of_response: float  # 0-100
    classification: str
    contributing_factors: ContributingFactors
    personalized: bool
    confidence: str


# ---------------------------------------------------------------------------
# Factor scoring functions
# ---------------------------------------------------------------------------


def score_company_response_rate(
    company_history_responses: int, company_history_applications: int
) -> float:
    """Historical response rate from user's past applications to this company.

    Returns 0.0 to 1.0. Uses default market rate if no history.
    """
    if company_history_applications == 0:
        return DEFAULT_RESPONSE_RATE
    return min(company_history_responses / company_history_applications, 1.0)


def score_role_competition(seniority_level: str) -> float:
    """Estimate competition level based on role seniority.

    Junior/popular = high competition = lower score.
    Senior/niche = low competition = higher score.
    Returns 0.0 to 1.0.
    """
    level_map = {
        "intern": 0.2,
        "junior": 0.3,
        "entry": 0.3,
        "mid": 0.5,
        "senior": 0.7,
        "staff": 0.8,
        "principal": 0.85,
        "lead": 0.75,
        "manager": 0.65,
        "director": 0.8,
        "vp": 0.85,
        "c-level": 0.9,
    }
    return level_map.get(seniority_level.lower(), 0.5)


def score_user_fit(skill_overlap_pct: float | None) -> float:
    """Compute user fit score from skill overlap percentage.

    If no SkillsProfile / no JD decoded, returns default 0.5.
    skill_overlap_pct is 0.0 to 1.0.
    """
    if skill_overlap_pct is None:
        return 0.5
    return max(0.0, min(skill_overlap_pct, 1.0))


def score_submission_timing(days_since_posted: int) -> float:
    """Score based on how recently the job was posted.

    0-3 days = 1.0, 4-7 = 0.7, 8-14 = 0.4, 15+ = 0.2.
    """
    if days_since_posted <= 3:
        return 1.0
    elif days_since_posted <= 7:
        return 0.7
    elif days_since_posted <= 14:
        return 0.4
    return 0.2


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------


def calculate_probability(factors: ContributingFactors) -> float:
    """Weighted sum of all factors, scaled to 0-100%."""
    raw = (
        factors.company_response_rate * WEIGHT_COMPANY_RESPONSE
        + factors.role_competition_level * WEIGHT_ROLE_COMPETITION
        + factors.user_fit_score * WEIGHT_USER_FIT
        + factors.submission_timing * WEIGHT_SUBMISSION_TIMING
    )
    return round(min(raw * 100, 100.0), 1)


def classify(probability: float) -> str:
    """Classify based on probability thresholds."""
    if probability > HIGH_ROI_THRESHOLD:
        return Classification.HIGH_ROI
    elif probability >= WORTH_A_SHOT_THRESHOLD:
        return Classification.WORTH_A_SHOT
    return Classification.SKIP_IT


# ---------------------------------------------------------------------------
# Personalization
# ---------------------------------------------------------------------------


def get_historical_calibration(
    total_applications: int, total_responses: int
) -> CalibrationResult:
    """Compute calibration from user's historical data."""
    if total_applications < PARTIAL_PERSONALIZATION_THRESHOLD:
        return CalibrationResult(
            personalized=False,
            confidence="low",
            calibration_multiplier=1.0,
            tracked_applications=total_applications,
        )

    personal_rate = total_responses / total_applications if total_applications > 0 else 0
    general_rate = DEFAULT_RESPONSE_RATE

    if total_applications >= FULL_PERSONALIZATION_THRESHOLD:
        # Full personalization
        multiplier = personal_rate / general_rate if general_rate > 0 else 1.0
        return CalibrationResult(
            personalized=True,
            confidence="high",
            calibration_multiplier=max(0.1, min(multiplier, 3.0)),  # clamp
            tracked_applications=total_applications,
        )

    # Partial personalization (10-49 apps): blend personal with general
    blend_weight = total_applications / FULL_PERSONALIZATION_THRESHOLD
    blended_rate = personal_rate * blend_weight + general_rate * (1 - blend_weight)
    multiplier = blended_rate / general_rate if general_rate > 0 else 1.0

    return CalibrationResult(
        personalized=True,
        confidence="medium",
        calibration_multiplier=max(0.1, min(multiplier, 3.0)),
        tracked_applications=total_applications,
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class EffortPerChanceEngine:
    """Deterministic ROI prediction engine for job applications."""

    def __init__(
        self,
        user_activity_repo: UserActivityRepository,
    ) -> None:
        self._activity_repo = user_activity_repo

    def predict(
        self,
        company_apps: int,
        company_responses: int,
        seniority_level: str,
        skill_overlap_pct: float | None,
        days_since_posted: int,
        total_user_apps: int,
        total_user_responses: int,
    ) -> ROIPrediction:
        """Compute ROI prediction from contributing factors."""
        factors = ContributingFactors(
            company_response_rate=score_company_response_rate(company_responses, company_apps),
            role_competition_level=score_role_competition(seniority_level),
            user_fit_score=score_user_fit(skill_overlap_pct),
            submission_timing=score_submission_timing(days_since_posted),
        )

        base_probability = calculate_probability(factors)

        # Apply personalization calibration
        calibration = get_historical_calibration(total_user_apps, total_user_responses)
        adjusted_probability = round(
            min(base_probability * calibration.calibration_multiplier, 100.0), 1
        )

        return ROIPrediction(
            probability_of_response=adjusted_probability,
            classification=classify(adjusted_probability),
            contributing_factors=factors,
            personalized=calibration.personalized,
            confidence=calibration.confidence,
        )
