"""
Trust verification routes — company and recruiter trust scoring.
"""

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_user, get_scam_report_repository
from src.core.exceptions import NotFoundError
from src.db.documents.user import User
from src.repositories.scam_report_repository import ScamReportRepository
from src.services.trust.damage_control_assistant import DamageControlAssistant
from src.services.trust.deepfake_guide import DeepfakeInterviewGuide
from src.services.trust.ghost_job_sentry import GhostJobSentry
from src.services.trust.models import RiskSignal
from src.services.trust.off_platform_analyzer import OffPlatformAlertAnalyzer
from src.services.trust.pii_gatekeeper import PIIGatekeeper
from src.services.trust.scam_report_service import ScamReportService
from src.services.trust.verification_service import TrustVerificationService

logger = structlog.get_logger()
router = APIRouter(prefix="/trust", tags=["trust"])

# Module-level singleton — stateless, only holds in-memory cache
_verification_service = TrustVerificationService()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class TrustVerifyRequest(BaseModel):
    company_name: str
    company_registration_number: str | None = None
    recruiter_email: str | None = None
    recruiter_linkedin_url: str | None = None
    job_url: str | None = None


class TrustVerifyResponse(BaseModel):
    entity_id: str
    company_verification_score: float
    recruiter_verification_score: float
    posting_freshness_score: float
    red_flag_count: int
    overall_trust_score: float
    risk_category: str
    risk_signals: list[dict]


class JobTrustResponse(BaseModel):
    job_id: str
    company_verification_score: float
    recruiter_verification_score: float
    posting_freshness_score: float
    red_flag_count: int
    overall_trust_score: float
    risk_category: str
    risk_signals: list[dict]


class PostingAnalysisRequest(BaseModel):
    job_title: str
    company_name: str
    jd_text: str
    posted_date: str | None = None
    salary_range: str | None = None
    communication_channel: str | None = None
    locale: str = "US"


class FreshnessScoreResponse(BaseModel):
    score: float
    days_since_posted: int
    repost_frequency: int
    similar_postings_count: int
    staleness_flag: bool


class RedFlagResponse(BaseModel):
    category: str
    severity: str
    explanation: str


class PostingAnalysisResponse(BaseModel):
    freshness: FreshnessScoreResponse
    red_flags: list[RedFlagResponse]
    india_specific_flags: list[RedFlagResponse]
    recommended_actions: list[str]
    overall_risk_level: str


_VALID_ENTITY_TYPES = {"company", "recruiter", "posting"}
_VALID_EVIDENCE_TYPES = {"screenshot", "url", "description"}


class ScamReportRequest(BaseModel):
    entity_type: str
    entity_identifier: str
    evidence_type: str = "description"
    evidence_text: str
    risk_category: str

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        if v not in _VALID_ENTITY_TYPES:
            msg = f"entity_type must be one of: {', '.join(sorted(_VALID_ENTITY_TYPES))}"
            raise ValueError(msg)
        return v

    @field_validator("evidence_type")
    @classmethod
    def validate_evidence_type(cls, v: str) -> str:
        if v not in _VALID_EVIDENCE_TYPES:
            msg = f"evidence_type must be one of: {', '.join(sorted(_VALID_EVIDENCE_TYPES))}"
            raise ValueError(msg)
        return v


class ScamReportResponse(BaseModel):
    id: str
    entity_type: str
    entity_identifier: str
    risk_category: str
    warning_badge_applied: bool


class EntityReportSummary(BaseModel):
    entity_identifier: str
    report_count: int
    risk_categories: list[str]
    warning_badge: bool
    reporters: list[str]


class TrendingScamResponse(BaseModel):
    pattern_type: str
    region: str
    affected_companies: list[str]
    report_count: int
    example_signals: list[str]


class CommunicationAnalysisRequest(BaseModel):
    communication_channel: str = ""
    recruiter_behavior: list[str] = []
    hiring_stage: str = "application"
    pii_requested: list[str] = []
    jurisdiction: str = "US"


class CommunicationRiskFlagResponse(BaseModel):
    behavior: str
    severity: str
    explanation: str
    recommended_action: str


class PIIAssessmentResponse(BaseModel):
    hiring_stage: str
    jurisdiction: str
    appropriate_pii: list[str]
    inappropriate_pii: list[str]
    alerts: list[str]


class CommunicationAnalysisResponse(BaseModel):
    risk_flags: list[CommunicationRiskFlagResponse]
    overall_risk_level: str
    recommended_actions: list[str]
    pii_assessment: PIIAssessmentResponse | None = None


class GhostCheckRequest(BaseModel):
    job_url: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    posted_date: str | None = None

    @field_validator("job_url", mode="after")
    @classmethod
    def validate_has_input(cls, v, info):
        # Validation runs after all fields parsed; check in job_url validator
        # since it's the first optional field
        return v


class LivenessSignalResponse(BaseModel):
    signal_name: str
    signal_value: float
    weight: float
    description: str


class GhostCheckResponse(BaseModel):
    liveness_score: float
    verdict: str
    signals: list[LivenessSignalResponse]
    warning: str | None = None
    recommendation: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/verify", response_model=TrustVerifyResponse)
async def verify_trust(
    request: TrustVerifyRequest,
    user: User = Depends(get_current_user),
) -> TrustVerifyResponse:
    """Verify trust score for a company/recruiter combination."""
    trust_score = await _verification_service.verify(
        company_name=request.company_name,
        company_registration_number=request.company_registration_number,
        recruiter_email=request.recruiter_email,
        recruiter_linkedin_url=request.recruiter_linkedin_url,
        job_url=request.job_url,
    )

    entity_id = TrustVerificationService._build_entity_id(
        request.company_name, request.recruiter_email
    )

    return TrustVerifyResponse(
        entity_id=entity_id,
        company_verification_score=trust_score.company_verification_score,
        recruiter_verification_score=trust_score.recruiter_verification_score,
        posting_freshness_score=trust_score.posting_freshness_score,
        red_flag_count=trust_score.red_flag_count,
        overall_trust_score=trust_score.overall_trust_score,
        risk_category=trust_score.risk_category,
        risk_signals=[s.model_dump() for s in trust_score.risk_signals],
    )


@router.get("/jobs/{job_id}", response_model=JobTrustResponse)
async def get_job_trust(
    job_id: str,
    user: User = Depends(get_current_user),
) -> JobTrustResponse:
    """Retrieve cached trust score for a job."""
    cached = _verification_service.get_cached_score_for_job(job_id)
    if cached is None:
        raise NotFoundError("Trust score", job_id)

    return JobTrustResponse(
        job_id=job_id,
        company_verification_score=cached.company_verification_score,
        recruiter_verification_score=cached.recruiter_verification_score,
        posting_freshness_score=cached.posting_freshness_score,
        red_flag_count=cached.red_flag_count,
        overall_trust_score=cached.overall_trust_score,
        risk_category=cached.risk_category,
        risk_signals=[s.model_dump() for s in cached.risk_signals],
    )


@router.post("/analyze-posting", response_model=PostingAnalysisResponse)
async def analyze_posting(
    request: PostingAnalysisRequest,
    user: User = Depends(get_current_user),
) -> PostingAnalysisResponse:
    """Analyze a job posting for freshness, red flags, and India-specific scam patterns."""
    result = await _verification_service.analyze_posting(
        job_title=request.job_title,
        company_name=request.company_name,
        jd_text=request.jd_text,
        posted_date=request.posted_date,
        salary_range=request.salary_range,
        communication_channel=request.communication_channel,
        locale=request.locale,
    )

    return PostingAnalysisResponse(
        freshness=FreshnessScoreResponse(**result["freshness"].model_dump()),
        red_flags=[RedFlagResponse(**f.model_dump()) for f in result["red_flags"]],
        india_specific_flags=[RedFlagResponse(**f.model_dump()) for f in result["india_specific_flags"]],
        recommended_actions=result["recommended_actions"],
        overall_risk_level=result["overall_risk_level"],
    )


@router.post("/report", response_model=ScamReportResponse, status_code=201)
async def submit_scam_report(
    request: ScamReportRequest,
    user: User = Depends(get_current_user),
    repo: ScamReportRepository = Depends(get_scam_report_repository),
) -> ScamReportResponse:
    """Submit a scam report for a company, recruiter, or posting."""
    service = ScamReportService(repo)
    report = await service.submit_report(
        reporter_user_id=user.id,
        entity_type=request.entity_type,
        entity_identifier=request.entity_identifier,
        evidence_type=request.evidence_type,
        evidence_text=request.evidence_text,
        risk_category=request.risk_category,
    )

    return ScamReportResponse(
        id=str(report.id),
        entity_type=report.entity_type,
        entity_identifier=report.entity_identifier,
        risk_category=report.risk_category,
        warning_badge_applied=report.warning_badge_applied,
    )


@router.get("/reports", response_model=EntityReportSummary)
async def get_entity_reports(
    entity_identifier: str = Query(..., description="Entity to look up reports for"),
    user: User = Depends(get_current_user),
    repo: ScamReportRepository = Depends(get_scam_report_repository),
) -> EntityReportSummary:
    """Get report summary for an entity. Returns empty result if no reports exist."""
    service = ScamReportService(repo)
    summary = await service.get_entity_reports(entity_identifier)
    return EntityReportSummary(**summary)


@router.get("/trending", response_model=list[TrendingScamResponse])
async def get_trending_scams(
    region: str | None = Query(None, description="Filter by region (e.g. IN, US)"),
    user: User = Depends(get_current_user),
    repo: ScamReportRepository = Depends(get_scam_report_repository),
) -> list[TrendingScamResponse]:
    """Return trending scam patterns, optionally filtered by region."""
    service = ScamReportService(repo)
    patterns = await service.get_trending_scams(region=region)
    return [
        TrendingScamResponse(
            pattern_type=p.pattern_type,
            region=p.region,
            affected_companies=p.affected_companies,
            report_count=p.report_count,
            example_signals=p.example_signals,
        )
        for p in patterns
    ]


@router.post("/analyze-communication", response_model=CommunicationAnalysisResponse)
async def analyze_communication(
    request: CommunicationAnalysisRequest,
    user: User = Depends(get_current_user),
) -> CommunicationAnalysisResponse:
    """Analyze recruiter communication for scam patterns and PII sharing boundaries."""
    analyzer = OffPlatformAlertAnalyzer()
    flags = analyzer.analyze(request.recruiter_behavior)
    overall_risk = analyzer.calculate_overall_risk(flags)
    actions = analyzer.generate_recommended_actions(flags)

    pii_assessment = None
    if request.pii_requested:
        gatekeeper = PIIGatekeeper()
        assessment = gatekeeper.evaluate(
            hiring_stage=request.hiring_stage,
            jurisdiction=request.jurisdiction,
            pii_requested=request.pii_requested,
        )
        pii_assessment = PIIAssessmentResponse(
            hiring_stage=assessment.hiring_stage,
            jurisdiction=assessment.jurisdiction,
            appropriate_pii=assessment.appropriate_pii,
            inappropriate_pii=assessment.inappropriate_pii,
            alerts=assessment.alerts,
        )

    return CommunicationAnalysisResponse(
        risk_flags=[
            CommunicationRiskFlagResponse(
                behavior=f.behavior,
                severity=f.severity,
                explanation=f.explanation,
                recommended_action=f.recommended_action,
            )
            for f in flags
        ],
        overall_risk_level=overall_risk,
        recommended_actions=actions,
        pii_assessment=pii_assessment,
    )


@router.post("/ghost-check", response_model=GhostCheckResponse)
async def ghost_check(
    request: GhostCheckRequest,
    user: User = Depends(get_current_user),
    repo: ScamReportRepository = Depends(get_scam_report_repository),
) -> GhostCheckResponse:
    """Check if a job posting is likely a ghost listing."""
    if not request.job_url and not (request.company_name and request.job_title):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail="Provide either job_url or both company_name and job_title",
        )

    sentry = GhostJobSentry(repo)
    result = await sentry.check(
        job_url=request.job_url,
        company_name=request.company_name,
        job_title=request.job_title,
        posted_date=request.posted_date,
    )

    return GhostCheckResponse(
        liveness_score=result["liveness_score"],
        verdict=result["verdict"],
        signals=[
            LivenessSignalResponse(
                signal_name=s.signal_name,
                signal_value=s.signal_value,
                weight=s.weight,
                description=s.description,
            )
            for s in result["signals"]
        ],
        warning=result["warning"],
        recommendation=result["recommendation"],
    )


# ---------------------------------------------------------------------------
# Deepfake guide schemas
# ---------------------------------------------------------------------------


class ChecklistItemResponse(BaseModel):
    check: str
    description: str
    severity: str


class ChecklistCategoryResponse(BaseModel):
    category_name: str
    items: list[ChecklistItemResponse]


class DeepfakeChecklistResponse(BaseModel):
    categories: list[ChecklistCategoryResponse]
    last_updated: str


class DeepfakeReportRequest(BaseModel):
    interview_id: str | None = None
    company_name: str | None = None
    recruiter_name: str | None = None
    observed_anomalies: list[str]
    interview_platform: str | None = None


class DeepfakeReportResponse(BaseModel):
    id: str
    entity_type: str
    entity_identifier: str
    risk_category: str


# ---------------------------------------------------------------------------
# Deepfake endpoints
# ---------------------------------------------------------------------------


@router.get("/deepfake-guide", response_model=DeepfakeChecklistResponse)
async def get_deepfake_guide(
    user: User = Depends(get_current_user),
) -> DeepfakeChecklistResponse:
    """Return the deepfake interview detection checklist."""
    guide = DeepfakeInterviewGuide.get_guide()
    return DeepfakeChecklistResponse(
        categories=[
            ChecklistCategoryResponse(
                category_name=c.category_name,
                items=[
                    ChecklistItemResponse(
                        check=i.check,
                        description=i.description,
                        severity=i.severity,
                    )
                    for i in c.items
                ],
            )
            for c in guide.categories
        ],
        last_updated=guide.last_updated,
    )


@router.post("/deepfake-report", response_model=DeepfakeReportResponse, status_code=201)
async def submit_deepfake_report(
    request: DeepfakeReportRequest,
    user: User = Depends(get_current_user),
    repo: ScamReportRepository = Depends(get_scam_report_repository),
) -> DeepfakeReportResponse:
    """Submit a deepfake interview concern report."""
    service = ScamReportService(repo)
    report = await service.submit_deepfake_report(
        reporter_user_id=user.id,
        company_name=request.company_name,
        recruiter_name=request.recruiter_name,
        interview_id=request.interview_id,
        observed_anomalies=request.observed_anomalies,
        interview_platform=request.interview_platform,
    )
    return DeepfakeReportResponse(
        id=str(report.id),
        entity_type=report.entity_type,
        entity_identifier=report.entity_identifier,
        risk_category=report.risk_category,
    )


# ---------------------------------------------------------------------------
# Damage control schemas
# ---------------------------------------------------------------------------

_VALID_SCAM_TYPES = {"financial_fraud", "identity_theft", "fake_offer", "data_breach"}
_VALID_JURISDICTIONS = {"IN", "US"}


class DamageControlRequest(BaseModel):
    scam_type: str
    information_shared: list[str]
    jurisdiction: str
    additional_context: str = ""

    @field_validator("scam_type")
    @classmethod
    def validate_scam_type(cls, v: str) -> str:
        if v not in _VALID_SCAM_TYPES:
            msg = f"scam_type must be one of: {', '.join(sorted(_VALID_SCAM_TYPES))}"
            raise ValueError(msg)
        return v

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in _VALID_JURISDICTIONS:
            msg = f"jurisdiction must be one of: {', '.join(sorted(_VALID_JURISDICTIONS))}"
            raise ValueError(msg)
        return v_upper


class RecoveryStepResponse(BaseModel):
    step_number: int
    action: str
    details: str
    urgency: str
    url: str | None = None


class RecoveryPlanResponse(BaseModel):
    scam_type: str
    jurisdiction: str
    immediate_actions: list[RecoveryStepResponse]
    complaint_filing: list[RecoveryStepResponse]
    monitoring_steps: list[RecoveryStepResponse]
    platform_flagging: list[RecoveryStepResponse]
    additional_recommendations: list[str]


# ---------------------------------------------------------------------------
# Damage control endpoint
# ---------------------------------------------------------------------------


@router.post("/damage-control", response_model=RecoveryPlanResponse)
async def damage_control(
    request: DamageControlRequest,
    user: User = Depends(get_current_user),
) -> RecoveryPlanResponse:
    """Generate a post-scam recovery plan based on scam type and jurisdiction."""
    assistant = DamageControlAssistant()
    plan = assistant.generate_plan(
        scam_type=request.scam_type,
        information_shared=request.information_shared,
        jurisdiction=request.jurisdiction,
        additional_context=request.additional_context,
    )

    def _to_response(steps):
        return [
            RecoveryStepResponse(
                step_number=s.step_number,
                action=s.action,
                details=s.details,
                urgency=s.urgency,
                url=s.url,
            )
            for s in steps
        ]

    return RecoveryPlanResponse(
        scam_type=plan.scam_type,
        jurisdiction=plan.jurisdiction,
        immediate_actions=_to_response(plan.immediate_actions),
        complaint_filing=_to_response(plan.complaint_filing),
        monitoring_steps=_to_response(plan.monitoring_steps),
        platform_flagging=_to_response(plan.platform_flagging),
        additional_recommendations=plan.additional_recommendations,
    )
