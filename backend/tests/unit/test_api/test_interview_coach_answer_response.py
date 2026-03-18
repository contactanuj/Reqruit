"""
Tests for enhanced answer endpoint response with structured scores (Story 9.2).
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


class TestAnswerResponse:
    async def test_returns_structured_scores(self, app, client) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "evaluation": json.dumps({
                "score_relevance": 4,
                "score_structure": 3,
                "score_specificity": 5,
                "score_confidence": 4,
                "feedback": "Good STAR usage",
                "improvement_suggestion": "Quantify results more",
            }),
            "current_question": "Next question",
            "difficulty_level": "medium",
            "predicted_questions": json.dumps([{"question_text": "Q"}] * 10),
            "current_question_index": 3,
            "star_stories": "Story: Led migration...",
            "overall_assessment": "",
            "status": "evaluating",
        })
        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph

        response = await client.post(
            "/interviews/coach/test-thread/answer",
            json={"answer": "In my previous role, I led a team..."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scores"]["relevance"] == 4
        assert data["scores"]["specificity"] == 5
        assert data["feedback"] == "Good STAR usage"
        assert data["improvement_suggestion"] == "Quantify results more"

    async def test_returns_questions_remaining(self, app, client) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "evaluation": "{}",
            "current_question": "Q",
            "difficulty_level": "medium",
            "predicted_questions": json.dumps([{"question_text": "Q"}] * 10),
            "current_question_index": 3,
            "star_stories": "",
            "overall_assessment": "",
            "status": "evaluating",
        })
        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph

        response = await client.post(
            "/interviews/coach/test-thread/answer",
            json={"answer": "Answer"},
        )
        data = response.json()
        assert data["questions_remaining"] == 6  # 10 - 3 - 1

    async def test_returns_star_stories_and_difficulty(self, app, client) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "evaluation": "{}",
            "current_question": "Q",
            "difficulty_level": "hard",
            "predicted_questions": "[]",
            "current_question_index": 0,
            "star_stories": "Story: Led a cross-functional team...",
            "overall_assessment": "",
            "status": "evaluating",
        })
        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph

        response = await client.post(
            "/interviews/coach/test-thread/answer",
            json={"answer": "Answer"},
        )
        data = response.json()
        assert data["difficulty_level"] == "hard"
        assert "Led a cross-functional team" in data["star_stories"]

    async def test_handles_non_json_evaluation(self, app, client) -> None:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "evaluation": "Non-JSON feedback text",
            "current_question": "Q",
            "difficulty_level": "medium",
            "predicted_questions": "[]",
            "current_question_index": 0,
            "star_stories": "",
            "overall_assessment": "",
            "status": "evaluating",
        })
        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph

        response = await client.post(
            "/interviews/coach/test-thread/answer",
            json={"answer": "Answer"},
        )
        data = response.json()
        assert data["scores"] == {}
        assert data["evaluation"] == "Non-JSON feedback text"

    async def test_returns_401_without_auth(self, app, client) -> None:
        app.dependency_overrides.pop(get_current_user, None)

        response = await client.post(
            "/interviews/coach/test-thread/answer",
            json={"answer": "Answer"},
        )
        assert response.status_code == 401


class TestSessionStatus:
    async def test_returns_full_state_for_reconnect(self, app, client) -> None:
        mock_graph = MagicMock()
        state = MagicMock()
        state.values = {
            "status": "coaching",
            "current_question_index": 2,
            "difficulty_level": "hard",
            "session_scores": [
                {"score_relevance": 4, "score_structure": 3},
            ],
        }
        mock_graph.aget_state = AsyncMock(return_value=state)
        app.dependency_overrides[get_interview_coach_graph] = lambda: mock_graph

        response = await client.get("/interviews/coach/test-thread/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "coaching"
        assert data["current_question_index"] == 2
        assert data["difficulty_level"] == "hard"
        assert len(data["session_scores"]) == 1
