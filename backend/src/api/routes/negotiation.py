"""
Negotiation routes: multi-turn negotiation simulation and script generation.

Endpoints for starting a negotiation simulation, responding to recruiter turns,
generating counter-offer scripts, and retrieving session state. All require JWT auth.
"""

import uuid

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from fastapi.responses import Response

from src.api.dependencies import (
    get_current_user,
    get_negotiation_session_repository,
    get_offer_repository,
    get_salary_benchmark_repository,
)
from src.db.documents.negotiation_session import NegotiationSession
from src.repositories.negotiation_session_repository import (
    NegotiationSessionRepository,
)
from src.core.exceptions import BusinessValidationError, NotFoundError
from src.db.documents.user import User
from src.repositories.offer_repository import OfferRepository
from src.repositories.salary_benchmark_repository import SalaryBenchmarkRepository
from src.services.market_positioning import compute_market_position
from src.workflows.graphs.negotiation import get_negotiation_graph

logger = structlog.get_logger()

router = APIRouter(prefix="/negotiation", tags=["negotiation"])


# ---------------------------------------------------------------------------
# Inline Pydantic schemas
# ---------------------------------------------------------------------------


class NegotiationSimulateRequest(BaseModel):
    offer_id: PydanticObjectId
    competing_offer_ids: list[PydanticObjectId] = []
    negotiation_goals: dict = {}


class NegotiationSimulateResponse(BaseModel):
    thread_id: str
    recruiter_response: str
    coaching_feedback: str
    turn_number: int


class NegotiationRespondRequest(BaseModel):
    user_response: str


class NegotiationTurnResponse(BaseModel):
    recruiter_response: str
    coaching_feedback: str
    tactic_detected: str
    turn_number: int
    simulation_complete: bool


class ScriptGenerateRequest(BaseModel):
    offer_id: PydanticObjectId
    target_total_comp: float
    priorities: list[str] = []


class ScriptBranchResponse(BaseModel):
    scenario_name: str
    recruiter_response: str
    recommended_user_response: str
    reasoning: str
    risk_assessment: str


class NonSalaryTacticResponse(BaseModel):
    priority: str
    script: str
    fallback: str = ""


class ScriptGenerateResponse(BaseModel):
    opening_statement: str
    branches: list[ScriptBranchResponse]
    non_salary_tactics: list[NonSalaryTacticResponse]
    general_tips: list[str] = []


# ---------------------------------------------------------------------------
# POST /negotiation/simulate
# ---------------------------------------------------------------------------


@router.post("/simulate", response_model=NegotiationSimulateResponse, status_code=202)
async def simulate_negotiation(
    body: NegotiationSimulateRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
    benchmark_repo: SalaryBenchmarkRepository = Depends(  # noqa: B008
        get_salary_benchmark_repository
    ),
    session_repo: NegotiationSessionRepository = Depends(  # noqa: B008
        get_negotiation_session_repository
    ),
) -> NegotiationSimulateResponse:
    """Start a new negotiation simulation for an offer."""
    # Validate offer exists and belongs to user
    offer = await offer_repo.get_by_user_and_id(current_user.id, body.offer_id)
    if offer is None:
        raise NotFoundError(f"Offer {body.offer_id} not found")

    # Build offer details for state
    offer_details = {
        "company_name": offer.company_name,
        "role_title": offer.role_title,
        "total_comp_annual": offer.total_comp_annual,
        "locale_market": offer.locale_market,
        "currency": offer.components[0].currency if offer.components else "INR",
        "components": [
            {"name": c.name, "value": c.value, "frequency": c.frequency}
            for c in offer.components
        ],
    }

    # Get market positioning data
    market_data = {}
    try:
        market_result = await compute_market_position(offer, benchmark_repo)
        if market_result.data_available:
            market_data = {
                "percentile": market_result.market_percentile,
                "salary_range": market_result.salary_range,
            }
    except Exception:
        logger.warning("market_data_fetch_failed", offer_id=str(offer.id))

    # Fetch competing offers if provided
    competing = []
    if body.competing_offer_ids:
        comp_offers = await offer_repo.compare_offers(
            current_user.id, body.competing_offer_ids
        )
        for co in comp_offers:
            competing.append({
                "company_name": co.company_name,
                "total_comp_annual": co.total_comp_annual,
                "role_title": co.role_title,
            })

    # Initialize graph state
    thread_id = str(uuid.uuid4())
    initial_state = {
        "messages": [],
        "offer_details": offer_details,
        "market_data": market_data,
        "competing_offers": competing,
        "user_priorities": body.negotiation_goals,
        "simulation_transcript": [],
        "user_response": "",
        "scripts": [],
        "decision_matrix": {},
        "feedback": "",
        "status": "simulating",
    }

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(current_user.id),
        }
    }

    # Run first turn — will hit interrupt()
    graph = get_negotiation_graph()
    result = await graph.ainvoke(initial_state, config)

    # Extract the first recruiter response from transcript
    transcript = result.get("simulation_transcript", [])
    recruiter_turn = next(
        (t for t in transcript if t.get("role") == "recruiter"),
        {},
    )

    # Persist session
    session = NegotiationSession(
        user_id=current_user.id,
        offer_id=body.offer_id,
        session_type="simulation",
        status="active",
        thread_id=thread_id,
        transcript=transcript,
    )
    await session_repo.create(session)

    logger.info(
        "negotiation_simulation_started",
        thread_id=thread_id,
        offer_id=str(body.offer_id),
        company=offer.company_name,
    )

    return NegotiationSimulateResponse(
        thread_id=thread_id,
        recruiter_response=recruiter_turn.get("content", ""),
        coaching_feedback=recruiter_turn.get("coaching_feedback", ""),
        turn_number=recruiter_turn.get("turn_number", 1),
    )


# ---------------------------------------------------------------------------
# POST /negotiation/{thread_id}/respond
# ---------------------------------------------------------------------------


@router.post(
    "/{thread_id}/respond",
    response_model=NegotiationTurnResponse,
)
async def respond_to_negotiation(
    thread_id: str,
    body: NegotiationRespondRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> NegotiationTurnResponse:
    """Submit a user response and get the next recruiter turn + coaching."""
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(current_user.id),
        }
    }

    graph = get_negotiation_graph()

    # Resume graph from interrupt with user's response
    from langgraph.types import Command

    result = await graph.ainvoke(
        Command(resume={"user_response": body.user_response}),
        config,
    )

    # Get the latest recruiter response from transcript
    transcript = result.get("simulation_transcript", [])
    recruiter_turns = [t for t in transcript if t.get("role") == "recruiter"]
    latest = recruiter_turns[-1] if recruiter_turns else {}

    is_complete = result.get("status") == "complete"

    logger.info(
        "negotiation_turn_completed",
        thread_id=thread_id,
        turn=latest.get("turn_number", 0),
        complete=is_complete,
    )

    return NegotiationTurnResponse(
        recruiter_response=latest.get("content", ""),
        coaching_feedback=latest.get("coaching_feedback", ""),
        tactic_detected=latest.get("tactic_detected", ""),
        turn_number=latest.get("turn_number", 0),
        simulation_complete=is_complete,
    )


# ---------------------------------------------------------------------------
# POST /negotiation/scripts
# ---------------------------------------------------------------------------


@router.post("/scripts", response_model=ScriptGenerateResponse)
async def generate_scripts(
    body: ScriptGenerateRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
    benchmark_repo: SalaryBenchmarkRepository = Depends(  # noqa: B008
        get_salary_benchmark_repository
    ),
    session_repo: NegotiationSessionRepository = Depends(  # noqa: B008
        get_negotiation_session_repository
    ),
) -> ScriptGenerateResponse:
    """Generate counter-offer scripts with decision tree branches for an offer."""
    # Validate offer exists and belongs to user
    offer = await offer_repo.get_by_user_and_id(current_user.id, body.offer_id)
    if offer is None:
        raise NotFoundError(f"Offer {body.offer_id} not found")

    # Build offer details for agent state
    offer_details = {
        "company_name": offer.company_name,
        "role_title": offer.role_title,
        "total_comp_annual": offer.total_comp_annual,
        "locale_market": offer.locale_market,
        "currency": offer.components[0].currency if offer.components else "INR",
        "components": [
            {"name": c.name, "value": c.value, "frequency": c.frequency}
            for c in offer.components
        ],
    }

    # Get market positioning data
    market_data = {}
    try:
        market_result = await compute_market_position(offer, benchmark_repo)
        if market_result.data_available:
            market_data = {
                "percentile": market_result.market_percentile,
                "salary_range": market_result.salary_range,
            }
    except Exception:
        logger.warning("market_data_fetch_failed", offer_id=str(offer.id))

    # Invoke ScriptGeneratorAgent directly (outside graph)
    from src.agents.script_generator import ScriptGeneratorAgent

    agent = ScriptGeneratorAgent()
    state = {
        "offer_details": offer_details,
        "target_total_comp": body.target_total_comp,
        "user_priorities": body.priorities,
        "competing_offers": [],
        "market_data": market_data,
    }
    config = {"configurable": {"user_id": str(current_user.id)}}
    result = await agent(state, config)

    # Persist session
    scripts_data = {
        "opening_statement": result.get("opening_statement", ""),
        "branches": result.get("branches", []),
        "non_salary_tactics": result.get("non_salary_tactics", []),
        "general_tips": result.get("general_tips", []),
    }
    session = NegotiationSession(
        user_id=current_user.id,
        offer_id=body.offer_id,
        session_type="script",
        status="completed",
        scripts=[scripts_data],
    )
    await session_repo.create(session)

    logger.info(
        "negotiation_scripts_generated",
        offer_id=str(body.offer_id),
        branches_count=len(result.get("branches", [])),
    )

    return ScriptGenerateResponse(
        opening_statement=result.get("opening_statement", ""),
        branches=[
            ScriptBranchResponse(
                scenario_name=b.get("scenario_name", ""),
                recruiter_response=b.get("recruiter_response", ""),
                recommended_user_response=b.get("recommended_user_response", ""),
                reasoning=b.get("reasoning", ""),
                risk_assessment=b.get("risk_assessment", "moderate"),
            )
            for b in result.get("branches", [])
        ],
        non_salary_tactics=[
            NonSalaryTacticResponse(
                priority=t.get("priority", ""),
                script=t.get("script", ""),
                fallback=t.get("fallback", ""),
            )
            for t in result.get("non_salary_tactics", [])
        ],
        general_tips=result.get("general_tips", []),
    )


# ---------------------------------------------------------------------------
# POST /negotiation/decide
# ---------------------------------------------------------------------------


class DecisionFrameworkRequest(BaseModel):
    offer_ids: list[PydanticObjectId]
    criteria_weights: dict[str, float] = {}


class CriterionScoreResponse(BaseModel):
    criterion_name: str
    raw_score: float
    justification: str
    weighted_score: float


class OfferDecisionRowResponse(BaseModel):
    offer_id: str
    company_name: str
    scores: list[CriterionScoreResponse]
    weighted_total: float


class SensitivityResultResponse(BaseModel):
    scenario_description: str
    affected_offers: list[str]
    outcome: str


class DecisionMatrixResponse(BaseModel):
    offers: list[OfferDecisionRowResponse]
    criteria_weights: dict[str, float]
    sensitivity_analysis: list[SensitivityResultResponse]
    recommended_choice: str
    recommended_company: str
    reasoning: str
    weights_are_defaults: bool


@router.post("/decide", response_model=DecisionMatrixResponse)
async def decide_offers(
    body: DecisionFrameworkRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
    session_repo: NegotiationSessionRepository = Depends(  # noqa: B008
        get_negotiation_session_repository
    ),
) -> DecisionMatrixResponse:
    """Compute weighted multi-criteria decision matrix for competing offers."""
    if len(body.offer_ids) < 2:
        raise BusinessValidationError(
            detail="At least 2 offers are required for decision framework",
            error_code="INSUFFICIENT_OFFERS_FOR_COMPARISON",
        )

    # Validate weights sum to ~1.0 if provided
    if body.criteria_weights:
        weight_sum = sum(body.criteria_weights.values())
        if abs(weight_sum - 1.0) > 0.05:
            raise BusinessValidationError(
                detail=f"Criteria weights must sum to 1.0 (got {weight_sum:.3f})",
                error_code="INVALID_CRITERIA_WEIGHTS",
            )

    # Fetch all offers (user-scoped)
    offers = await offer_repo.compare_offers(current_user.id, body.offer_ids)
    if len(offers) != len(body.offer_ids):
        raise NotFoundError("One or more offers not found")

    from src.services.decision_framework import compute_decision_matrix

    result = await compute_decision_matrix(
        offers=offers,
        criteria_weights=body.criteria_weights or None,
        user_id=str(current_user.id),
    )

    # Persist session — use first offer_id as the session's offer_id
    session = NegotiationSession(
        user_id=current_user.id,
        offer_id=body.offer_ids[0],
        session_type="decision",
        status="completed",
        decision_matrix={
            "recommended_choice": result.recommended_choice,
            "recommended_company": result.recommended_company,
            "reasoning": result.reasoning,
            "weights_are_defaults": result.weights_are_defaults,
            "criteria_weights": result.criteria_weights,
            "offer_count": len(result.offers),
        },
    )
    await session_repo.create(session)

    return DecisionMatrixResponse(
        offers=[
            OfferDecisionRowResponse(
                offer_id=row.offer_id,
                company_name=row.company_name,
                scores=[
                    CriterionScoreResponse(
                        criterion_name=s.criterion_name,
                        raw_score=s.raw_score,
                        justification=s.justification,
                        weighted_score=s.weighted_score,
                    )
                    for s in row.scores
                ],
                weighted_total=row.weighted_total,
            )
            for row in result.offers
        ],
        criteria_weights=result.criteria_weights,
        sensitivity_analysis=[
            SensitivityResultResponse(
                scenario_description=s.scenario_description,
                affected_offers=s.affected_offers,
                outcome=s.outcome,
            )
            for s in result.sensitivity_analysis
        ],
        recommended_choice=result.recommended_choice,
        recommended_company=result.recommended_company,
        reasoning=result.reasoning,
        weights_are_defaults=result.weights_are_defaults,
    )


# ---------------------------------------------------------------------------
# Session CRUD schemas
# ---------------------------------------------------------------------------


class NegotiationSessionSummary(BaseModel):
    session_id: str
    offer_id: str
    session_type: str
    status: str
    created_at: str


class NegotiationSessionListResponse(BaseModel):
    items: list[NegotiationSessionSummary]
    total: int
    page: int
    page_size: int


class NegotiationSessionDetailResponse(BaseModel):
    session_id: str
    offer_id: str
    session_type: str
    status: str
    thread_id: str
    transcript: list[dict]
    scripts: list[dict]
    decision_matrix: dict
    created_at: str


# ---------------------------------------------------------------------------
# GET /negotiation/sessions
# ---------------------------------------------------------------------------


@router.get("/sessions", response_model=NegotiationSessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),  # noqa: B008
    session_repo: NegotiationSessionRepository = Depends(  # noqa: B008
        get_negotiation_session_repository
    ),
) -> NegotiationSessionListResponse:
    """List negotiation sessions for the current user, paginated."""
    skip = (page - 1) * page_size
    sessions = await session_repo.get_user_sessions(
        current_user.id, skip=skip, limit=page_size
    )

    return NegotiationSessionListResponse(
        items=[
            NegotiationSessionSummary(
                session_id=str(s.id),
                offer_id=str(s.offer_id),
                session_type=s.session_type,
                status=s.status,
                created_at=s.created_at.isoformat() if s.created_at else "",
            )
            for s in sessions
        ],
        total=len(sessions),
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# GET /negotiation/sessions/{session_id}
# ---------------------------------------------------------------------------


@router.get(
    "/sessions/{session_id}",
    response_model=NegotiationSessionDetailResponse,
)
async def get_session(
    session_id: PydanticObjectId,
    current_user: User = Depends(get_current_user),  # noqa: B008
    session_repo: NegotiationSessionRepository = Depends(  # noqa: B008
        get_negotiation_session_repository
    ),
) -> NegotiationSessionDetailResponse:
    """Get full details for a negotiation session."""
    session = await session_repo.get_by_user_and_id(current_user.id, session_id)
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")

    return NegotiationSessionDetailResponse(
        session_id=str(session.id),
        offer_id=str(session.offer_id),
        session_type=session.session_type,
        status=session.status,
        thread_id=session.thread_id,
        transcript=session.transcript,
        scripts=session.scripts,
        decision_matrix=session.decision_matrix,
        created_at=session.created_at.isoformat() if session.created_at else "",
    )


# ---------------------------------------------------------------------------
# DELETE /negotiation/sessions/{session_id}
# ---------------------------------------------------------------------------


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: PydanticObjectId,
    current_user: User = Depends(get_current_user),  # noqa: B008
    session_repo: NegotiationSessionRepository = Depends(  # noqa: B008
        get_negotiation_session_repository
    ),
) -> Response:
    """Delete a negotiation session. Returns 204 on success."""
    deleted = await session_repo.delete_by_user_and_id(current_user.id, session_id)
    if not deleted:
        raise NotFoundError(f"Session {session_id} not found")

    logger.info(
        "negotiation_session_deleted",
        session_id=str(session_id),
        user_id=str(current_user.id),
    )
    return Response(status_code=204)
