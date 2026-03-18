"""
Application workflow routes (Stage 3: Apply).

Design decisions
----------------
Why SSE for cover letter streaming:
    LLM calls take 5-30 seconds. A blocking HTTP response would time out
    in many reverse proxies (nginx default: 60s). More importantly, SSE
    lets the client show real-time progress: "Analyzing requirements...
    Writing cover letter... Awaiting review." This improves perceived
    performance significantly.

Why the graph starts in the SSE endpoint (not the POST):
    The POST creates the DocumentRecord and returns a thread_id immediately
    (fast, no LLM calls). The SSE endpoint is what opens the SSE connection
    AND starts the graph. This way:
    - The client can immediately open the SSE stream after the POST
    - The graph's output is captured and forwarded over the same SSE connection
    - No need for a separate background task + polling mechanism

    If the client disconnects mid-stream (before interrupt), the graph
    continues until the checkpoint. On reconnect, the SSE endpoint detects
    an existing checkpoint and serves the awaiting_review event immediately.

Why LangGraph interrupt() for HITL (not a separate review collection):
    LangGraph's checkpoint persists the complete graph state at the interrupt
    point. On resume, the graph continues exactly where it left off. This
    means the cover letter content, requirements analysis, and all context
    are preserved without extra storage or complex state management.

The thread_id lifecycle:
    1. POST /cover-letter -> creates DocumentRecord with thread_id=uuid4()
    2. GET /cover-letter/stream -> runs graph with config={thread_id: X}
    3. Graph hits interrupt() -> SSE emits awaiting_review -> stream closes
    4. POST /cover-letter/review -> graph.ainvoke(Command(resume=...), config)
    5. On approve -> DocumentRecord.is_approved=True, content saved
    6. On revise -> thread continues, client re-opens SSE stream
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel

from src.api.dependencies import (
    get_application_repository,
    get_cover_letter_graph,
    get_current_user,
    get_document_repository,
    get_job_repository,
    get_llm_usage_repository,
    get_resume_repository,
)
from src.core.config import get_settings
from src.core.exceptions import (
    AuthorizationError,
    BusinessValidationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from src.db.documents.document_record import DocumentRecord
from src.db.documents.enums import DocumentType
from src.db.documents.user import User
from src.repositories.application_repository import ApplicationRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.job_repository import JobRepository
from src.repositories.llm_usage_repository import LLMUsageRepository
from src.repositories.resume_repository import ResumeRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/apply", tags=["apply"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class StartCoverLetterRequest(BaseModel):
    resume_id: str | None = None  # defaults to master resume


class ReviewRequest(BaseModel):
    thread_id: str
    action: str  # "approve" | "revise"
    feedback: str = ""


class DocumentSummary(BaseModel):
    id: str
    doc_type: str
    version: int
    is_approved: bool
    content_preview: str  # first 200 chars
    created_at: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_application_or_403(
    application_id: str,
    current_user: User,
    app_repo: ApplicationRepository,
):
    """Fetch application verifying ownership. Raises 404 or 403."""
    application = await app_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(application_id)
    )
    if not application:
        raise NotFoundError("Application", application_id)
    return application


async def _get_thread_document_or_error(
    thread_id: str,
    current_user: User,
    doc_repo: DocumentRepository,
) -> DocumentRecord:
    """Fetch DocumentRecord by thread_id verifying ownership. Raises 403 or 404."""
    doc = await doc_repo.get_by_thread_id_and_user(thread_id, current_user.id)
    if doc:
        return doc
    exists = await doc_repo.get_by_thread_id(thread_id)
    if exists:
        # Security audit: thread exists but belongs to a different user.
        # Returning 403 (not 404) is an intentional design choice per AC #2
        # that trades minimal info leak for better client-side error handling.
        logger.warning(
            "thread_ownership_violation",
            thread_id=thread_id,
            user_id=str(current_user.id),
        )
        raise AuthorizationError("Insufficient permissions")
    raise NotFoundError("Document", thread_id)


def _format_sse_event(payload: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(payload)}\n\n"


async def _get_resume_text(
    resume_id: str | None,
    user_id: PydanticObjectId,
    resume_repo: ResumeRepository,
) -> str:
    """Get raw_text from specified resume or master resume."""
    if resume_id:
        resume = await resume_repo.get_by_id(PydanticObjectId(resume_id))
        if not resume or resume.user_id != user_id:
            raise NotFoundError("Resume", resume_id)
        return resume.raw_text or ""
    master = await resume_repo.get_master_resume(user_id)
    return master.raw_text if master else ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/applications/{application_id}/documents", response_model=list[DocumentSummary])
async def list_documents(
    application_id: str,
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    doc_repo: DocumentRepository = Depends(get_document_repository),
) -> list[DocumentSummary]:
    """List all AI-generated documents for an application."""
    await _get_application_or_403(application_id, current_user, app_repo)
    docs = await doc_repo.get_for_application(PydanticObjectId(application_id))
    return [
        DocumentSummary(
            id=str(d.id),
            doc_type=d.doc_type,
            version=d.version,
            is_approved=d.is_approved,
            content_preview=d.content[:200] if d.content else "",
            created_at=d.created_at.isoformat() if d.created_at else None,
        )
        for d in docs
    ]


@router.post("/applications/{application_id}/cover-letter", status_code=202)
async def start_cover_letter(
    application_id: str,
    body: StartCoverLetterRequest,
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    doc_repo: DocumentRepository = Depends(get_document_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    llm_usage_repo: LLMUsageRepository = Depends(get_llm_usage_repository),
) -> dict:
    """
    Start the cover letter generation workflow.

    Returns 202 with thread_id immediately. Open the /stream endpoint to
    receive real-time events and the final draft.
    """
    application = await _get_application_or_403(application_id, current_user, app_repo)

    job = await job_repo.get_by_id(application.job_id)
    if not job:
        raise NotFoundError("Job", str(application.job_id))

    # Duplicate detection: block if a generation is already in-progress
    in_progress = await doc_repo.get_in_progress_for_application(
        PydanticObjectId(application_id), DocumentType.COVER_LETTER
    )
    if in_progress:
        logger.warning(
            "duplicate_generation_blocked",
            application_id=application_id,
            existing_thread_id=in_progress.thread_id,
        )
        raise ConflictError(
            detail=f"A cover letter generation is already in progress (thread_id: {in_progress.thread_id})",
            error_code="GENERATION_ALREADY_IN_PROGRESS",
        )

    # Rate limit check: enforce per-user LLM request budget
    settings = get_settings()
    since = datetime.now(UTC) - timedelta(
        seconds=settings.rate_limit.rate_limit_window_seconds
    )
    request_count = await llm_usage_repo.count_recent_for_user(
        current_user.id, since
    )
    if request_count >= settings.rate_limit.max_llm_requests_per_hour:
        logger.warning(
            "rate_limit_exceeded",
            user_id=str(current_user.id),
            request_count=request_count,
            limit=settings.rate_limit.max_llm_requests_per_hour,
            window_seconds=settings.rate_limit.rate_limit_window_seconds,
        )
        raise RateLimitError(
            "Per-user LLM request rate limit exceeded",
            "RATE_LIMITED",
            retry_after=settings.rate_limit.rate_limit_window_seconds,
        )

    thread_id = str(uuid4())

    resume_id = PydanticObjectId(body.resume_id) if body.resume_id else None
    doc = DocumentRecord(
        user_id=current_user.id,
        application_id=PydanticObjectId(application_id),
        doc_type=DocumentType.COVER_LETTER,
        thread_id=thread_id,
        resume_id=resume_id,
    )
    doc = await doc_repo.create_versioned(doc)

    logger.info(
        "cover_letter_started",
        user_id=str(current_user.id),
        application_id=application_id,
        thread_id=thread_id,
        version=doc.version,
    )
    return {
        "thread_id": thread_id,
        "document_id": str(doc.id),
        "version": doc.version,
        "status": "started",
    }


@router.get("/applications/{application_id}/cover-letter/stream")
async def stream_cover_letter(
    application_id: str,
    thread_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    doc_repo: DocumentRepository = Depends(get_document_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    graph=Depends(get_cover_letter_graph),
) -> StreamingResponse:
    """
    SSE stream for cover letter generation with reconnect support.

    On first call the graph runs from start with the job + resume context.
    On reconnect the endpoint detects an existing checkpoint and adapts:
      - Graph completed → emits a single ``completed`` event.
      - Graph paused at ``human_review`` interrupt → emits ``awaiting_review``
        with the saved draft content (no graph re-execution).
      - Graph in-flight at another node → resumes from the last checkpoint.

    Events:
        {"event": "node_complete", "node": "analyze_requirements"}
        {"event": "awaiting_review", "cover_letter": "...", "thread_id": "..."}
        {"event": "completed", "thread_id": "..."}
        {"event": "error", "detail": "..."}
    """
    # --- Ownership validation (must run BEFORE checkpoint detection) ---
    application = await _get_application_or_403(application_id, current_user, app_repo)
    thread_doc = await _get_thread_document_or_error(thread_id, current_user, doc_repo)
    if thread_doc.application_id != PydanticObjectId(application_id):
        raise AuthorizationError("Insufficient permissions")

    config = {"configurable": {"thread_id": thread_id, "user_id": str(current_user.id)}}

    # --- Checkpoint state detection ---
    snapshot = await graph.aget_state(config)

    sse_headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
    }

    # Case 1: Graph completed (terminal state — values populated, no pending nodes)
    if snapshot.values and snapshot.next is not None and len(snapshot.next) == 0:
        logger.info(
            "sse_reconnect_detected",
            thread_id=thread_id,
            checkpoint_next=str(snapshot.next),
            reconnect_type="completed",
        )

        async def completed_generator():
            yield _format_sse_event({"event": "completed", "thread_id": thread_id})

        return StreamingResponse(
            completed_generator(), media_type="text/event-stream", headers=sse_headers
        )

    # Case 2: Graph paused at human_review interrupt
    if snapshot.next and "human_review" in snapshot.next:
        logger.info(
            "sse_reconnect_detected",
            thread_id=thread_id,
            checkpoint_next=str(snapshot.next),
            reconnect_type="awaiting_review",
        )

        async def awaiting_review_generator():
            yield _format_sse_event(
                {
                    "event": "awaiting_review",
                    "cover_letter": snapshot.values.get("cover_letter", ""),
                    "requirements_analysis": snapshot.values.get(
                        "requirements_analysis", ""
                    ),
                    "thread_id": thread_id,
                }
            )

        return StreamingResponse(
            awaiting_review_generator(),
            media_type="text/event-stream",
            headers=sse_headers,
        )

    # Case 3: Graph in-flight at a different node — resume from checkpoint
    if snapshot.next and snapshot.values:
        logger.info(
            "sse_reconnect_detected",
            thread_id=thread_id,
            checkpoint_next=str(snapshot.next),
            reconnect_type="in_flight",
        )

        async def resume_generator():
            try:
                async for event in graph.astream(
                    None, config=config, stream_mode="updates"
                ):
                    for node_name, node_output in event.items():
                        if node_name == "__interrupt__":
                            interrupt_value = (
                                node_output[0].value if node_output else {}
                            )
                            yield _format_sse_event(
                                {
                                    "event": "awaiting_review",
                                    "cover_letter": interrupt_value.get(
                                        "cover_letter", ""
                                    ),
                                    "requirements_analysis": interrupt_value.get(
                                        "requirements_analysis", ""
                                    ),
                                    "thread_id": thread_id,
                                }
                            )
                            return
                        else:
                            yield _format_sse_event(
                                {"event": "node_complete", "node": node_name}
                            )
            except Exception as e:
                logger.error(
                    "cover_letter_stream_error", thread_id=thread_id, error=str(e)
                )
                yield _format_sse_event({"event": "error", "detail": "An internal error occurred"})

        return StreamingResponse(
            resume_generator(), media_type="text/event-stream", headers=sse_headers
        )

    # Case 4: Fresh start — no checkpoint exists (empty values)
    logger.info("sse_fresh_start", thread_id=thread_id)

    job = await job_repo.get_by_id(application.job_id)
    if not job:
        raise NotFoundError("Job", str(application.job_id))

    doc = await doc_repo.get_latest(PydanticObjectId(application_id), DocumentType.COVER_LETTER)
    resume_text = await _get_resume_text(
        str(doc.resume_id) if doc and doc.resume_id else None,
        current_user.id,
        resume_repo,
    )

    initial_state = {
        "job_description": job.description or f"{job.title} at {job.company_name}",
        "resume_text": resume_text,
    }

    async def event_generator():
        try:
            async for event in graph.astream(
                initial_state, config=config, stream_mode="updates"
            ):
                for node_name, node_output in event.items():
                    if node_name == "__interrupt__":
                        interrupt_value = node_output[0].value if node_output else {}
                        yield _format_sse_event(
                            {
                                "event": "awaiting_review",
                                "cover_letter": interrupt_value.get(
                                    "cover_letter", ""
                                ),
                                "requirements_analysis": interrupt_value.get(
                                    "requirements_analysis", ""
                                ),
                                "thread_id": thread_id,
                            }
                        )
                        return
                    else:
                        yield _format_sse_event(
                            {"event": "node_complete", "node": node_name}
                        )
        except Exception as e:
            logger.error(
                "cover_letter_stream_error", thread_id=thread_id, error=str(e)
            )
            yield _format_sse_event({"event": "error", "detail": "An internal error occurred"})

    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=sse_headers
    )


@router.post("/applications/{application_id}/cover-letter/review")
async def review_cover_letter(
    application_id: str,
    body: ReviewRequest,
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    doc_repo: DocumentRepository = Depends(get_document_repository),
    graph=Depends(get_cover_letter_graph),
) -> dict:
    """
    Resume the cover letter workflow after human review.

    On approve: marks the document as approved, saves final content.
    On revise: resumes graph with feedback. Client should re-open SSE stream.
    """
    if body.action not in ("approve", "revise"):
        raise BusinessValidationError(
            "Action must be 'approve' or 'revise'", "INVALID_ACTION"
        )

    await _get_application_or_403(application_id, current_user, app_repo)
    thread_doc = await _get_thread_document_or_error(body.thread_id, current_user, doc_repo)
    if thread_doc.application_id != PydanticObjectId(application_id):
        raise AuthorizationError("Insufficient permissions")

    config = {
        "configurable": {"thread_id": body.thread_id, "user_id": str(current_user.id)}
    }

    # Check checkpoint state before attempting resume
    snapshot = await graph.aget_state(config)

    if not snapshot.values:
        logger.warning("review_thread_not_found", thread_id=body.thread_id)
        raise BusinessValidationError(
            "No active workflow session found for this thread",
            "THREAD_NOT_FOUND",
        )

    if not snapshot.next:
        logger.warning("review_thread_expired", thread_id=body.thread_id)
        raise BusinessValidationError(
            "Workflow session has expired or already completed",
            "THREAD_EXPIRED",
        )

    if "human_review" not in snapshot.next:
        logger.warning(
            "review_thread_not_ready",
            thread_id=body.thread_id,
            checkpoint_next=str(snapshot.next),
        )
        raise BusinessValidationError(
            "Workflow is still processing — please wait for the draft to complete",
            "THREAD_NOT_READY",
        )

    if body.action == "approve":
        try:
            result = await graph.ainvoke(
                Command(resume={"action": "approve"}),
                config=config,
            )
        except Exception as e:
            logger.error(
                "cover_letter_approve_error",
                thread_id=body.thread_id,
                error=str(e),
            )
            raise BusinessValidationError(
                "Failed to complete the approval workflow",
                "GRAPH_EXECUTION_ERROR",
            )
        cover_letter = result.get("cover_letter", "")

        doc = await doc_repo.get_latest(
            PydanticObjectId(application_id), DocumentType.COVER_LETTER
        )
        if doc:
            await doc_repo.update(doc.id, {"content": cover_letter, "is_approved": True})

        logger.info(
            "cover_letter_approved",
            application_id=application_id,
            thread_id=body.thread_id,
        )
        return {"status": "approved", "document_id": str(doc.id) if doc else None}

    else:  # revise
        try:
            await graph.ainvoke(
                Command(resume={"action": "revise", "feedback": body.feedback}),
                config=config,
            )
        except Exception as e:
            logger.error(
                "cover_letter_revise_error",
                thread_id=body.thread_id,
                error=str(e),
            )
            raise BusinessValidationError(
                "Failed to resume the revision workflow",
                "GRAPH_EXECUTION_ERROR",
            )
        doc = await doc_repo.get_latest(
            PydanticObjectId(application_id), DocumentType.COVER_LETTER
        )
        if doc:
            await doc_repo.update(doc.id, {"feedback": body.feedback})

        logger.info(
            "cover_letter_revision_requested",
            application_id=application_id,
            feedback_length=len(body.feedback),
        )
        return {"status": "revision_started", "thread_id": body.thread_id}
