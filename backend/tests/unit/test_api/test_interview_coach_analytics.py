"""
Tests for enhanced trends and history endpoints (Story 9.4).
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_interview_performance_repository,
)


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_session(session_id="s1", overall_score=3.5, company="Acme", role="SWE", q_count=2):
    session = MagicMock()
    session.session_id = session_id
    session.company_name = company
    session.role_title = role
    session.overall_score = overall_score
    session.created_at = None
    session.question_scores = [MagicMock() for _ in range(q_count)]
    return session


def _override(app, user, repo=None):
    app.dependency_overrides[get_current_user] = lambda: user
    if repo:
        app.dependency_overrides[get_interview_performance_repository] = lambda: repo


# ---------------------------------------------------------------------------
# Trends endpoint
# ---------------------------------------------------------------------------


class TestTrendsEndpoint:
    async def test_returns_category_trends(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[_make_session(), _make_session("s2")])
        repo.get_user_trends = AsyncMock(return_value={
            "categories": {
                "behavioral": {"average_score": 4.0, "data_points": 3, "trend": []},
                "technical": {"average_score": 2.5, "data_points": 3, "trend": []},
            },
            "overall_trend": [
                {"session_id": "s1", "overall_score": 3.0, "created_at": None},
                {"session_id": "s2", "overall_score": 3.5, "created_at": None},
            ],
        })
        repo.get_improvement_velocity = AsyncMock(return_value={
            "velocity": {
                "behavioral": {"early_avg": 3.5, "late_avg": 4.5, "delta": 1.0, "improving": True},
            },
            "has_enough_data": True,
        })
        repo.get_weak_areas = AsyncMock(return_value=[
            {"category": "technical", "weak_session_count": 3, "average_score": 2.5, "examples": []},
        ])
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/trends")

        assert response.status_code == 200
        data = response.json()
        assert "category_trends" in data
        assert "behavioral" in data["category_trends"]
        assert "improvement_velocity" in data
        assert "recurring_weaknesses" in data
        assert len(data["recurring_weaknesses"]) == 1
        assert data["total_sessions"] == 2

    async def test_empty_when_no_sessions(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[])
        repo.get_user_trends = AsyncMock(return_value={"categories": {}, "overall_trend": []})
        repo.get_improvement_velocity = AsyncMock(return_value={"velocity": {}, "has_enough_data": False})
        repo.get_weak_areas = AsyncMock(return_value=[])
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/trends")

        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0
        assert data["category_trends"] == {}
        assert data["improvement_velocity"] == {}
        assert data["recurring_weaknesses"] == []

    async def test_includes_avg_score_trend(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[_make_session("s1"), _make_session("s2"), _make_session("s3")])
        repo.get_user_trends = AsyncMock(return_value={
            "categories": {},
            "overall_trend": [
                {"session_id": "s1", "overall_score": 2.0, "created_at": None},
                {"session_id": "s2", "overall_score": 4.0, "created_at": None},
                {"session_id": "s3", "overall_score": 3.5, "created_at": None},
            ],
        })
        repo.get_improvement_velocity = AsyncMock(return_value={"velocity": {}, "has_enough_data": True})
        repo.get_weak_areas = AsyncMock(return_value=[])
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/trends")
        data = response.json()
        assert len(data["avg_score_trend"]) == 3
        assert data["avg_score_trend"][0]["session_id"] == "s1"


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------


class TestHistoryEndpoint:
    async def test_returns_paginated_sessions(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[
            _make_session("s1", 3.5),
            _make_session("s2", 4.0),
        ])
        repo.count_user_sessions = AsyncMock(return_value=5)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history?skip=0&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["total"] == 5
        assert data["skip"] == 0
        assert data["limit"] == 2

    async def test_includes_question_count(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[
            _make_session("s1", 3.5, q_count=3),
            _make_session("s2", 4.0, q_count=5),
        ])
        repo.count_user_sessions = AsyncMock(return_value=2)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history")

        data = response.json()
        assert data["sessions"][0]["question_count"] == 3
        assert data["sessions"][1]["question_count"] == 5

    async def test_pagination_skip_limit(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[_make_session("s3")])
        repo.count_user_sessions = AsyncMock(return_value=3)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history?skip=2&limit=1")

        data = response.json()
        assert data["skip"] == 2
        assert data["limit"] == 1
        # Verify repo was called with skip/limit
        repo.get_user_sessions.assert_called_once()
        call_kwargs = repo.get_user_sessions.call_args
        assert call_kwargs[1]["skip"] == 2 or call_kwargs[0][1] == 2 if len(call_kwargs[0]) > 1 else call_kwargs[1].get("skip") == 2

    async def test_empty_history(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[])
        repo.count_user_sessions = AsyncMock(return_value=0)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    async def test_default_pagination(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[])
        repo.count_user_sessions = AsyncMock(return_value=0)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history")

        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 20
