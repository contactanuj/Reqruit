"""
Tests for interview coach session setup and prediction endpoints (Story 9.1).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_interview_coach_graph,
    get_interview_performance_repository,
)
from src.api.main import create_app

_user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _fake_user():
    user = MagicMock()
    user.id = _user_id
    return user


@pytest.fixture()
def app():
    application = create_app()
    application.dependency_overrides[get_current_user] = lambda: _fake_user()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# POST /interviews/coach/start
# ---------------------------------------------------------------------------


class TestStartSession:
    async def test_returns_202_with_session_id(self, app, client) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "predicted_questions": "[]",
            "status": "predicting",
        })
        mock_perf_repo = MagicMock()
        mock_perf_repo.count_active_sessions = AsyncMock(return_value=0)

        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph
        app.dependency_overrides[get_interview_performance_repository] = lambda: mock_perf_repo

        response = await client.post(
            "/interviews/coach/start",
            json={"company_name": "Acme", "role_title": "SDE-2"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "thread_id" in data
        assert "session_id" in data
        assert data["status"] == "started"

    async def test_passes_jd_text_into_state(self, app, client) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={})
        mock_perf_repo = MagicMock()
        mock_perf_repo.count_active_sessions = AsyncMock(return_value=0)

        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph
        app.dependency_overrides[get_interview_performance_repository] = lambda: mock_perf_repo

        await client.post(
            "/interviews/coach/start",
            json={"company_name": "Acme", "role_title": "SDE-2", "jd_text": "Build APIs"},
        )

        call_args = mock_graph.ainvoke.call_args
        initial_state = call_args[0][0]
        assert initial_state["jd_analysis"] == "Build APIs"
        assert initial_state["jd_text"] == "Build APIs"

    async def test_passes_job_id_into_state(self, app, client) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={})
        mock_perf_repo = MagicMock()
        mock_perf_repo.count_active_sessions = AsyncMock(return_value=0)

        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph
        app.dependency_overrides[get_interview_performance_repository] = lambda: mock_perf_repo

        await client.post(
            "/interviews/coach/start",
            json={"company_name": "Acme", "role_title": "SDE-2", "job_id": "abc123"},
        )

        call_args = mock_graph.ainvoke.call_args
        initial_state = call_args[0][0]
        assert initial_state["job_id"] == "abc123"

    async def test_returns_429_when_max_sessions(self, app, client) -> None:
        mock_graph = MagicMock()
        mock_perf_repo = MagicMock()
        mock_perf_repo.count_active_sessions = AsyncMock(return_value=3)

        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph
        app.dependency_overrides[get_interview_performance_repository] = lambda: mock_perf_repo

        response = await client.post(
            "/interviews/coach/start",
            json={"company_name": "Acme", "role_title": "SDE-2"},
        )
        assert response.status_code == 429
        assert "MAX_CONCURRENT_SESSIONS" in response.json().get("error_code", "")

    async def test_returns_401_without_auth(self, app, client) -> None:
        # Remove the auth override so it requires real auth
        app.dependency_overrides.pop(get_current_user, None)

        response = await client.post(
            "/interviews/coach/start",
            json={"company_name": "Acme", "role_title": "SDE-2"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /interviews/coach/predict
# ---------------------------------------------------------------------------


class TestPredictEndpoint:
    async def test_returns_200_with_questions(self, app, client) -> None:
        questions = [
            {
                "question_text": "Tell me about yourself",
                "question_type": "behavioral",
                "confidence": "high",
                "difficulty": "easy",
                "suggested_preparation": "Prepare a 2-min summary",
            },
        ]

        with patch("src.api.routes.interview_coach.QuestionPredictorAgent") as MockPredictor:
            mock_instance = AsyncMock(return_value={
                "predicted_questions": json.dumps(questions),
            })
            MockPredictor.return_value = mock_instance

            response = await client.post(
                "/interviews/coach/predict",
                json={"company_name": "Google", "role_title": "SDE-2"},
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["questions"]) == 1
            assert data["questions"][0]["confidence"] == "high"

    async def test_returns_401_without_auth(self, app, client) -> None:
        app.dependency_overrides.pop(get_current_user, None)

        response = await client.post(
            "/interviews/coach/predict",
            json={"company_name": "Google", "role_title": "SDE-2"},
        )
        assert response.status_code == 401

    async def test_handles_non_json_agent_response(self, app, client) -> None:
        with patch("src.api.routes.interview_coach.QuestionPredictorAgent") as MockPredictor:
            mock_instance = AsyncMock(return_value={
                "predicted_questions": "1. Tell me about yourself\n2. Why this company?",
            })
            MockPredictor.return_value = mock_instance

            response = await client.post(
                "/interviews/coach/predict",
                json={"company_name": "Acme", "role_title": "Intern"},
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["questions"]) == 1
            assert "Tell me about yourself" in data["questions"][0]["question_text"]

    async def test_passes_jd_text_to_agent(self, app, client) -> None:
        with patch("src.api.routes.interview_coach.QuestionPredictorAgent") as MockPredictor:
            mock_instance = AsyncMock(return_value={
                "predicted_questions": "[]",
            })
            MockPredictor.return_value = mock_instance

            await client.post(
                "/interviews/coach/predict",
                json={"company_name": "Acme", "role_title": "SDE-2", "jd_text": "Build APIs"},
            )

            call_args = mock_instance.call_args
            state = call_args[0][0]
            assert state["jd_analysis"] == "Build APIs"
