"""
Unit tests for interview coach routes.

Covers:
    POST /interviews/coach/start
    POST /interviews/coach/{thread_id}/answer
    GET  /interviews/coach/{thread_id}/status
    GET  /interviews/coach/history
    GET  /interviews/coach/history/{session_id}
    GET  /interviews/coach/trends
    POST /interviews/coach/{thread_id}/save
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_interview_coach_graph,
    get_interview_performance_repository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_graph_mock(invoke_result=None, state_values=None):
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(return_value=invoke_result or {"status": "started"})
    state = MagicMock()
    state.values = state_values or {
        "status": "coaching",
        "current_question_index": 0,
        "difficulty_level": "medium",
        "session_scores": [],
        "company_name": "Acme",
        "role_title": "SWE",
        "overall_assessment": "",
    }
    graph.aget_state = AsyncMock(return_value=state)
    return graph


def _make_session(session_id="s1", overall_score=3.5, company="Acme", role="SWE"):
    session = MagicMock()
    session.session_id = session_id
    session.company_name = company
    session.role_title = role
    session.overall_score = overall_score
    session.created_at = None
    session.strengths = ["communication"]
    session.improvement_areas = ["confidence"]
    session.question_scores = []
    session.difficulty_level = "medium"
    session.session_summary = "Good session"
    session.model_dump.return_value = {
        "session_id": session_id,
        "company_name": company,
        "role_title": role,
        "overall_score": overall_score,
    }
    return session


def _override(app, user, graph=None, repo=None):
    app.dependency_overrides[get_current_user] = lambda: user
    if graph:
        app.dependency_overrides[get_interview_coach_graph] = lambda: graph
    if repo:
        app.dependency_overrides[get_interview_performance_repository] = lambda: repo


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------


class TestStartSession:
    async def test_start_session(self, client: AsyncClient) -> None:
        user = _make_user()
        graph = _make_graph_mock()
        perf_repo = MagicMock()
        perf_repo.count_active_sessions = AsyncMock(return_value=0)
        _override(client.app, user, graph=graph, repo=perf_repo)

        response = await client.post(
            "/interviews/coach/start",
            json={
                "company_name": "Acme Corp",
                "role_title": "Senior SWE",
                "jd_text": "Python developer needed",
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "thread_id" in data
        assert "session_id" in data
        assert data["status"] == "started"


class TestAnswerQuestion:
    async def test_answer_question(self, client: AsyncClient) -> None:
        user = _make_user()
        graph = _make_graph_mock(invoke_result={
            "evaluation": '{"score_relevance": 4}',
            "current_question": "Tell me about yourself",
            "overall_assessment": "",
            "status": "evaluating",
        })
        _override(client.app, user, graph=graph)

        response = await client.post(
            "/interviews/coach/test-thread/answer",
            json={"answer": "I am a senior Python developer."},
        )

        assert response.status_code == 200
        assert "evaluation" in response.json()
        assert response.json()["status"] == "evaluating"


class TestGetSessionStatus:
    async def test_get_status(self, client: AsyncClient) -> None:
        user = _make_user()
        graph = _make_graph_mock()
        _override(client.app, user, graph=graph)

        response = await client.get("/interviews/coach/test-thread/status")

        assert response.status_code == 200
        assert response.json()["status"] == "coaching"
        assert response.json()["difficulty_level"] == "medium"


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------


class TestGetHistory:
    async def test_get_history(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[
            _make_session("s1", 3.5, "Acme", "SWE"),
            _make_session("s2", 4.0, "BigCo", "Lead"),
        ])
        repo.count_user_sessions = AsyncMock(return_value=2)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["sessions"][0]["session_id"] == "s1"
        assert data["total"] == 2

    async def test_get_history_empty(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[])
        repo.count_user_sessions = AsyncMock(return_value=0)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history")

        assert response.status_code == 200
        assert response.json()["sessions"] == []


class TestGetSessionDetail:
    async def test_get_session_detail(self, client: AsyncClient) -> None:
        user = _make_user()
        session = _make_session("s1")
        repo = MagicMock()
        repo.get_by_session = AsyncMock(return_value=session)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history/s1")

        assert response.status_code == 200

    async def test_session_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_by_session = AsyncMock(return_value=None)
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/history/nonexistent")

        assert response.status_code == 404


class TestGetTrends:
    async def test_get_trends(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[_make_session(), _make_session("s2")])
        repo.get_user_trends = AsyncMock(return_value={
            "categories": {"behavioral": {"average_score": 3.5, "data_points": 2, "trend": []}},
            "overall_trend": [
                {"session_id": "s1", "overall_score": 3.0, "created_at": None},
                {"session_id": "s2", "overall_score": 4.0, "created_at": None},
            ],
        })
        repo.get_improvement_velocity = AsyncMock(return_value={
            "velocity": {"behavioral": {"early_avg": 3.0, "late_avg": 4.0, "delta": 1.0, "improving": True}},
            "has_enough_data": True,
        })
        repo.get_weak_areas = AsyncMock(return_value=[])
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/trends")

        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 2
        assert len(data["avg_score_trend"]) == 2

    async def test_trends_empty(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_user_sessions = AsyncMock(return_value=[])
        repo.get_user_trends = AsyncMock(return_value={"categories": {}, "overall_trend": []})
        repo.get_improvement_velocity = AsyncMock(return_value={"velocity": {}, "has_enough_data": False})
        repo.get_weak_areas = AsyncMock(return_value=[])
        _override(client.app, user, repo=repo)

        response = await client.get("/interviews/coach/trends")

        assert response.status_code == 200
        assert response.json()["total_sessions"] == 0


class TestSaveSession:
    async def test_save_session(self, client: AsyncClient) -> None:
        user = _make_user()
        graph = _make_graph_mock(state_values={
            "company_name": "Acme",
            "role_title": "SWE",
            "difficulty_level": "medium",
            "session_scores": [
                {"question_text": "Q1", "score_relevance": 4, "score_structure": 3,
                 "score_specificity": 4, "score_confidence": 3},
            ],
            "overall_assessment": "Good session",
        })
        repo = MagicMock()
        created = MagicMock()
        created.overall_score = 3.5
        repo.create = AsyncMock(return_value=created)
        _override(client.app, user, graph=graph, repo=repo)

        response = await client.post("/interviews/coach/test-thread/save")

        assert response.status_code == 201
        assert "session_id" in response.json()
        repo.create.assert_called_once()


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


class TestAuthRequired:
    async def test_coach_endpoints_require_auth(self, client: AsyncClient) -> None:
        client.app.dependency_overrides.clear()

        endpoints = [
            ("POST", "/interviews/coach/start"),
            ("POST", "/interviews/coach/test/answer"),
            ("GET", "/interviews/coach/test/status"),
            ("GET", "/interviews/coach/history"),
            ("GET", "/interviews/coach/history/s1"),
            ("GET", "/interviews/coach/trends"),
            ("POST", "/interviews/coach/test/save"),
        ]

        for method, url in endpoints:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json={})
            assert response.status_code in (401, 403), f"{method} {url} returned {response.status_code}"
