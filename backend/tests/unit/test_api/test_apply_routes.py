"""
Unit tests for cover letter application routes (Stage 3: Apply).

Covers:
  [P1] POST /apply/applications/{id}/cover-letter          — start workflow
  [P1] GET  /apply/applications/{id}/cover-letter/stream   — SSE stream + reconnect
  [P2] GET  /apply/applications/{id}/documents             — list documents
  [P0] POST /apply/applications/{id}/cover-letter/review   — HITL approve/revise

SSE stream tests mock graph.astream as an async generator to simulate LangGraph
event flow without a real LLM or MongoDB connection.

Reconnect test documents the contract stated in apply.py:
  "On reconnect, the SSE endpoint detects an existing checkpoint and serves
   the awaiting_review event immediately."
LangGraph handles this transparently via its checkpointer — when astream() is
called for a thread_id already at an interrupt checkpoint, it emits only the
interrupt event (no prior node_complete events). The reconnect test simulates
this by having the mock yield __interrupt__ as its first and only event.
"""

import json
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_cover_letter_graph,
    get_current_user,
    get_document_repository,
    get_job_repository,
    get_llm_usage_repository,
    get_resume_repository,
)
from src.db.documents.enums import DocumentType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa"):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    return user


def _make_application(
    app_id: str = "222222222222222222222222",
    user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa",
    job_id: str = "111111111111111111111111",
):
    app = MagicMock()
    app.id = PydanticObjectId(app_id)
    app.user_id = PydanticObjectId(user_id)
    app.job_id = PydanticObjectId(job_id)
    return app


def _make_job(job_id: str = "111111111111111111111111"):
    job = MagicMock()
    job.id = PydanticObjectId(job_id)
    job.title = "Senior Engineer"
    job.company_name = "Acme Corp"
    job.description = "Build great things with Python"
    return job


def _make_doc(
    doc_id: str = "333333333333333333333333",
    user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa",
    application_id: str = "222222222222222222222222",
    thread_id: str = "thread-default",
):
    doc = MagicMock()
    doc.id = PydanticObjectId(doc_id)
    doc.user_id = PydanticObjectId(user_id)
    doc.application_id = PydanticObjectId(application_id)
    doc.thread_id = thread_id
    doc.doc_type = DocumentType.COVER_LETTER
    doc.version = 1
    doc.is_approved = False
    doc.content = "Dear Hiring Manager..."
    doc.resume_id = None
    doc.created_at = None
    return doc


def _make_resume():
    resume = MagicMock()
    resume.raw_text = "Experienced engineer with 5 years in Python..."
    return resume


def _parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE response body into a list of event dicts."""
    raw = [line for line in response_text.split("\n\n") if line.startswith("data: ")]
    return [json.loads(line[len("data: "):]) for line in raw]


# ---------------------------------------------------------------------------
# Tests: POST /apply/applications/{id}/cover-letter  [start]
# ---------------------------------------------------------------------------


async def test_start_cover_letter_returns_202_with_thread_id(
    client: AsyncClient,
) -> None:
    """[P1] POST start should create a DocumentRecord and return 202 with thread_id."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_job = _make_job()
    fake_doc = _make_doc()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_doc_repo = AsyncMock()
    mock_doc_repo.create_versioned.return_value = fake_doc
    mock_doc_repo.get_in_progress_for_application = AsyncMock(return_value=None)

    mock_resume_repo = AsyncMock()

    mock_llm_usage_repo = AsyncMock()
    mock_llm_usage_repo.count_recent_for_user = AsyncMock(return_value=0)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: mock_llm_usage_repo

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter",
            json={},
        )
        assert response.status_code == 202
        data = response.json()
        assert "thread_id" in data
        assert len(data["thread_id"]) > 0
        assert "document_id" in data
        assert data["status"] == "started"
        assert data["version"] == 1
        mock_doc_repo.create_versioned.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_start_cover_letter_application_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """[P1] POST start returns 404 when application does not exist for this user."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = None

    mock_job_repo = AsyncMock()
    mock_doc_repo = AsyncMock()
    mock_resume_repo = AsyncMock()
    mock_llm_usage_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: mock_llm_usage_repo

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter",
            json={},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "APPLICATION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_start_cover_letter_job_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """[P1] POST start returns 404 when the application's job record is missing."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = None

    mock_doc_repo = AsyncMock()
    mock_resume_repo = AsyncMock()
    mock_llm_usage_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: mock_llm_usage_repo

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter",
            json={},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "JOB_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: Duplicate detection + rate limiting (Story 3.3)
# ---------------------------------------------------------------------------


async def test_start_cover_letter_duplicate_in_progress_returns_409(
    client: AsyncClient,
) -> None:
    """[P0] POST start with in-progress generation returns 409 GENERATION_ALREADY_IN_PROGRESS."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_job = _make_job()
    existing_doc = _make_doc(thread_id="existing-thread")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_in_progress_for_application = AsyncMock(return_value=existing_doc)

    mock_resume_repo = AsyncMock()
    mock_llm_usage_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: mock_llm_usage_repo

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter",
            json={},
        )
        assert response.status_code == 409
        assert response.json()["error_code"] == "GENERATION_ALREADY_IN_PROGRESS"
        assert "existing-thread" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


async def test_start_cover_letter_no_duplicate_proceeds(
    client: AsyncClient,
) -> None:
    """[P1] POST start with no in-progress doc proceeds to create new document."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_job = _make_job()
    fake_doc = _make_doc()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_in_progress_for_application = AsyncMock(return_value=None)
    mock_doc_repo.create_versioned.return_value = fake_doc

    mock_resume_repo = AsyncMock()

    mock_llm_usage_repo = AsyncMock()
    mock_llm_usage_repo.count_recent_for_user = AsyncMock(return_value=0)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: mock_llm_usage_repo

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter",
            json={},
        )
        assert response.status_code == 202
        mock_doc_repo.create_versioned.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_start_cover_letter_rate_limit_exceeded_returns_429(
    client: AsyncClient,
) -> None:
    """[P0] POST start when rate limit exceeded returns 429 RATE_LIMITED with Retry-After."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_job = _make_job()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_in_progress_for_application = AsyncMock(return_value=None)

    mock_resume_repo = AsyncMock()

    mock_llm_usage_repo = AsyncMock()
    mock_llm_usage_repo.count_recent_for_user = AsyncMock(return_value=10)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: mock_llm_usage_repo

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter",
            json={},
        )
        assert response.status_code == 429
        assert response.json()["error_code"] == "RATE_LIMITED"
        assert "Retry-After" in response.headers
        mock_doc_repo.create_versioned.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_start_cover_letter_under_rate_limit_proceeds(
    client: AsyncClient,
) -> None:
    """[P1] POST start when under rate limit proceeds normally."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_job = _make_job()
    fake_doc = _make_doc()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_in_progress_for_application = AsyncMock(return_value=None)
    mock_doc_repo.create_versioned.return_value = fake_doc

    mock_resume_repo = AsyncMock()

    mock_llm_usage_repo = AsyncMock()
    mock_llm_usage_repo.count_recent_for_user = AsyncMock(return_value=5)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: mock_llm_usage_repo

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter",
            json={},
        )
        assert response.status_code == 202
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /apply/applications/{id}/cover-letter/stream  [SSE]
# ---------------------------------------------------------------------------


async def test_stream_cover_letter_emits_node_complete_then_awaiting_review(
    client: AsyncClient,
) -> None:
    """[P1] SSE stream: fresh start emits node_complete events then awaiting_review on interrupt."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_job = _make_job()
    fake_doc = _make_doc(thread_id="thread-first-run")
    fake_resume = _make_resume()

    interrupt_val = MagicMock()
    interrupt_val.value = {
        "cover_letter": "Dear Hiring Manager, I am excited...",
        "requirements_analysis": "Python, FastAPI, MongoDB required",
    }

    async def _mock_astream(*args, **kwargs):
        yield {"analyze_requirements": {"requirements_analysis": "Python, FastAPI"}}
        yield {"write_cover_letter": {"cover_letter": "Dear Hiring Manager..."}}
        yield {"__interrupt__": [interrupt_val]}

    # Fresh start: aget_state returns empty values (no checkpoint)
    mock_snapshot = MagicMock()
    mock_snapshot.values = {}
    mock_snapshot.next = ()

    mock_graph = MagicMock()
    mock_graph.astream = _mock_astream
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)
    mock_doc_repo.get_latest.return_value = fake_doc

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_master_resume.return_value = fake_resume

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "thread-first-run"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = _parse_sse_events(response.text)
        node_events = [e for e in events if e["event"] == "node_complete"]
        review_events = [e for e in events if e["event"] == "awaiting_review"]

        assert len(node_events) == 2
        assert node_events[0]["node"] == "analyze_requirements"
        assert node_events[1]["node"] == "write_cover_letter"

        assert len(review_events) == 1
        assert review_events[0]["cover_letter"] == "Dear Hiring Manager, I am excited..."
        assert review_events[0]["thread_id"] == "thread-first-run"
        assert "requirements_analysis" in review_events[0]
    finally:
        app.dependency_overrides.clear()


async def test_stream_reconnect_at_human_review_serves_awaiting_review_immediately(
    client: AsyncClient,
) -> None:
    """[P1] AC #1: Reconnect when checkpoint is at human_review interrupt.

    aget_state returns snapshot with next=("human_review",) and populated values.
    Endpoint emits awaiting_review from snapshot.values without calling astream().
    """
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-reconnect-review")

    mock_snapshot = MagicMock()
    mock_snapshot.values = {
        "cover_letter": "Reconnected cover letter draft",
        "requirements_analysis": "Python, distributed systems",
    }
    mock_snapshot.next = ("human_review",)

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
    mock_graph.astream = MagicMock()  # Should NOT be called

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph
    app.dependency_overrides[get_job_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_resume_repository] = lambda: AsyncMock()

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "thread-reconnect-review"},
        )
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        assert len(events) == 1
        assert events[0]["event"] == "awaiting_review"
        assert events[0]["cover_letter"] == "Reconnected cover letter draft"
        assert events[0]["requirements_analysis"] == "Python, distributed systems"
        assert events[0]["thread_id"] == "thread-reconnect-review"

        # graph.astream must NOT have been called
        mock_graph.astream.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_stream_reconnect_in_flight_resumes_from_checkpoint(
    client: AsyncClient,
) -> None:
    """[P1] AC #2: Reconnect when checkpoint is in-flight at a non-interrupt node.

    aget_state returns snapshot with next=("write_cover_letter",) and populated values.
    Endpoint calls graph.astream(None, config) to resume (not initial_state).
    """
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-in-flight")

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"requirements_analysis": "Python, FastAPI"}
    mock_snapshot.next = ("write_cover_letter",)

    interrupt_val = MagicMock()
    interrupt_val.value = {
        "cover_letter": "Resumed draft",
        "requirements_analysis": "Python, FastAPI",
    }

    astream_calls = []

    async def _mock_astream_resume(input_arg, *args, **kwargs):
        astream_calls.append(input_arg)
        yield {"write_cover_letter": {"cover_letter": "Resumed draft"}}
        yield {"__interrupt__": [interrupt_val]}

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
    mock_graph.astream = _mock_astream_resume

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph
    app.dependency_overrides[get_job_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_resume_repository] = lambda: AsyncMock()

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "thread-in-flight"},
        )
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        node_events = [e for e in events if e["event"] == "node_complete"]
        review_events = [e for e in events if e["event"] == "awaiting_review"]

        assert len(node_events) == 1
        assert node_events[0]["node"] == "write_cover_letter"
        assert len(review_events) == 1
        assert review_events[0]["cover_letter"] == "Resumed draft"

        # astream was called with None (resume), not with initial_state
        assert len(astream_calls) == 1
        assert astream_calls[0] is None
    finally:
        app.dependency_overrides.clear()


async def test_stream_reconnect_completed_graph_emits_completed_event(
    client: AsyncClient,
) -> None:
    """[P1] Reconnect when graph already completed (terminal state).

    aget_state returns snapshot with populated values and next=() (no pending nodes).
    Endpoint emits a single completed event.
    """
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-completed")

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"cover_letter": "Final letter", "requirements_analysis": "..."}
    mock_snapshot.next = ()

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
    mock_graph.astream = MagicMock()  # Should NOT be called

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph
    app.dependency_overrides[get_job_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_resume_repository] = lambda: AsyncMock()

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "thread-completed"},
        )
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        assert len(events) == 1
        assert events[0]["event"] == "completed"
        assert events[0]["thread_id"] == "thread-completed"

        mock_graph.astream.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_stream_fresh_start_no_checkpoint_uses_initial_state(
    client: AsyncClient,
) -> None:
    """[P1] Fresh start: aget_state returns empty values, astream called with initial_state."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_job = _make_job()
    fake_doc = _make_doc(thread_id="thread-fresh")
    fake_resume = _make_resume()

    mock_snapshot = MagicMock()
    mock_snapshot.values = {}
    mock_snapshot.next = ()

    astream_calls = []

    interrupt_val = MagicMock()
    interrupt_val.value = {"cover_letter": "Fresh draft", "requirements_analysis": "..."}

    async def _mock_astream_fresh(input_arg, *args, **kwargs):
        astream_calls.append(input_arg)
        yield {"__interrupt__": [interrupt_val]}

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
    mock_graph.astream = _mock_astream_fresh

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)
    mock_doc_repo.get_latest.return_value = fake_doc

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_master_resume.return_value = fake_resume

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "thread-fresh"},
        )
        assert response.status_code == 200

        # astream was called with initial_state dict (not None)
        assert len(astream_calls) == 1
        assert astream_calls[0] is not None
        assert "job_description" in astream_calls[0]
        assert "resume_text" in astream_calls[0]
    finally:
        app.dependency_overrides.clear()


async def test_stream_ownership_validation_runs_before_checkpoint_detection(
    client: AsyncClient,
) -> None:
    """[P0] Ownership checks (403/404) must execute before aget_state is ever called."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    other_users_doc = _make_doc(user_id="bbbbbbbbbbbbbbbbbbbbbbbb")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=None)
    mock_doc_repo.get_by_thread_id = AsyncMock(return_value=other_users_doc)

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock()  # Should NOT be called

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph
    app.dependency_overrides[get_job_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_resume_repository] = lambda: AsyncMock()

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "stolen-thread"},
        )
        assert response.status_code == 403

        # aget_state must NOT have been called — ownership check rejected first
        mock_graph.aget_state.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_stream_cover_letter_emits_error_event_on_graph_exception(
    client: AsyncClient,
) -> None:
    """[P1] SSE stream: graph exception → error event emitted in stream (not 500)."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_job = _make_job()
    fake_doc = _make_doc(thread_id="thread-error")
    fake_resume = _make_resume()

    async def _mock_astream_raises(*args, **kwargs):
        yield {"analyze_requirements": {}}
        raise RuntimeError("LLM provider unavailable")

    # Fresh start: aget_state returns empty values
    mock_snapshot = MagicMock()
    mock_snapshot.values = {}
    mock_snapshot.next = ()

    mock_graph = MagicMock()
    mock_graph.astream = _mock_astream_raises
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)
    mock_doc_repo.get_latest.return_value = fake_doc

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_master_resume.return_value = fake_resume

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "thread-error"},
        )
        # SSE always returns 200 — errors are communicated in-stream
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1
        assert error_events[0]["detail"] == "An internal error occurred"
    finally:
        app.dependency_overrides.clear()


async def test_stream_cover_letter_application_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """[P1] SSE stream returns 404 when application does not exist."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = None

    mock_job_repo = AsyncMock()
    mock_doc_repo = AsyncMock()
    mock_resume_repo = AsyncMock()
    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "any-thread"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "APPLICATION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /apply/applications/{id}/documents
# ---------------------------------------------------------------------------


async def test_list_documents_returns_summaries(client: AsyncClient) -> None:
    """[P2] GET documents returns a list of DocumentSummary for the application."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_for_application.return_value = [fake_doc]

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/documents"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["version"] == 1
        assert data[0]["is_approved"] is False
        assert "content_preview" in data[0]
    finally:
        app.dependency_overrides.clear()


async def test_list_documents_empty_when_application_not_found(
    client: AsyncClient,
) -> None:
    """[P2] GET documents returns 404 when application does not exist."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = None
    mock_doc_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/documents"
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: POST /apply/applications/{id}/cover-letter/review  [HITL]
# ---------------------------------------------------------------------------


async def test_review_cover_letter_approve_marks_document_approved(
    client: AsyncClient,
) -> None:
    """[P0] HITL approve: invokes graph, saves cover letter, sets is_approved=True."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-approve")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"cover_letter": "Draft", "requirements_analysis": "..."}
    mock_snapshot.next = ("human_review",)

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"cover_letter": "Final approved letter"})
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)
    mock_doc_repo.get_latest.return_value = fake_doc
    mock_doc_repo.update = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-approve", "action": "approve"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert "document_id" in data

        # Verify graph was invoked with approve command
        mock_graph.ainvoke.assert_called_once()
        call_args = mock_graph.ainvoke.call_args[0][0]  # first positional arg (Command)
        assert call_args.resume == {"action": "approve"}

        # Verify document updated with content and approval flag
        mock_doc_repo.update.assert_called_once()
        _, update_payload = mock_doc_repo.update.call_args[0]
        assert update_payload["is_approved"] is True
        assert update_payload["content"] == "Final approved letter"
    finally:
        app.dependency_overrides.clear()


async def test_review_cover_letter_revise_returns_revision_started(
    client: AsyncClient,
) -> None:
    """[P0] HITL revise: invokes graph with feedback, stores feedback, returns revision_started."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-revise")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"cover_letter": "Draft", "requirements_analysis": "..."}
    mock_snapshot.next = ("human_review",)

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={})
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)
    mock_doc_repo.get_latest.return_value = fake_doc
    mock_doc_repo.update = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={
                "thread_id": "thread-revise",
                "action": "revise",
                "feedback": "Please be more concise in the opening paragraph.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "revision_started"
        assert data["thread_id"] == "thread-revise"

        # Verify graph was invoked with revise + feedback
        mock_graph.ainvoke.assert_called_once()
        call_args = mock_graph.ainvoke.call_args[0][0]
        assert call_args.resume["action"] == "revise"
        assert call_args.resume["feedback"] == "Please be more concise in the opening paragraph."

        # Verify feedback stored on document
        mock_doc_repo.update.assert_called_once()
        _, update_payload = mock_doc_repo.update.call_args[0]
        assert update_payload["feedback"] == "Please be more concise in the opening paragraph."
    finally:
        app.dependency_overrides.clear()


async def test_review_cover_letter_invalid_action_returns_422(
    client: AsyncClient,
) -> None:
    """[P0] HITL review with action not in (approve, revise) returns 422 INVALID_ACTION."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    mock_app_repo = AsyncMock()
    mock_doc_repo = AsyncMock()
    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-bad", "action": "delete"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_ACTION"
    finally:
        app.dependency_overrides.clear()


async def test_review_cover_letter_application_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """[P0] HITL review returns 404 when application does not exist for this user."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = None
    mock_doc_repo = AsyncMock()
    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-abc", "action": "approve"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "APPLICATION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_review_cover_letter_approve_no_document_returns_null_document_id(
    client: AsyncClient,
) -> None:
    """[P1] HITL approve with no DocumentRecord returns status=approved, document_id=None.

    If doc_repo.get_latest returns None (race condition or deleted document),
    the handler should still return 200 with document_id=None rather than 500.
    The graph was already invoked so the revision loop must not block.
    """
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"cover_letter": "Draft", "requirements_analysis": "..."}
    mock_snapshot.next = ("human_review",)

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"cover_letter": "Approved content"})
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    thread_doc = _make_doc(thread_id="thread-no-doc")

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=thread_doc)
    mock_doc_repo.get_latest.return_value = None  # no document found

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-no-doc", "action": "approve"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["document_id"] is None
        mock_doc_repo.update.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_review_cover_letter_revise_with_empty_feedback_is_accepted(
    client: AsyncClient,
) -> None:
    """[P2] HITL revise with empty feedback string is accepted (feedback field has default='')."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-empty-fb")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"cover_letter": "Draft", "requirements_analysis": "..."}
    mock_snapshot.next = ("human_review",)

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={})
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)
    mock_doc_repo.get_latest.return_value = fake_doc
    mock_doc_repo.update = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-empty-fb", "action": "revise", "feedback": ""},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "revision_started"
    finally:
        app.dependency_overrides.clear()

# ---------------------------------------------------------------------------
# Tests: Review checkpoint validation (Story 3.2)
# ---------------------------------------------------------------------------


async def test_review_checkpoint_not_found_returns_422(
    client: AsyncClient,
) -> None:
    """[P0] Review with no checkpoint (never started / deleted) returns 422 THREAD_NOT_FOUND."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-no-checkpoint")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_snapshot = MagicMock()
    mock_snapshot.values = {}
    mock_snapshot.next = ()

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
    mock_graph.ainvoke = AsyncMock()  # should never be called

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-no-checkpoint", "action": "approve"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "THREAD_NOT_FOUND"
        mock_graph.ainvoke.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_review_checkpoint_expired_returns_422(
    client: AsyncClient,
) -> None:
    """[P0] Review with terminal checkpoint (completed) returns 422 THREAD_EXPIRED."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-expired")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"cover_letter": "Final text", "status": "approved"}
    mock_snapshot.next = ()

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
    mock_graph.ainvoke = AsyncMock()  # should never be called

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-expired", "action": "approve"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "THREAD_EXPIRED"
        mock_graph.ainvoke.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_review_checkpoint_not_ready_returns_422(
    client: AsyncClient,
) -> None:
    """[P0] Review when graph is in-flight (not at human_review) returns 422 THREAD_NOT_READY."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-inflight")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"job_description": "...", "status": "writing"}
    mock_snapshot.next = ("write_cover_letter",)

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
    mock_graph.ainvoke = AsyncMock()  # should never be called

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-inflight", "action": "approve"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "THREAD_NOT_READY"
        mock_graph.ainvoke.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_review_valid_checkpoint_proceeds_to_ainvoke(
    client: AsyncClient,
) -> None:
    """[P0] Review with valid checkpoint at human_review calls graph.ainvoke."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_doc = _make_doc(thread_id="thread-valid")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_snapshot = MagicMock()
    mock_snapshot.values = {"cover_letter": "Draft text", "requirements_analysis": "..."}
    mock_snapshot.next = ("human_review",)

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"cover_letter": "Final text"})
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=fake_doc)
    mock_doc_repo.get_latest.return_value = fake_doc
    mock_doc_repo.update = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "thread-valid", "action": "approve"},
        )
        assert response.status_code == 200
        mock_graph.ainvoke.assert_called_once()
        mock_graph.aget_state.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_review_ownership_runs_before_checkpoint_validation(
    client: AsyncClient,
) -> None:
    """[P0] Ownership 403 is returned before checkpoint validation (aget_state not called)."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    other_users_doc = _make_doc(user_id="bbbbbbbbbbbbbbbbbbbbbbbb")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock()

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=None)
    mock_doc_repo.get_by_thread_id = AsyncMock(return_value=other_users_doc)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "stolen-thread", "action": "approve"},
        )
        assert response.status_code == 403
        mock_graph.aget_state.assert_not_called()
    finally:
        app.dependency_overrides.clear()


async def test_review_404_runs_before_checkpoint_validation(
    client: AsyncClient,
) -> None:
    """[P0] Non-existent thread 404 is returned before checkpoint validation."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_graph = MagicMock()
    mock_graph.aget_state = AsyncMock()

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=None)
    mock_doc_repo.get_by_thread_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "nonexistent-thread", "action": "approve"},
        )
        assert response.status_code == 404
        mock_graph.aget_state.assert_not_called()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: Thread ownership validation (Story 2.4)
# ---------------------------------------------------------------------------


async def test_stream_cover_letter_cross_user_thread_returns_403(
    client: AsyncClient,
) -> None:
    """[P0] AC #2: stream with thread_id belonging to different user returns 403 FORBIDDEN."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    other_users_doc = _make_doc(user_id="bbbbbbbbbbbbbbbbbbbbbbbb")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=None)
    mock_doc_repo.get_by_thread_id = AsyncMock(return_value=other_users_doc)

    mock_job_repo = AsyncMock()
    mock_resume_repo = AsyncMock()
    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "stolen-thread"},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


async def test_stream_cover_letter_nonexistent_thread_returns_404(
    client: AsyncClient,
) -> None:
    """[P0] AC #3: stream with non-existent thread_id returns 404 DOCUMENT_NOT_FOUND."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=None)
    mock_doc_repo.get_by_thread_id = AsyncMock(return_value=None)

    mock_job_repo = AsyncMock()
    mock_resume_repo = AsyncMock()
    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "nonexistent-thread"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "DOCUMENT_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_stream_cover_letter_thread_application_mismatch_returns_403(
    client: AsyncClient,
) -> None:
    """[P0] Stream with thread_id owned by user but linked to different application returns 403."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    mismatched_doc = _make_doc(application_id="444444444444444444444444")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=mismatched_doc)

    mock_job_repo = AsyncMock()
    mock_resume_repo = AsyncMock()
    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.get(
            "/apply/applications/222222222222222222222222/cover-letter/stream",
            params={"thread_id": "mismatched-thread"},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


async def test_review_cover_letter_cross_user_thread_returns_403(
    client: AsyncClient,
) -> None:
    """[P0] AC #2: review with thread_id belonging to different user returns 403 FORBIDDEN."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    other_users_doc = _make_doc(user_id="bbbbbbbbbbbbbbbbbbbbbbbb")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=None)
    mock_doc_repo.get_by_thread_id = AsyncMock(return_value=other_users_doc)

    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "stolen-thread", "action": "approve"},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


async def test_review_cover_letter_nonexistent_thread_returns_404(
    client: AsyncClient,
) -> None:
    """[P0] AC #3: review with non-existent thread_id returns 404 DOCUMENT_NOT_FOUND."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=None)
    mock_doc_repo.get_by_thread_id = AsyncMock(return_value=None)

    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "nonexistent-thread", "action": "approve"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "DOCUMENT_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_review_cover_letter_thread_application_mismatch_returns_403(
    client: AsyncClient,
) -> None:
    """[P0] Review with thread_id owned by user but linked to different application returns 403."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    mismatched_doc = _make_doc(
        thread_id="mismatched-thread", application_id="444444444444444444444444"
    )

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_by_thread_id_and_user = AsyncMock(return_value=mismatched_doc)

    mock_graph = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_cover_letter_graph] = lambda: mock_graph

    try:
        response = await client.post(
            "/apply/applications/222222222222222222222222/cover-letter/review",
            json={"thread_id": "mismatched-thread", "action": "approve"},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()
