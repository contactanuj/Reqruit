"""
CareerVitals document — career health metrics and drift detection snapshots.

Stores periodic career health assessments with six core metrics:
skill relevance, market demand, compensation alignment, growth trajectory,
network strength, and job satisfaction.
"""

from datetime import datetime

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from src.db.base_document import TimestampedDocument


class HealthMetric(BaseModel):
    """A single career health metric with score and explanation."""

    name: str
    score: float = 0.0  # 0-100
    trend: str = "stable"  # improving, stable, declining
    explanation: str = ""


class DriftIndicator(BaseModel):
    """An indicator that the user's career is drifting from their goals."""

    category: str  # skill_gap, market_shift, compensation, stagnation
    severity: str = "low"  # low, medium, high
    description: str = ""
    recommended_action: str = ""


class CareerVitals(TimestampedDocument):
    """
    Career health assessment snapshot for a user.

    Each assessment captures six health metrics and any detected drift
    indicators. Assessments are generated periodically or on-demand.
    """

    user_id: Indexed(PydanticObjectId)
    assessment_date: datetime | None = None
    overall_score: float = 0.0  # 0-100 composite score
    metrics: list[HealthMetric] = Field(default_factory=list)
    drift_indicators: list[DriftIndicator] = Field(default_factory=list)
    career_stage: str = ""  # early, mid, senior, executive
    industry: str = ""
    role_title: str = ""
    years_experience: float = 0.0
    locale: str = ""

    class Settings:
        name = "career_vitals"
