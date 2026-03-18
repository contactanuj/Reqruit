"""Career routes — onboarding plans, coaching, and career operating system features."""

import json
import uuid
from datetime import UTC, datetime

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.agents.career_drift_detector import career_drift_detector_agent
from src.agents.career_path_simulator import career_path_simulator_agent
from src.agents.certification_roi_ranker import certification_roi_ranker_agent
from src.agents.learning_path_architect import learning_path_architect_agent
from src.agents.onboarding_coach import onboarding_coach_agent
from src.agents.service_exit_planner import service_exit_planner_agent
from src.agents.story_arc_builder import story_arc_builder_agent
from src.api.dependencies import get_current_user
from src.core.exceptions import NotFoundError
from src.db.documents.career_vitals import CareerVitals, DriftIndicator, HealthMetric
from src.db.documents.user import User
from src.repositories.career_vitals_repository import CareerVitalsRepository
from src.repositories.onboarding_plan_repository import OnboardingPlanRepository
from src.services.cross_industry_skill_mapper import translate_skills
from src.services.early_warning_service import generate_early_warnings
from src.services.gcc_career_ladder import analyze_gcc_career
from src.services.milestone_tracker import (
    generate_reminders,
    get_overdue_milestones,
    get_upcoming_milestones,
    update_milestone_status,
)
from src.services.stepping_stone_pathfinder import find_bridge_roles

logger = structlog.get_logger()
router = APIRouter(prefix="/career", tags=["career"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreatePlanRequest(BaseModel):
    company_name: str
    role_title: str
    start_date: str  # ISO date string
    jd_text: str | None = None
    locale: str = ""  # e.g., "IN", "US"


class MilestoneResponse(BaseModel):
    title: str
    target_day: int
    description: str
    completed: bool


class RelationshipTargetResponse(BaseModel):
    role: str
    description: str
    conversation_starters: list[str]
    optimal_timing: str


class JoiningPrepItemResponse(BaseModel):
    category: str
    title: str
    description: str
    checklist: list[str]
    locale_specific: bool


class OnboardingPlanResponse(BaseModel):
    id: str
    company_name: str
    role_title: str
    milestones: list[MilestoneResponse]
    progress_pct: float
    skill_gaps: list[dict]
    relationship_targets: list[RelationshipTargetResponse] = []
    joining_prep: list[JoiningPrepItemResponse] = []


class PlanCreatedResponse(BaseModel):
    thread_id: str
    message: str


class CoachingRequest(BaseModel):
    situation_description: str = Field(min_length=10)
    plan_id: str | None = None


class CoachingResponse(BaseModel):
    whats_happening: str
    how_to_respond: str
    conversation_scripts: list[str]
    when_to_escalate: str
    session_count: int


class MilestoneUpdateRequest(BaseModel):
    status: str  # "completed" or "incomplete"


class MilestoneStatusResponse(BaseModel):
    title: str
    target_day: int
    completed: bool
    completed_at: datetime | None = None
    overdue: bool = False
    days_overdue: int = 0
    catch_up_suggestion: str | None = None


class PlanDetailResponse(BaseModel):
    id: str
    company_name: str
    role_title: str
    milestones: list[MilestoneResponse]
    progress_pct: float
    relationship_targets: list[RelationshipTargetResponse] = []
    joining_prep: list[JoiningPrepItemResponse] = []
    overdue_milestones: list[MilestoneStatusResponse] = []
    upcoming_milestones: list[MilestoneStatusResponse] = []
    reminders: list[str] = []


def _safe_build_list(model_cls: type, items: list[dict]) -> list:
    """Build a list of Pydantic models, silently skipping invalid entries."""
    result = []
    for item in items:
        try:
            result.append(model_cls(**item))
        except (TypeError, ValueError):
            continue
    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/onboarding/plan", response_model=PlanCreatedResponse, status_code=202)
async def create_onboarding_plan(
    request: CreatePlanRequest,
    user: User = Depends(get_current_user),
) -> PlanCreatedResponse:
    """Trigger onboarding plan generation via the onboarding graph."""
    from src.workflows.graphs.onboarding import get_onboarding_graph

    graph = get_onboarding_graph()
    thread_id = str(uuid.uuid4())

    initial_state = {
        "messages": [],
        "company_name": request.company_name,
        "role_title": request.role_title,
        "skill_gaps": [],
        "plan": {},
        "jd_text": request.jd_text or "",
        "coaching_query": "",
        "coaching_response": "",
        "feedback": "",
        "locale": request.locale,
        "status": "generating",
    }

    # Attempt to fetch skill gaps from SkillsProfile if available
    try:
        from src.repositories.skills_profile_repository import SkillsProfileRepository
        skills_repo = SkillsProfileRepository()
        profile = await skills_repo.find_one({"user_id": user.id})
        if profile and hasattr(profile, "skills"):
            initial_state["skill_gaps"] = [
                {"skill": s.name, "level": s.proficiency_level}
                for s in profile.skills
                if hasattr(s, "proficiency_level") and s.proficiency_level in ("beginner", "novice")
            ]
    except Exception:
        logger.warning("skills_profile_fetch_failed", user_id=str(user.id))

    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}

    try:
        await graph.ainvoke(initial_state, config)
    except Exception:
        logger.exception("onboarding_graph_invoke_failed", user_id=str(user.id))
        from src.core.exceptions import BusinessValidationError
        raise BusinessValidationError(
            "Onboarding plan generation failed. Please try again.",
            error_code="ONBOARDING_GRAPH_FAILED",
        )

    return PlanCreatedResponse(
        thread_id=thread_id,
        message="Onboarding plan generation started",
    )


@router.get("/onboarding/plan", response_model=OnboardingPlanResponse)
async def get_onboarding_plan(
    user: User = Depends(get_current_user),
) -> OnboardingPlanResponse:
    """Return the user's active onboarding plan."""
    repo = OnboardingPlanRepository()
    plan = await repo.get_active(user.id)

    if not plan:
        raise NotFoundError("Onboarding plan")

    return OnboardingPlanResponse(
        id=str(plan.id),
        company_name=plan.company_name,
        role_title=plan.role_title,
        milestones=[
            MilestoneResponse(
                title=m.title,
                target_day=m.target_day,
                description=m.description,
                completed=m.completed,
            )
            for m in plan.milestones
        ],
        progress_pct=plan.progress_pct,
        skill_gaps=plan.skill_gaps,
        relationship_targets=[
            RelationshipTargetResponse(
                role=rt.role,
                description=rt.description,
                conversation_starters=rt.conversation_starters,
                optimal_timing=rt.optimal_timing,
            )
            for rt in plan.relationship_targets
        ],
        joining_prep=[
            JoiningPrepItemResponse(
                category=jp.category,
                title=jp.title,
                description=jp.description,
                checklist=jp.checklist,
                locale_specific=jp.locale_specific,
            )
            for jp in plan.joining_prep
        ],
    )


@router.get("/onboarding/plan/{plan_id}", response_model=PlanDetailResponse)
async def get_onboarding_plan_detail(
    plan_id: str,
    user: User = Depends(get_current_user),
) -> PlanDetailResponse:
    """Return full plan detail with progress, overdue flags, and reminders."""
    repo = OnboardingPlanRepository()
    plan = await repo.get_by_id_and_user(PydanticObjectId(plan_id), user.id)

    if not plan:
        raise NotFoundError("Onboarding plan")

    overdue = get_overdue_milestones(plan)
    upcoming = get_upcoming_milestones(plan)
    reminders = generate_reminders(plan)

    return PlanDetailResponse(
        id=str(plan.id),
        company_name=plan.company_name,
        role_title=plan.role_title,
        milestones=[
            MilestoneResponse(
                title=m.title,
                target_day=m.target_day,
                description=m.description,
                completed=m.completed,
            )
            for m in plan.milestones
        ],
        progress_pct=plan.progress_pct,
        relationship_targets=[
            RelationshipTargetResponse(
                role=rt.role,
                description=rt.description,
                conversation_starters=rt.conversation_starters,
                optimal_timing=rt.optimal_timing,
            )
            for rt in plan.relationship_targets
        ],
        joining_prep=[
            JoiningPrepItemResponse(
                category=jp.category,
                title=jp.title,
                description=jp.description,
                checklist=jp.checklist,
                locale_specific=jp.locale_specific,
            )
            for jp in plan.joining_prep
        ],
        overdue_milestones=[
            MilestoneStatusResponse(
                title=o.title,
                target_day=o.target_day,
                completed=False,
                overdue=True,
                days_overdue=o.days_overdue,
                catch_up_suggestion=o.catch_up_suggestion,
            )
            for o in overdue
        ],
        upcoming_milestones=[
            MilestoneStatusResponse(
                title=u.title,
                target_day=u.target_day,
                completed=False,
            )
            for u in upcoming
        ],
        reminders=reminders,
    )


@router.patch("/onboarding/plan/{plan_id}/milestone/{milestone_index}")
async def update_milestone(
    plan_id: str,
    milestone_index: int,
    request: MilestoneUpdateRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Update a milestone's completion status and recalculate progress."""
    repo = OnboardingPlanRepository()
    plan = await repo.get_by_id_and_user(PydanticObjectId(plan_id), user.id)

    if not plan:
        raise NotFoundError("Onboarding plan")

    completed = request.status == "completed"

    try:
        plan = update_milestone_status(plan, milestone_index, completed)
    except IndexError:
        raise NotFoundError("Milestone")

    await repo.update(plan.id, {
        "milestones": [m.model_dump() for m in plan.milestones],
        "progress_pct": plan.progress_pct,
    })

    return {
        "progress_pct": plan.progress_pct,
        "milestone": {
            "title": plan.milestones[milestone_index].title,
            "completed": plan.milestones[milestone_index].completed,
        },
    }


@router.post("/onboarding/coach", response_model=CoachingResponse)
async def coaching_session(
    request: CoachingRequest,
    user: User = Depends(get_current_user),
) -> CoachingResponse:
    """Provide confidential onboarding coaching for a tricky situation."""
    # Build minimal state for the agent
    state = {
        "coaching_query": request.situation_description,
        "company_name": "",
        "role_title": "",
        "plan": {},
    }

    # If plan_id provided, fetch plan for context
    if request.plan_id:
        repo = OnboardingPlanRepository()
        plan = await repo.get_by_id_and_user(
            PydanticObjectId(request.plan_id), user.id
        )
        if plan:
            state["company_name"] = plan.company_name
            state["role_title"] = plan.role_title
            state["plan"] = {
                "milestones": [m.model_dump() for m in plan.milestones],
            }
            plan.coaching_session_count += 1
            await repo.update(plan.id, {
                "coaching_session_count": plan.coaching_session_count,
            })

    config = {"configurable": {"user_id": str(user.id)}}
    result = await onboarding_coach_agent(state, config)

    coaching_data = json.loads(result.get("coaching_response", "{}"))

    # Get session count
    session_count = 1
    if request.plan_id:
        repo = OnboardingPlanRepository()
        plan = await repo.get_by_id_and_user(
            PydanticObjectId(request.plan_id), user.id
        )
        if plan:
            session_count = plan.coaching_session_count

    return CoachingResponse(
        whats_happening=coaching_data.get("whats_happening", ""),
        how_to_respond=coaching_data.get("how_to_respond", ""),
        conversation_scripts=coaching_data.get("conversation_scripts", []),
        when_to_escalate=coaching_data.get("when_to_escalate", ""),
        session_count=session_count,
    )


# ---------------------------------------------------------------------------
# Schemas — Career Health (Epic 20)
# ---------------------------------------------------------------------------


class CareerVitalsRequest(BaseModel):
    role_title: str
    industry: str = ""
    years_experience: float = 0
    skills: list[str] = Field(default_factory=list)
    career_goals: str = ""
    locale: str = ""


class HealthMetricResponse(BaseModel):
    name: str
    score: float
    trend: str
    explanation: str


class DriftIndicatorResponse(BaseModel):
    category: str
    severity: str
    description: str
    recommended_action: str


class CareerVitalsResponse(BaseModel):
    overall_score: float
    career_stage: str
    metrics: list[HealthMetricResponse]
    drift_indicators: list[DriftIndicatorResponse]


class CareerPathRequest(BaseModel):
    role_title: str
    industry: str = ""
    years_experience: float = 0
    skills: list[str] = Field(default_factory=list)
    career_goals: str = ""
    locale: str = ""
    current_salary: str = ""


class EarlyWarningResponse(BaseModel):
    signal_type: str
    severity: str
    title: str
    description: str
    recommended_action: str


# ---------------------------------------------------------------------------
# Schemas — Career Transition (Epic 22)
# ---------------------------------------------------------------------------


class LearningPathRequest(BaseModel):
    current_skills: list[str] = Field(default_factory=list)
    target_skills: list[str] = Field(default_factory=list)
    role_title: str = ""
    hours_per_week: int = 10
    budget: str = ""


class NarrativeRequest(BaseModel):
    experiences: list[dict] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    role_title: str = ""
    target_narrative: str = ""
    feedback: str = ""


class SkillTranslateRequest(BaseModel):
    skills: list[str]
    source_industry: str
    target_industry: str


class BridgeRoleRequest(BaseModel):
    current_role: str
    target_role: str
    current_skills: list[str] = Field(default_factory=list)


class CertificationROIRequest(BaseModel):
    role_title: str = ""
    skills: list[str] = Field(default_factory=list)
    career_goals: str = ""
    locale: str = ""
    budget: str = ""
    existing_certifications: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Schemas — India Career Mobility (Epic 23)
# ---------------------------------------------------------------------------


class ServiceExitRequest(BaseModel):
    current_company: str = ""
    company_type: str = "service"
    role_title: str = ""
    years_experience: float = 0
    skills: list[str] = Field(default_factory=list)
    target_companies: str = ""
    notice_period_days: int = 0
    current_ctc: str = ""


class GCCCareerRequest(BaseModel):
    current_role: str = ""
    years_experience: float = 0
    target_track: str = "individual_contributor"


# ---------------------------------------------------------------------------
# Career Health Endpoints (Epic 20)
# ---------------------------------------------------------------------------


@router.post("/vitals", response_model=CareerVitalsResponse)
async def assess_career_vitals(
    request: CareerVitalsRequest,
    user: User = Depends(get_current_user),
) -> CareerVitalsResponse:
    """Run a career health assessment using the drift detector agent."""
    state = {
        "role_title": request.role_title,
        "industry": request.industry,
        "years_experience": request.years_experience,
        "skills": request.skills,
        "career_goals": request.career_goals,
        "locale": request.locale,
    }

    config = {"configurable": {"user_id": str(user.id)}}
    result = await career_drift_detector_agent(state, config)

    vitals = CareerVitals(
        user_id=user.id,
        assessment_date=datetime.now(UTC),
        overall_score=result.get("overall_score", 0.0),
        metrics=_safe_build_list(HealthMetric, result.get("metrics", [])),
        drift_indicators=_safe_build_list(DriftIndicator, result.get("drift_indicators", [])),
        career_stage=result.get("career_stage", ""),
        industry=request.industry,
        role_title=request.role_title,
        years_experience=request.years_experience,
        locale=request.locale,
    )
    repo = CareerVitalsRepository()
    await repo.create(vitals)

    return CareerVitalsResponse(
        overall_score=result.get("overall_score", 0.0),
        career_stage=result.get("career_stage", ""),
        metrics=_safe_build_list(HealthMetricResponse, result.get("metrics", [])),
        drift_indicators=_safe_build_list(DriftIndicatorResponse, result.get("drift_indicators", [])),
    )


@router.post("/path-simulation")
async def simulate_career_paths(
    request: CareerPathRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Simulate career path scenarios with probability estimates."""
    state = {
        "role_title": request.role_title,
        "industry": request.industry,
        "years_experience": request.years_experience,
        "skills": request.skills,
        "career_goals": request.career_goals,
        "locale": request.locale,
        "current_salary": request.current_salary,
    }

    config = {"configurable": {"user_id": str(user.id)}}
    result = await career_path_simulator_agent(state, config)

    return {
        "scenarios": result.get("scenarios", []),
        "india_insights": result.get("india_insights", {}),
    }


@router.get("/signals", response_model=list[EarlyWarningResponse])
async def get_early_warning_signals(
    user: User = Depends(get_current_user),
) -> list[EarlyWarningResponse]:
    """Get early warning signals based on latest career vitals."""
    repo = CareerVitalsRepository()
    vitals = await repo.get_latest(user.id)

    if not vitals:
        return []

    signals = generate_early_warnings(vitals)

    return [
        EarlyWarningResponse(
            signal_type=s.signal_type,
            severity=s.severity,
            title=s.title,
            description=s.description,
            recommended_action=s.recommended_action,
        )
        for s in signals
    ]


# ---------------------------------------------------------------------------
# Career Transition Endpoints (Epic 22)
# ---------------------------------------------------------------------------


@router.post("/learning-path")
async def generate_learning_path(
    request: LearningPathRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Generate a personalized learning path for skill gaps."""
    state = {
        "current_skills": request.current_skills,
        "target_skills": request.target_skills,
        "role_title": request.role_title,
        "hours_per_week": request.hours_per_week,
        "budget": request.budget,
    }

    config = {"configurable": {"user_id": str(user.id)}}
    result = await learning_path_architect_agent(state, config)

    return {
        "learning_paths": result.get("learning_paths", []),
        "total_estimated_hours": result.get("total_estimated_hours", 0),
        "recommended_schedule": result.get("recommended_schedule", ""),
    }


@router.post("/narrative")
async def build_career_narrative(
    request: NarrativeRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Build a career narrative from work experience."""
    state = {
        "experiences": request.experiences,
        "achievements": request.achievements,
        "role_title": request.role_title,
        "target_narrative": request.target_narrative,
        "feedback": request.feedback,
    }

    config = {"configurable": {"user_id": str(user.id)}}
    result = await story_arc_builder_agent(state, config)

    return {
        "career_arc": result.get("career_arc", {}),
        "stories": result.get("stories", []),
        "positioning_statement": result.get("positioning_statement", ""),
        "elevator_pitch": result.get("elevator_pitch", ""),
    }


@router.post("/skill-translate")
async def translate_cross_industry_skills(
    request: SkillTranslateRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Translate skills between industry contexts."""
    result = translate_skills(
        skills=request.skills,
        source_industry=request.source_industry,
        target_industry=request.target_industry,
    )
    return result.model_dump()


@router.post("/bridge-roles")
async def find_stepping_stone_roles(
    request: BridgeRoleRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Find bridge roles for career transitions."""
    result = find_bridge_roles(
        current_role=request.current_role,
        target_role=request.target_role,
        current_skills=request.current_skills or None,
    )
    return result.model_dump()


@router.post("/certification-roi")
async def rank_certifications(
    request: CertificationROIRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Rank certifications by ROI for the user's career context."""
    state = {
        "role_title": request.role_title,
        "skills": request.skills,
        "career_goals": request.career_goals,
        "locale": request.locale,
        "budget": request.budget,
        "existing_certifications": request.existing_certifications,
    }

    config = {"configurable": {"user_id": str(user.id)}}
    result = await certification_roi_ranker_agent(state, config)

    return {
        "certifications": result.get("certifications", []),
        "top_recommendation": result.get("top_recommendation", ""),
        "locale_insights": result.get("locale_insights", ""),
    }


# ---------------------------------------------------------------------------
# India Career Mobility Endpoints (Epic 23)
# ---------------------------------------------------------------------------


@router.post("/service-exit-plan")
async def plan_service_exit(
    request: ServiceExitRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Plan a service-to-product company transition."""
    state = {
        "current_company": request.current_company,
        "company_type": request.company_type,
        "role_title": request.role_title,
        "years_experience": request.years_experience,
        "skills": request.skills,
        "target_companies": request.target_companies,
        "notice_period_days": request.notice_period_days,
        "current_ctc": request.current_ctc,
    }

    config = {"configurable": {"user_id": str(user.id)}}
    result = await service_exit_planner_agent(state, config)

    return {
        "readiness_score": result.get("readiness_score", 0),
        "skill_gaps": result.get("skill_gaps", []),
        "resume_strategy": result.get("resume_strategy", {}),
        "interview_prep": result.get("interview_prep", {}),
        "target_companies": result.get("target_companies", {}),
        "timeline": result.get("timeline", []),
        "compensation_insights": result.get("compensation_insights", {}),
        "notice_period_strategy": result.get("notice_period_strategy", ""),
    }


@router.post("/gcc-career")
async def analyze_gcc_career_path(
    request: GCCCareerRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Analyze career progression within the GCC framework."""
    result = analyze_gcc_career(
        current_role=request.current_role,
        years_experience=request.years_experience,
        target_track=request.target_track,
    )
    return result.model_dump()
