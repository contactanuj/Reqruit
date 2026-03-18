"""
Interview coach routes: adaptive mock interview sessions + history + trends.

Endpoints power the Adaptive Interview Coach (Module 14 / Phase 2).
All require JWT auth.
"""

import json
import uuid
from typing import Literal

import structlog
from fastapi import APIRouter, Depends
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel

from src.agents.company_patterns import get_company_pattern, get_default_pattern
from src.agents.question_predictor import QuestionPredictorAgent
from src.api.dependencies import (
    get_current_user,
    get_interview_coach_graph,
    get_interview_performance_repository,
)
from src.core.exceptions import BusinessValidationError, NotFoundError, RateLimitError
from src.db.documents.interview_performance import InterviewPerformance, QuestionScore
from src.db.documents.user import User
from src.repositories.interview_performance_repository import InterviewPerformanceRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/interviews/coach", tags=["interview-coach"])

_MAX_CONCURRENT_SESSIONS = 3


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CoachStartRequest(BaseModel):
    """Start a mock interview session."""

    company_name: str
    role_title: str
    jd_text: str = ""
    job_id: str = ""
    interview_mode: Literal["standard", "campus_placement"] = "standard"


class AnswerRequest(BaseModel):
    """Submit an answer to the current question."""

    answer: str


class PredictRequest(BaseModel):
    """Standalone question prediction request."""

    company_name: str
    role_title: str
    jd_text: str = ""


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------


@router.post("/start", status_code=202)
async def start_session(
    body: CoachStartRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_interview_coach_graph),  # noqa: B008
    perf_repo: InterviewPerformanceRepository = Depends(get_interview_performance_repository),  # noqa: B008
) -> dict:
    """Start a new mock interview coaching session."""
    active_count = await perf_repo.count_active_sessions(user.id)
    if active_count >= _MAX_CONCURRENT_SESSIONS:
        raise RateLimitError(
            "Maximum 3 concurrent coaching sessions allowed",
            error_code="MAX_CONCURRENT_SESSIONS",
        )

    thread_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}

    # Look up company-specific interview pattern
    pattern = get_company_pattern(body.company_name)
    pattern_json = pattern.model_dump_json() if pattern else get_default_pattern().model_dump_json()

    # Campus placement starts with aptitude round; standard starts with behavioral
    round_type = "aptitude" if body.interview_mode == "campus_placement" else "behavioral"

    initial_state = {
        "messages": [],
        "company_name": body.company_name,
        "role_title": body.role_title,
        "jd_analysis": body.jd_text,
        "jd_text": body.jd_text,
        "company_research": "",
        "locale_context": "",
        "predicted_questions": "",
        "current_question_index": 0,
        "current_question": "",
        "current_question_type": "",
        "user_answer": "",
        "difficulty_level": "medium",
        "evaluation": "",
        "session_scores": [],
        "star_stories": "",
        "overall_assessment": "",
        "status": "pending",
        "session_id": session_id,
        "job_id": body.job_id,
        "interview_mode": body.interview_mode,
        "round_type": round_type,
        "company_pattern": pattern_json,
        "current_round_index": 0,
    }

    await graph.ainvoke(initial_state, config=config)
    logger.info(
        "coach_session_started",
        thread_id=thread_id,
        session_id=session_id,
        user_id=str(user.id),
    )
    return {"thread_id": thread_id, "session_id": session_id, "status": "started"}


@router.post("/predict")
async def predict_questions(
    body: PredictRequest,
    user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Standalone question prediction — no graph, direct agent call."""
    predictor = QuestionPredictorAgent()
    state = {
        "company_name": body.company_name,
        "role_title": body.role_title,
        "jd_analysis": body.jd_text,
        "company_research": "",
        "locale_context": "",
    }
    config = {"configurable": {"user_id": str(user.id)}}
    result = await predictor(state, config)

    raw = result.get("predicted_questions", "[]")
    try:
        questions = json.loads(raw)
        if not isinstance(questions, list):
            questions = [{"question_text": raw, "confidence": "medium"}]
    except (json.JSONDecodeError, TypeError):
        questions = [{"question_text": raw, "confidence": "medium"}]

    return {"questions": questions}


class InterviewScore(BaseModel):
    """Structured scoring on 4 dimensions (0-5 each)."""

    relevance: int = 0
    structure: int = 0
    specificity: int = 0
    confidence: int = 0


@router.get("/{thread_id}/debrief")
async def get_debrief(
    thread_id: str,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_interview_coach_graph),  # noqa: B008
) -> dict:
    """Get the full debrief for a completed coaching session."""
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}
    state = await graph.aget_state(config)
    values = state.values

    if values.get("status") != "complete":
        raise BusinessValidationError(
            detail="Session is not yet complete",
            error_code="SESSION_NOT_COMPLETE",
        )

    try:
        assessment = json.loads(values.get("overall_assessment", "{}"))
    except (json.JSONDecodeError, TypeError):
        assessment = {"summary": values.get("overall_assessment", "")}

    return {
        "thread_id": thread_id,
        "overall_assessment": assessment,
        "session_scores": values.get("session_scores", []),
        "company_name": values.get("company_name", ""),
        "role_title": values.get("role_title", ""),
        "difficulty_level": values.get("difficulty_level", "medium"),
    }


@router.post("/{thread_id}/answer")
async def answer_question(
    thread_id: str,
    body: AnswerRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_interview_coach_graph),  # noqa: B008
) -> dict:
    """Submit an answer to the current interview question."""
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}

    result = await graph.ainvoke(
        Command(resume={"answer": body.answer}),
        config=config,
    )

    # Parse structured scores from evaluation
    scores: dict = {}
    feedback = ""
    improvement_suggestion = ""
    evaluation_raw = result.get("evaluation", "")
    try:
        eval_data = json.loads(evaluation_raw)
        if isinstance(eval_data, dict):
            scores = {
                "relevance": eval_data.get("score_relevance", 0),
                "structure": eval_data.get("score_structure", 0),
                "specificity": eval_data.get("score_specificity", 0),
                "confidence": eval_data.get("score_confidence", 0),
            }
            feedback = eval_data.get("feedback", "")
            improvement_suggestion = eval_data.get("improvement_suggestion", "")
    except (json.JSONDecodeError, TypeError):
        pass

    # Calculate questions remaining
    predicted = result.get("predicted_questions", "[]")
    try:
        total_questions = len(json.loads(predicted))
    except (json.JSONDecodeError, TypeError):
        total_questions = 0
    current_index = result.get("current_question_index", 0)

    return {
        "evaluation": evaluation_raw,
        "scores": scores,
        "feedback": feedback,
        "improvement_suggestion": improvement_suggestion,
        "current_question": result.get("current_question", ""),
        "difficulty_level": result.get("difficulty_level", "medium"),
        "questions_remaining": max(0, total_questions - current_index - 1),
        "star_stories": result.get("star_stories", ""),
        "overall_assessment": result.get("overall_assessment", ""),
        "status": result.get("status", ""),
    }


@router.get("/{thread_id}/status")
async def get_session_status(
    thread_id: str,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_interview_coach_graph),  # noqa: B008
) -> dict:
    """Get current status of a coaching session."""
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}
    state = await graph.aget_state(config)
    values = state.values

    return {
        "status": values.get("status", ""),
        "current_question_index": values.get("current_question_index", 0),
        "difficulty_level": values.get("difficulty_level", "medium"),
        "session_scores": values.get("session_scores", []),
    }


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------


@router.get("/history")
async def get_history(
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),  # noqa: B008
    repo: InterviewPerformanceRepository = Depends(get_interview_performance_repository),  # noqa: B008
) -> dict:
    """Get recent interview coaching session history with pagination."""
    sessions = await repo.get_user_sessions(user.id, skip=skip, limit=limit)
    total = await repo.count_user_sessions(user.id)
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "company_name": s.company_name,
                "role_title": s.role_title,
                "overall_score": s.overall_score,
                "question_count": len(s.question_scores),
                "created_at": str(s.created_at) if s.created_at else None,
            }
            for s in sessions
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/history/{session_id}")
async def get_session_detail(
    session_id: str,
    user: User = Depends(get_current_user),  # noqa: B008
    repo: InterviewPerformanceRepository = Depends(get_interview_performance_repository),  # noqa: B008
) -> dict:
    """Get full details for a specific coaching session."""
    session = await repo.get_by_session(user.id, session_id)
    if not session:
        raise NotFoundError("Interview performance session")
    return session.model_dump(by_alias=True)


@router.get("/trends")
async def get_trends(
    user: User = Depends(get_current_user),  # noqa: B008
    repo: InterviewPerformanceRepository = Depends(get_interview_performance_repository),  # noqa: B008
) -> dict:
    """Get interview performance trends with per-category breakdowns."""
    sessions = await repo.get_user_sessions(user.id, limit=100)
    trends = await repo.get_user_trends(user.id, sessions=sessions)
    velocity = await repo.get_improvement_velocity(user.id, sessions=sessions)
    weak_areas = await repo.get_weak_areas(user.id, sessions=sessions)

    return {
        "avg_score_trend": trends["overall_trend"],
        "category_trends": trends["categories"],
        "improvement_velocity": velocity["velocity"],
        "recurring_weaknesses": weak_areas,
        "total_sessions": len(trends["overall_trend"]),
    }


@router.post("/{thread_id}/save", status_code=201)
async def save_session(
    thread_id: str,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_interview_coach_graph),  # noqa: B008
    repo: InterviewPerformanceRepository = Depends(get_interview_performance_repository),  # noqa: B008
) -> dict:
    """Save a completed coaching session as an InterviewPerformance record."""
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}
    state = await graph.aget_state(config)
    values = state.values

    # Guard against duplicate saves — the graph's save_performance node auto-saves
    graph_session_id = values.get("session_id", "")
    if graph_session_id:
        existing = await repo.get_by_session(user.id, graph_session_id)
        if existing:
            return {"session_id": existing.session_id, "overall_score": existing.overall_score}

    session_id = str(uuid.uuid4())
    scores = values.get("session_scores", [])

    question_scores = [
        QuestionScore(
            question_text=s.get("question_text", ""),
            question_type=s.get("question_type", ""),
            score_relevance=s.get("score_relevance", 0),
            score_structure=s.get("score_structure", 0),
            score_specificity=s.get("score_specificity", 0),
            score_confidence=s.get("score_confidence", 0),
            feedback=s.get("feedback", ""),
            improvement_suggestion=s.get("improvement_suggestion", ""),
        )
        for s in scores
    ]

    # Calculate overall score
    total = []
    for qs in question_scores:
        vals = [qs.score_relevance, qs.score_structure, qs.score_specificity, qs.score_confidence]
        if any(vals):
            total.append(sum(vals) / len(vals))
    overall = sum(total) / len(total) if total else 0.0

    perf = InterviewPerformance(
        user_id=user.id,
        session_id=session_id,
        company_name=values.get("company_name", ""),
        role_title=values.get("role_title", ""),
        difficulty_level=values.get("difficulty_level", "medium"),
        question_scores=question_scores,
        overall_score=overall,
        session_summary=values.get("overall_assessment", ""),
    )
    created = await repo.create(perf)
    logger.info("coach_session_saved", session_id=session_id, user_id=str(user.id))
    return {"session_id": session_id, "overall_score": created.overall_score}
