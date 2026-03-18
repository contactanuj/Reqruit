"""
Unit tests for mock interview session routes.

Coverage:
- POST /{interview_id}/mock-sessions — start session (201, 404, 422 no questions)
- GET /{interview_id}/mock-sessions — list sessions
- GET /{interview_id}/mock-sessions/{session_id} — get single session
- POST /{interview_id}/mock-sessions/{session_id}/answer — submit answer
- POST /{interview_id}/mock-sessions/{session_id}/complete — complete session
- DELETE /{interview_id}/mock-sessions/{session_id} — delete session
"""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_interview_repository,
    get_mock_session_repository,
)
from src.db.documents.enums import MockSessionStatus
from src.db.documents.interview import GeneratedQuestion, Interview
from src.db.documents.mock_session import MockInterviewSession, QuestionFeedback

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"
INTERVIEW_ID = "bbbbbbbbbbbbbbbbbbbbbbbb"
SESSION_ID = "cccccccccccccccccccccccc"


def _make_user(user_id: str = USER_ID):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    return user


def _make_interview(
    interview_id: str = INTERVIEW_ID,
    with_questions: bool = True,
):
    interview = MagicMock(spec=Interview)
    interview.id = PydanticObjectId(interview_id)
    interview.user_id = PydanticObjectId(USER_ID)
    interview.application_id = PydanticObjectId("dddddddddddddddddddddddd")
    if with_questions:
        interview.generated_questions = [
            GeneratedQuestion(question="Tell me about a time you led a team.", suggested_angle="Leadership"),
            GeneratedQuestion(question="Describe a challenging bug you fixed.", suggested_angle="Problem-solving"),
        ]
    else:
        interview.generated_questions = []
    return interview


def _make_session(
    session_id: str = SESSION_ID,
    interview_id: str = INTERVIEW_ID,
    status: MockSessionStatus = MockSessionStatus.IN_PROGRESS,
    feedbacks: list | None = None,
    current_index: int = 0,
):
    session = MagicMock(spec=MockInterviewSession)
    session.id = PydanticObjectId(session_id)
    session.user_id = PydanticObjectId(USER_ID)
    session.interview_id = PydanticObjectId(interview_id)
    session.status = status
    session.question_feedbacks = feedbacks or []
    session.current_question_index = current_index
    session.overall_feedback = ""
    session.overall_score = None
    session.created_at = None
    session.updated_at = None
    return session


def _setup(app, mock_interview_repo=None, mock_session_repo=None):
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    if mock_interview_repo:
        app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo
    if mock_session_repo:
        app.dependency_overrides[get_mock_session_repository] = lambda: mock_session_repo


# ---------------------------------------------------------------------------
# Tests: POST /interviews/{id}/mock-sessions — start session
# ---------------------------------------------------------------------------


class TestStartMockSession:
    async def test_start_session_201(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = _make_interview()
        mock_session_repo = AsyncMock()
        mock_session_repo.find_one.return_value = None  # no existing session
        mock_session_repo.create.return_value = _make_session()
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.post(f"/interviews/{INTERVIEW_ID}/mock-sessions")
            assert resp.status_code == 201
            data = resp.json()
            assert data["id"] == SESSION_ID
            assert data["status"] == "in_progress"
            assert data["current_question"] == "Tell me about a time you led a team."
        finally:
            app.dependency_overrides.clear()

    async def test_start_session_idempotent(self, client: AsyncClient):
        """Return existing IN_PROGRESS session instead of creating a new one."""
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = _make_interview()
        existing = _make_session()
        mock_session_repo = AsyncMock()
        mock_session_repo.find_one.return_value = existing
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.post(f"/interviews/{INTERVIEW_ID}/mock-sessions")
            assert resp.status_code == 201
            assert resp.json()["id"] == SESSION_ID
            mock_session_repo.create.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    async def test_start_session_404_interview_not_found(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = None
        mock_session_repo = AsyncMock()
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.post(f"/interviews/{INTERVIEW_ID}/mock-sessions")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_start_session_422_no_questions(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = _make_interview(with_questions=False)
        mock_session_repo = AsyncMock()
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.post(f"/interviews/{INTERVIEW_ID}/mock-sessions")
            assert resp.status_code == 422
            assert resp.json()["error_code"] == "NO_QUESTIONS"
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /interviews/{id}/mock-sessions — list sessions
# ---------------------------------------------------------------------------


class TestListMockSessions:
    async def test_list_sessions_200(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = _make_interview()
        mock_session_repo = AsyncMock()
        mock_session_repo.get_for_interview.return_value = [_make_session()]
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.get(f"/interviews/{INTERVIEW_ID}/mock-sessions")
            assert resp.status_code == 200
            assert len(resp.json()) == 1
        finally:
            app.dependency_overrides.clear()

    async def test_list_sessions_empty(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = _make_interview()
        mock_session_repo = AsyncMock()
        mock_session_repo.get_for_interview.return_value = []
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.get(f"/interviews/{INTERVIEW_ID}/mock-sessions")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_sessions_404_interview_not_found(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = None
        mock_session_repo = AsyncMock()
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.get(f"/interviews/{INTERVIEW_ID}/mock-sessions")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /interviews/{id}/mock-sessions/{session_id} — get session
# ---------------------------------------------------------------------------


class TestGetMockSession:
    async def test_get_session_200(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = _make_session()
        _setup(app, mock_session_repo=mock_session_repo)

        try:
            resp = await client.get(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}"
            )
            assert resp.status_code == 200
            assert resp.json()["id"] == SESSION_ID
        finally:
            app.dependency_overrides.clear()

    async def test_get_session_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_session_repo=mock_session_repo)

        try:
            resp = await client.get(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}"
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: POST /{id}/mock-sessions/{sid}/answer — submit answer
# ---------------------------------------------------------------------------


class TestSubmitAnswer:
    async def test_submit_answer_success(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = _make_interview()
        session = _make_session(current_index=0)
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = session
        _setup(app, mock_interview_repo, mock_session_repo)

        with patch(
            "src.agents.interview_prep.MockInterviewer.__call__",
            new_callable=AsyncMock,
            return_value={"score": 7, "feedback": "Good answer."},
        ):
            try:
                resp = await client.post(
                    f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/answer",
                    json={"answer": "I led a team of 5 engineers..."},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["score"] == 7
                assert data["ai_feedback"] == "Good answer."
                assert data["session_complete"] is False
                assert data["next_question"] == "Describe a challenging bug you fixed."
            finally:
                app.dependency_overrides.clear()

    async def test_submit_answer_last_question(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = _make_interview()
        session = _make_session(current_index=1)  # last question (index 1 of 2)
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = session
        _setup(app, mock_interview_repo, mock_session_repo)

        with patch(
            "src.agents.interview_prep.MockInterviewer.__call__",
            new_callable=AsyncMock,
            return_value={"score": 9, "feedback": "Excellent."},
        ):
            try:
                resp = await client.post(
                    f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/answer",
                    json={"answer": "I debugged a race condition..."},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["session_complete"] is True
                assert data["next_question"] is None
            finally:
                app.dependency_overrides.clear()

    async def test_submit_answer_404_session_not_found(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.post(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/answer",
                json={"answer": "something"},
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_submit_answer_422_session_completed(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        session = _make_session(status=MockSessionStatus.COMPLETED)
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = session
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.post(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/answer",
                json={"answer": "something"},
            )
            assert resp.status_code == 422
            assert resp.json()["error_code"] == "SESSION_NOT_IN_PROGRESS"
        finally:
            app.dependency_overrides.clear()

    async def test_submit_answer_422_no_more_questions(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = _make_interview()
        session = _make_session(current_index=2)  # past all 2 questions
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = session
        _setup(app, mock_interview_repo, mock_session_repo)

        try:
            resp = await client.post(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/answer",
                json={"answer": "something"},
            )
            assert resp.status_code == 422
            assert resp.json()["error_code"] == "NO_MORE_QUESTIONS"
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: POST /{id}/mock-sessions/{sid}/complete — complete session
# ---------------------------------------------------------------------------


class TestCompleteMockSession:
    async def test_complete_session_success(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        feedback = QuestionFeedback(
            question="Q1", user_answer="A1", ai_feedback="Good", score=7
        )
        session = _make_session(feedbacks=[feedback])
        completed_session = _make_session(
            status=MockSessionStatus.COMPLETED, feedbacks=[feedback]
        )
        completed_session.overall_feedback = "Great overall performance."
        completed_session.overall_score = 75

        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.side_effect = [session, completed_session]
        _setup(app, mock_session_repo=mock_session_repo)

        with patch(
            "src.agents.interview_prep.MockInterviewSummarizer.__call__",
            new_callable=AsyncMock,
            return_value={
                "overall_score": 75,
                "overall_feedback": "Great overall performance.",
            },
        ):
            try:
                resp = await client.post(
                    f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/complete"
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "completed"
                assert data["overall_score"] == 75
                assert "Great overall" in data["overall_feedback"]
            finally:
                app.dependency_overrides.clear()

    async def test_complete_session_422_not_in_progress(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        session = _make_session(status=MockSessionStatus.COMPLETED)
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = session
        _setup(app, mock_session_repo=mock_session_repo)

        try:
            resp = await client.post(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/complete"
            )
            assert resp.status_code == 422
            assert resp.json()["error_code"] == "SESSION_NOT_IN_PROGRESS"
        finally:
            app.dependency_overrides.clear()

    async def test_complete_session_422_no_answers(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        session = _make_session(feedbacks=[])
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = session
        _setup(app, mock_session_repo=mock_session_repo)

        try:
            resp = await client.post(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/complete"
            )
            assert resp.status_code == 422
            assert resp.json()["error_code"] == "NO_ANSWERS"
        finally:
            app.dependency_overrides.clear()

    async def test_complete_session_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_session_repo=mock_session_repo)

        try:
            resp = await client.post(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}/complete"
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: DELETE /{id}/mock-sessions/{sid} — delete session
# ---------------------------------------------------------------------------


class TestDeleteMockSession:
    async def test_delete_session_204(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = _make_session()
        mock_session_repo.delete.return_value = True
        _setup(app, mock_session_repo=mock_session_repo)

        try:
            resp = await client.delete(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}"
            )
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_session_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_session_repo = AsyncMock()
        mock_session_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_session_repo=mock_session_repo)

        try:
            resp = await client.delete(
                f"/interviews/{INTERVIEW_ID}/mock-sessions/{SESSION_ID}"
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_start_session_requires_auth(self, client: AsyncClient):
        """Mock session endpoints require authentication."""
        resp = await client.post(f"/interviews/{INTERVIEW_ID}/mock-sessions")
        assert resp.status_code == 401
