"""
Trust verification models — TrustScore, RiskCategory, RiskSignal, posting analysis.
"""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskCategory(StrEnum):
    VERIFIED = "VERIFIED"
    LIKELY_SAFE = "LIKELY_SAFE"
    UNCERTAIN = "UNCERTAIN"
    SUSPICIOUS = "SUSPICIOUS"
    SCAM_LIKELY = "SCAM_LIKELY"


class RiskSignal(BaseModel):
    signal_type: str
    description: str
    severity: str = "medium"  # low, medium, high


class TrustScore(BaseModel):
    company_verification_score: float = 0.0
    recruiter_verification_score: float = 0.0
    posting_freshness_score: float = 0.0
    red_flag_count: int = 0
    overall_trust_score: float = 0.0
    risk_category: str = RiskCategory.UNCERTAIN
    risk_signals: list[RiskSignal] = Field(default_factory=list)
    warning_badge: bool = False
    computed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class RedFlag(BaseModel):
    category: str
    severity: str  # HIGH_RISK, MEDIUM_RISK, LOW_RISK
    explanation: str


class FreshnessScore(BaseModel):
    score: float = 100.0  # 0-100
    days_since_posted: int = 0
    repost_frequency: int = 0  # placeholder
    similar_postings_count: int = 0  # placeholder
    staleness_flag: bool = False


class ReviewQueueItem(BaseModel):
    report_id: str
    entity_type: str
    entity_identifier: str
    report_count: int = 0
    evidence_summary: list[dict] = Field(default_factory=list)
    risk_categories: list[str] = Field(default_factory=list)
    warning_badge_applied: bool = False
    created_at: datetime | None = None


class TrendingScamPattern(BaseModel):
    pattern_type: str
    region: str = "GLOBAL"
    affected_companies: list[str] = Field(default_factory=list)
    report_count: int = 0
    example_signals: list[str] = Field(default_factory=list)


class HiringStage(StrEnum):
    APPLICATION = "application"
    PHONE_SCREEN = "phone_screen"
    ONSITE = "onsite"
    OFFER = "offer"
    POST_OFFER = "post_offer"


class CommunicationRiskFlag(BaseModel):
    behavior: str
    severity: str  # HIGH, MEDIUM, LOW
    explanation: str
    recommended_action: str


class PIIAssessment(BaseModel):
    hiring_stage: str
    jurisdiction: str
    appropriate_pii: list[str] = Field(default_factory=list)
    inappropriate_pii: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


class LivenessSignal(BaseModel):
    signal_name: str
    signal_value: float
    weight: float
    description: str


class ChecklistItem(BaseModel):
    check: str
    description: str
    severity: str  # critical, important, informational


class ChecklistCategory(BaseModel):
    category_name: str
    items: list[ChecklistItem] = Field(default_factory=list)


class DeepfakeChecklist(BaseModel):
    categories: list[ChecklistCategory] = Field(default_factory=list)
    last_updated: str = "2026-03-16"


class RecoveryStep(BaseModel):
    step_number: int
    action: str
    details: str
    urgency: str  # immediate, within_24h, within_week, ongoing
    url: str | None = None


class RecoveryPlan(BaseModel):
    scam_type: str
    jurisdiction: str
    immediate_actions: list[RecoveryStep] = Field(default_factory=list)
    complaint_filing: list[RecoveryStep] = Field(default_factory=list)
    monitoring_steps: list[RecoveryStep] = Field(default_factory=list)
    platform_flagging: list[RecoveryStep] = Field(default_factory=list)
    additional_recommendations: list[str] = Field(default_factory=list)
