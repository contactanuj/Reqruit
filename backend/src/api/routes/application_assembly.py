"""
Application assembly routes: orchestrated application pipeline + success analytics.

Endpoints power the Application Assembly Line (Module 13 / Phase 2).
All require JWT auth.
"""

import json
import uuid
from typing import Literal

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel, model_validator

from src.agents.success_pattern import SuccessPatternAgent
from src.api.dependencies import (
    get_application_assembly_graph,
    get_application_repository,
    get_current_user,
    get_skills_profile_repository,
    get_success_analytics_service,
)
from src.core.exceptions import BusinessValidationError, ConflictError, NotFoundError
from src.db.documents.application import Application
from src.db.documents.enums import ApplicationStatus
from src.db.documents.user import User
from src.repositories.application_repository import ApplicationRepository
from src.repositories.skills_profile_repository import SkillsProfileRepository
from src.services.success_analytics import SuccessAnalyticsService, confidence_level

logger = structlog.get_logger()

router = APIRouter(prefix="/applications", tags=["application-assembly"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class StartAssemblyRequest(BaseModel):
    """Start an application assembly pipeline."""

    job_url: str | None = None
    jd_text: str | None = None

    @model_validator(mode="after")
    def at_least_one_input(self) -> "StartAssemblyRequest":
        if not self.job_url and not self.jd_text:
            raise ValueError("Provide at least one of job_url or jd_text")
        return self


class StartAssemblyResponse(BaseModel):
    """Response from starting an assembly."""

    thread_id: str
    application_id: str


class SaveApplicationRequest(BaseModel):
    """Save approved assembly as an application."""

    submission_method: str = ""


class ReviewActionRequest(BaseModel):
    """Review action for an assembly at human_review gate."""

    thread_id: str
    action: Literal["approve", "revise", "reject"]
    feedback: str = ""


class EditApplicationRequest(BaseModel):
    """Direct content edits to an assembly at review gate."""

    tailored_resume: str | None = None
    cover_letter: str | None = None
    micro_pitch: str | None = None


# ---------------------------------------------------------------------------
# Assembly endpoints
# ---------------------------------------------------------------------------


@router.post("/build", status_code=202, response_model=StartAssemblyResponse)
async def start_assembly(
    body: StartAssemblyRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_application_assembly_graph),  # noqa: B008
    skills_repo: SkillsProfileRepository = Depends(get_skills_profile_repository),  # noqa: B008
    app_repo: ApplicationRepository = Depends(get_application_repository),  # noqa: B008
) -> StartAssemblyResponse:
    """Start an application assembly pipeline for a job.

    AC #1: Returns 202 with thread_id and application_id.
    AC #4: Returns 422 PROFILE_NOT_BUILT if no SkillsProfile.
    AC #5: Returns 409 GENERATION_ALREADY_IN_PROGRESS if duplicate.
    """
    # AC #4: Validate SkillsProfile exists
    profile = await skills_repo.get_by_user(user.id)
    if not profile:
        raise BusinessValidationError(
            "Complete your skills profile before building applications",
            error_code="PROFILE_NOT_BUILT",
        )

    # AC #5: Check for existing in-progress assembly for same user
    existing = await app_repo.find_in_progress_assembly(user.id)
    if existing:
        raise ConflictError(
            detail="Application assembly already in progress",
            error_code="GENERATION_ALREADY_IN_PROGRESS",
        )

    thread_id = str(uuid.uuid4())

    # Create Application document to track this assembly
    application = Application(
        user_id=user.id,
        job_id=PydanticObjectId(),  # placeholder — real job_id resolved after JD decode
        thread_id=thread_id,
    )
    created = await app_repo.create(application)

    jd_text = body.jd_text or ""
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}

    initial_state = {
        "messages": [],
        "job_id": str(created.id),
        "job_url": body.job_url or "",
        "jd_text": jd_text,
        "resume_text": "",
        "job_description": jd_text,
        "decoded_jd": "",
        "fit_analysis": "",
        "skills_summary": profile.summary or "",
        "locale_context": "",
        "selected_resume_blocks": "",
        "application_strategy": "",
        "tailored_resume": "",
        "cover_letter": "",
        "micro_pitch": "",
        "feedback": "",
        "status": "pending",
        "resume_block_fallback": False,
        "star_stories_available": False,
        "application_id": str(created.id),
        "thread_id": thread_id,
    }

    # Use ainvoke — graph will pause at human_review interrupt
    await graph.ainvoke(initial_state, config=config)
    logger.info(
        "assembly_started",
        thread_id=thread_id,
        application_id=str(created.id),
        user_id=str(user.id),
    )
    return StartAssemblyResponse(thread_id=thread_id, application_id=str(created.id))


@router.get("/build/stream")
async def stream_assembly(
    thread_id: str = Query(...),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_application_assembly_graph),  # noqa: B008
) -> StreamingResponse:
    """SSE stream for assembly progress events with checkpoint reconnect.

    Detects checkpoint state and emits appropriate events:
    - Completed graph → completed event
    - Paused at human_review → awaiting_review with full package
    - Fresh/in-progress → status + state events
    """
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}

    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        raise NotFoundError("Assembly thread", thread_id)

    def _format_sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, default=str)}\n\n"

    # Case 1: Graph completed
    if snapshot.values and snapshot.next is not None and len(snapshot.next) == 0:
        async def completed_gen():
            yield _format_sse({"event": "completed", "thread_id": thread_id})
        return StreamingResponse(completed_gen(), media_type="text/event-stream")

    # Case 2: Graph paused at human_review interrupt
    if snapshot.next and "human_review" in snapshot.next:
        async def awaiting_review_gen():
            yield _format_sse({
                "event": "awaiting_review",
                "tailored_resume": snapshot.values.get("tailored_resume", ""),
                "cover_letter": snapshot.values.get("cover_letter", ""),
                "micro_pitch": snapshot.values.get("micro_pitch", ""),
                "fit_analysis": snapshot.values.get("fit_analysis", ""),
                "application_strategy": snapshot.values.get("application_strategy", ""),
                "thread_id": thread_id,
            })
        return StreamingResponse(awaiting_review_gen(), media_type="text/event-stream")

    # Case 3: Status/state snapshot
    async def generate():
        values = snapshot.values
        status = values.get("status", "pending")
        yield _format_sse({"event": "status", "status": status})
        yield _format_sse({
            "event": "state",
            "decoded_jd": values.get("decoded_jd", ""),
            "fit_analysis": values.get("fit_analysis", ""),
            "status": status,
            "thread_id": thread_id,
        })
        yield _format_sse({"event": "completed", "thread_id": thread_id})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/build/{thread_id}/status")
async def get_assembly_status(
    thread_id: str,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_application_assembly_graph),  # noqa: B008
) -> dict:
    """Get current status of an assembly pipeline."""
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}
    state = await graph.aget_state(config)
    values = state.values

    return {
        "status": values.get("status", ""),
        "outputs": {
            "decoded_jd": values.get("decoded_jd", ""),
            "fit_analysis": values.get("fit_analysis", ""),
            "application_strategy": values.get("application_strategy", ""),
            "tailored_resume": values.get("tailored_resume", ""),
            "cover_letter": values.get("cover_letter", ""),
        },
    }


@router.post("/build/{thread_id}/save", status_code=201)
async def save_assembly(
    thread_id: str,
    body: SaveApplicationRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_application_assembly_graph),  # noqa: B008
    app_repo: ApplicationRepository = Depends(get_application_repository),  # noqa: B008
) -> dict:
    """Save an approved assembly as an Application document."""
    config = {"configurable": {"thread_id": thread_id, "user_id": str(user.id)}}
    state = await graph.aget_state(config)
    values = state.values

    job_id_str = values.get("job_id")
    if not job_id_str:
        raise NotFoundError("job_id in assembly state")

    application = Application(
        user_id=user.id,
        job_id=PydanticObjectId(job_id_str),
        submission_method=body.submission_method,
        tailoring_strategy=values.get("application_strategy", "")[:500],
    )
    created = await app_repo.create(application)
    logger.info("assembly_saved", application_id=str(created.id), user_id=str(user.id))
    return {"application_id": str(created.id), "status": "saved"}


# ---------------------------------------------------------------------------
# Review endpoints (Story 7.4)
# ---------------------------------------------------------------------------


@router.post("/build/review")
async def review_assembly(
    body: ReviewActionRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_application_assembly_graph),  # noqa: B008
    app_repo: ApplicationRepository = Depends(get_application_repository),  # noqa: B008
) -> dict:
    """Review an assembly at the human_review gate.

    AC #2: approve → status approved, graph completes.
    AC #4: revise → graph routes back to tailor_resume with feedback.
    AC #5: reject → status rejected, graph completes.
    """
    # Verify thread ownership before checkpoint access
    owned_app = await app_repo.find_one({"thread_id": body.thread_id, "user_id": user.id})
    if not owned_app:
        raise NotFoundError("Assembly thread", body.thread_id)

    config = {"configurable": {"thread_id": body.thread_id, "user_id": str(user.id)}}

    # Checkpoint state validation (from apply.py pattern)
    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        raise BusinessValidationError(
            "No active workflow session found", error_code="THREAD_NOT_FOUND"
        )
    if not snapshot.next:
        raise BusinessValidationError(
            "Workflow has expired or completed", error_code="THREAD_EXPIRED"
        )
    if "human_review" not in snapshot.next:
        raise BusinessValidationError(
            "Workflow is still processing", error_code="THREAD_NOT_READY"
        )

    result = await graph.ainvoke(
        Command(resume={"action": body.action, "feedback": body.feedback}),
        config=config,
    )

    # Update Application document status
    app_id = snapshot.values.get("application_id")
    if app_id:
        app = await app_repo.get_by_user_and_id(user.id, PydanticObjectId(app_id))
        if app:
            if body.action == "approve":
                await app_repo.update(app.id, {"status": ApplicationStatus.APPLIED})
            elif body.action == "reject":
                await app_repo.update(app.id, {"status": ApplicationStatus.WITHDRAWN})

    logger.info(
        "assembly_reviewed",
        thread_id=body.thread_id,
        action=body.action,
        user_id=str(user.id),
    )
    return {"status": result.get("status", ""), "thread_id": body.thread_id}


@router.patch("/{application_id}")
async def edit_application(
    application_id: str,
    body: EditApplicationRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_application_assembly_graph),  # noqa: B008
    app_repo: ApplicationRepository = Depends(get_application_repository),  # noqa: B008
) -> dict:
    """Edit assembly content via checkpoint state update (AC #3)."""
    app = await app_repo.get_by_user_and_id(user.id, PydanticObjectId(application_id))
    if not app:
        raise NotFoundError("Application", application_id)

    config = {"configurable": {"thread_id": app.thread_id, "user_id": str(user.id)}}

    # Only allow edits while graph is paused at human_review
    snapshot = await graph.aget_state(config)
    if not snapshot.next or "human_review" not in snapshot.next:
        raise BusinessValidationError(
            "Can only edit while assembly is paused at review",
            error_code="EDIT_NOT_ALLOWED",
        )

    updates = body.model_dump(exclude_none=True)
    if updates:
        await graph.aupdate_state(config, updates)

    logger.info(
        "assembly_edited",
        application_id=application_id,
        updated_fields=list(updates.keys()),
        user_id=str(user.id),
    )
    return {"updated_fields": list(updates.keys()), "application_id": application_id}


@router.get("/{application_id}")
async def get_application(
    application_id: str,
    user: User = Depends(get_current_user),  # noqa: B008
    graph: CompiledStateGraph = Depends(get_application_assembly_graph),  # noqa: B008
    app_repo: ApplicationRepository = Depends(get_application_repository),  # noqa: B008
) -> dict:
    """Get full application package from checkpoint state (AC #8)."""
    app = await app_repo.get_by_user_and_id(user.id, PydanticObjectId(application_id))
    if not app:
        raise NotFoundError("Application", application_id)

    config = {"configurable": {"thread_id": app.thread_id, "user_id": str(user.id)}}
    state = await graph.aget_state(config)
    values = state.values or {}

    return {
        "application_id": application_id,
        "status": values.get("status", ""),
        "tailored_resume": values.get("tailored_resume", ""),
        "cover_letter": values.get("cover_letter", ""),
        "micro_pitch": values.get("micro_pitch", ""),
        "fit_analysis": values.get("fit_analysis", ""),
        "application_strategy": values.get("application_strategy", ""),
        "decoded_jd": values.get("decoded_jd", ""),
    }


@router.delete("/{application_id}", status_code=204)
async def delete_application(
    application_id: str,
    user: User = Depends(get_current_user),  # noqa: B008
    app_repo: ApplicationRepository = Depends(get_application_repository),  # noqa: B008
) -> Response:
    """Delete an application (AC #9)."""
    app = await app_repo.get_by_user_and_id(user.id, PydanticObjectId(application_id))
    if not app:
        raise NotFoundError("Application", application_id)

    await app_repo.delete(app.id)
    logger.info("assembly_deleted", application_id=application_id, user_id=str(user.id))
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------


@router.get("/analytics/response-rate")
async def get_response_rate(
    user: User = Depends(get_current_user),  # noqa: B008
    service: SuccessAnalyticsService = Depends(get_success_analytics_service),  # noqa: B008
) -> dict:
    """Get overall response rate and breakdown by submission method."""
    return await service.get_response_rate(user.id)


@router.get("/analytics/strategies")
async def get_strategies(
    user: User = Depends(get_current_user),  # noqa: B008
    service: SuccessAnalyticsService = Depends(get_success_analytics_service),  # noqa: B008
) -> dict:
    """Get best-performing tailoring strategies ranked by response rate."""
    return await service.get_best_performing_strategies(user.id)


@router.get("/analytics/response-time")
async def get_response_time(
    user: User = Depends(get_current_user),  # noqa: B008
    service: SuccessAnalyticsService = Depends(get_success_analytics_service),  # noqa: B008
) -> dict:
    """Get average days to first employer response."""
    return await service.get_avg_response_time(user.id)


@router.post("/analytics/insights")
async def get_insights(
    user: User = Depends(get_current_user),  # noqa: B008
    service: SuccessAnalyticsService = Depends(get_success_analytics_service),  # noqa: B008
) -> dict:
    """Generate AI-powered insights from application outcome data."""
    rate_data = await service.get_response_rate(user.id)
    strategy_data = await service.get_best_performing_strategies(user.id)
    time_data = await service.get_avg_response_time(user.id)

    analytics_summary = str({
        "response_rate": rate_data,
        "strategies": strategy_data,
        "response_time": time_data,
    })

    agent = SuccessPatternAgent()
    result = await agent({"analytics_data": analytics_summary})
    return result


# ---------------------------------------------------------------------------
# Strategy Insights (Story 8.3)
# ---------------------------------------------------------------------------

_GENERIC_RECOMMENDATIONS = [
    "Track at least 10 applications to get meaningful insights",
    "Vary your resume and cover letter strategies across applications",
    "Submit applications on weekday mornings for best visibility",
]


@router.get("/analytics/strategy")
async def get_strategy_insights(
    user: User = Depends(get_current_user),  # noqa: B008
    service: SuccessAnalyticsService = Depends(get_success_analytics_service),  # noqa: B008
) -> dict:
    """Get strategy insights with AI narrative and timing analysis."""
    rate_data = await service.get_response_rate(user.id)

    if rate_data["total"] < 5:
        return {
            "data_driven": False,
            "confidence": "insufficient",
            "recommendations": _GENERIC_RECOMMENDATIONS,
            "top_resume_strategy": None,
            "top_cover_letter_strategy": None,
            "timing_analysis": [],
            "ai_narrative": "",
        }

    strategy_data = await service.get_strategy_comparison(user.id)
    timing_data = await service.get_timing_analysis(user.id)

    analytics_summary = str({
        "response_rate": rate_data,
        "strategies": strategy_data,
        "timing": timing_data,
    })

    agent = SuccessPatternAgent()
    result = await agent({"analytics_data": analytics_summary})

    return {
        "data_driven": True,
        "confidence": strategy_data["confidence"],
        "top_resume_strategy": (
            strategy_data["resume_strategies"][0]
            if strategy_data["resume_strategies"]
            else None
        ),
        "top_cover_letter_strategy": (
            strategy_data["cover_letter_strategies"][0]
            if strategy_data["cover_letter_strategies"]
            else None
        ),
        "timing_analysis": timing_data["windows"][:5],
        "recommendations": [],
        "ai_narrative": result.get("success_insights", ""),
    }


# ---------------------------------------------------------------------------
# A/B Version Comparison (Story 8.4)
# ---------------------------------------------------------------------------

_ALLOWED_COMPARE_BY = {"resume_strategy", "cover_letter_strategy"}


@router.get("/analytics/compare")
async def compare_versions(
    compare_by: str = Query("resume_strategy"),
    user: User = Depends(get_current_user),  # noqa: B008
    service: SuccessAnalyticsService = Depends(get_success_analytics_service),  # noqa: B008
) -> dict:
    """Compare performance across resume or cover letter strategy variants."""
    if compare_by not in _ALLOWED_COMPARE_BY:
        raise BusinessValidationError(
            detail=f"compare_by must be one of: {', '.join(sorted(_ALLOWED_COMPARE_BY))}",
            error_code="INVALID_COMPARE_BY",
        )
    return await service.get_ab_comparison(user.id, compare_by)
