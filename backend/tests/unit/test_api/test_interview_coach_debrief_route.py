"""
Tests for GET /interviews/coach/{thread_id}/debrief endpoint (Story 9.3).
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_interview_coach_graph,
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


class TestGetDebrief:
    async def test_returns_assessment_when_complete(self, app, client) -> None:
        mock_graph = MagicMock()
        state = MagicMock()
        state.values = {
            "status": "complete",
            "overall_assessment": json.dumps({
                "summary": "Great session",
                "strengths": ["Clear communication"],
                "weaknesses": ["Needs more detail"],
                "recommendations": ["Quantify results"],
                "overall_score": 3.8,
                "question_count": 5,
            }),
            "session_scores": [{"question_text": "Q1", "score_relevance": 4}],
            "company_name": "TestCorp",
            "role_title": "SWE",
            "difficulty_level": "medium",
        }
        mock_graph.aget_state = AsyncMock(return_value=state)
        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph

        response = await client.get("/interviews/coach/thread-1/debrief")

        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "thread-1"
        assert data["overall_assessment"]["strengths"] == ["Clear communication"]
        assert data["overall_assessment"]["overall_score"] == 3.8
        assert len(data["session_scores"]) == 1

    async def test_returns_422_when_not_complete(self, app, client) -> None:
        mock_graph = MagicMock()
        state = MagicMock()
        state.values = {"status": "coaching"}
        mock_graph.aget_state = AsyncMock(return_value=state)
        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph

        response = await client.get("/interviews/coach/thread-1/debrief")

        assert response.status_code == 422
        assert "SESSION_NOT_COMPLETE" in response.json().get("error_code", "")

    async def test_returns_401_without_auth(self, app, client) -> None:
        app.dependency_overrides.pop(get_current_user, None)

        response = await client.get("/interviews/coach/thread-1/debrief")
        assert response.status_code == 401

    async def test_handles_plain_text_assessment(self, app, client) -> None:
        mock_graph = MagicMock()
        state = MagicMock()
        state.values = {
            "status": "complete",
            "overall_assessment": "Plain text summary",
            "session_scores": [],
            "company_name": "Acme",
            "role_title": "Dev",
            "difficulty_level": "easy",
        }
        mock_graph.aget_state = AsyncMock(return_value=state)
        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph

        response = await client.get("/interviews/coach/thread-1/debrief")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_assessment"]["summary"] == "Plain text summary"
