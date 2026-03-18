"""
Unit tests for application assembly routes.

Covers:
    POST /applications/build (202, 422, 409, validation)
    GET  /applications/build/stream?thread_id=X (SSE)
    GET  /applications/build/{thread_id}/status
    POST /applications/build/{thread_id}/save
    GET  /applications/analytics/response-rate
    GET  /applications/analytics/strategies
    GET  /applications/analytics/response-time
    POST /applications/analytics/insights
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_assembly_graph,
    get_application_repository,
    get_current_user,
    get_skills_profile_repository,
    get_success_analytics_service,
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


def _make_profile(user_id=None):
    profile = MagicMock()
    profile.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    profile.user_id = user_id or PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    profile.summary = "Senior Python developer"
    return profile


def _make_graph_mock(invoke_result=None, state_values=None, state_next=()):
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(return_value=invoke_result or {"status": "completed"})
    state = MagicMock()
    state.values = state_values or {"status": "completed"}
    state.next = state_next
    graph.aget_state = AsyncMock(return_value=state)
    return graph


def _override_assembly(app, user, graph, skills_repo=None, app_repo=None, analytics=None):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_application_assembly_graph] = lambda: graph
    if skills_repo:
        app.dependency_overrides[get_skills_profile_repository] = lambda: skills_repo
    if app_repo:
        app.dependency_overrides[get_application_repository] = lambda: app_repo
    if analytics:
        app.dependency_overrides[get_success_analytics_service] = lambda: analytics


# ---------------------------------------------------------------------------
# POST /applications/build
# ---------------------------------------------------------------------------


class TestStartAssembly:
    async def test_start_assembly_202(self, client: AsyncClient) -> None:
        """AC #1: Returns 202 with thread_id and application_id."""
        user = _make_user()
        profile = _make_profile(user.id)
        skills_repo = MagicMock()
        skills_repo.get_by_user = AsyncMock(return_value=profile)
        graph = _make_graph_mock()
        app_repo = MagicMock()
        app_repo.find_in_progress_assembly = AsyncMock(return_value=None)
        created_app = MagicMock()
        created_app.id = PydanticObjectId("cccccccccccccccccccccccc")
        app_repo.create = AsyncMock(return_value=created_app)
        _override_assembly(client.app, user, graph, skills_repo=skills_repo, app_repo=app_repo)

        response = await client.post(
            "/applications/build",
            json={"jd_text": "Senior Python developer needed"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "thread_id" in data
        assert "application_id" in data

    async def test_start_assembly_no_skills_profile_422(self, client: AsyncClient) -> None:
        """AC #4: Returns 422 PROFILE_NOT_BUILT if no SkillsProfile."""
        user = _make_user()
        skills_repo = MagicMock()
        skills_repo.get_by_user = AsyncMock(return_value=None)
        graph = _make_graph_mock()
        app_repo = MagicMock()
        _override_assembly(client.app, user, graph, skills_repo=skills_repo, app_repo=app_repo)

        response = await client.post(
            "/applications/build",
            json={"jd_text": "Some JD"},
        )

        assert response.status_code == 422
        assert response.json()["error_code"] == "PROFILE_NOT_BUILT"

    async def test_start_assembly_duplicate_409(self, client: AsyncClient) -> None:
        """AC #5: Returns 409 GENERATION_ALREADY_IN_PROGRESS if duplicate."""
        user = _make_user()
        profile = _make_profile(user.id)
        skills_repo = MagicMock()
        skills_repo.get_by_user = AsyncMock(return_value=profile)
        graph = _make_graph_mock()
        existing_app = MagicMock()
        existing_app.thread_id = "existing-thread"
        app_repo = MagicMock()
        app_repo.find_in_progress_assembly = AsyncMock(return_value=existing_app)
        _override_assembly(client.app, user, graph, skills_repo=skills_repo, app_repo=app_repo)

        response = await client.post(
            "/applications/build",
            json={"jd_text": "Python dev"},
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "GENERATION_ALREADY_IN_PROGRESS"

    async def test_start_assembly_no_input_422(self, client: AsyncClient) -> None:
        """Validation: Returns 422 when neither job_url nor jd_text provided."""
        user = _make_user()
        graph = _make_graph_mock()
        _override_assembly(client.app, user, graph)

        response = await client.post(
            "/applications/build",
            json={},
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /applications/build/stream
# ---------------------------------------------------------------------------


class TestStreamAssembly:
    async def test_stream_returns_sse_completed(self, client: AsyncClient) -> None:
        """SSE stream for completed graph returns completed event."""
        user = _make_user()
        graph = _make_graph_mock(
            state_values={"status": "completed"},
            state_next=(),
        )
        _override_assembly(client.app, user, graph)

        response = await client.get("/applications/build/stream?thread_id=test-thread")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "completed" in response.text

    async def test_stream_returns_awaiting_review(self, client: AsyncClient) -> None:
        """SSE stream at human_review returns awaiting_review with package."""
        user = _make_user()
        graph = _make_graph_mock(
            state_values={
                "tailored_resume": "Resume",
                "cover_letter": "CL",
                "micro_pitch": "Pitch",
                "fit_analysis": "Fit",
                "application_strategy": "Strategy",
            },
            state_next=("human_review",),
        )
        _override_assembly(client.app, user, graph)

        response = await client.get("/applications/build/stream?thread_id=test-thread")

        assert response.status_code == 200
        body = response.text
        assert "awaiting_review" in body
        assert "cover_letter" in body

    async def test_stream_not_found(self, client: AsyncClient) -> None:
        """Stream with unknown thread_id returns 404."""
        user = _make_user()
        graph = _make_graph_mock(state_values={})
        state = MagicMock()
        state.values = {}
        graph.aget_state = AsyncMock(return_value=state)
        _override_assembly(client.app, user, graph)

        response = await client.get("/applications/build/stream?thread_id=nonexistent")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /applications/build/{thread_id}/status
# ---------------------------------------------------------------------------


class TestGetAssemblyStatus:
    async def test_get_status(self, client: AsyncClient) -> None:
        user = _make_user()
        graph = _make_graph_mock(state_values={
            "status": "completed",
            "decoded_jd": "parsed",
            "fit_analysis": "85%",
            "application_strategy": "{}",
            "tailored_resume": "resume",
            "cover_letter": "letter",
        })
        _override_assembly(client.app, user, graph)

        response = await client.get("/applications/build/test-thread/status")

        assert response.status_code == 200
        assert response.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# POST /applications/build/{thread_id}/save
# ---------------------------------------------------------------------------


class TestSaveAssembly:
    async def test_save_application(self, client: AsyncClient) -> None:
        user = _make_user()
        graph = _make_graph_mock(state_values={
            "job_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
            "application_strategy": "keyword focused",
        })
        app_repo = MagicMock()
        created_app = MagicMock()
        created_app.id = PydanticObjectId("cccccccccccccccccccccccc")
        app_repo.create = AsyncMock(return_value=created_app)
        _override_assembly(client.app, user, graph, app_repo=app_repo)

        response = await client.post(
            "/applications/build/test-thread/save",
            json={"submission_method": "linkedin"},
        )

        assert response.status_code == 201
        assert "application_id" in response.json()


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------


class TestAnalyticsResponseRate:
    async def test_response_rate(self, client: AsyncClient) -> None:
        user = _make_user()
        analytics = MagicMock()
        analytics.get_response_rate = AsyncMock(
            return_value={"total": 10, "response_rate": 0.3, "by_method": {}}
        )
        graph = _make_graph_mock()
        _override_assembly(client.app, user, graph, analytics=analytics)

        response = await client.get("/applications/analytics/response-rate")

        assert response.status_code == 200
        assert response.json()["total"] == 10
        assert response.json()["response_rate"] == 0.3


class TestAnalyticsStrategies:
    async def test_strategies(self, client: AsyncClient) -> None:
        user = _make_user()
        analytics = MagicMock()
        analytics.get_best_performing_strategies = AsyncMock(
            return_value={"strategies": [{"strategy": "referral", "total": 5, "rate": 0.8}]}
        )
        graph = _make_graph_mock()
        _override_assembly(client.app, user, graph, analytics=analytics)

        response = await client.get("/applications/analytics/strategies")

        assert response.status_code == 200
        assert len(response.json()["strategies"]) == 1


class TestAnalyticsResponseTime:
    async def test_response_time(self, client: AsyncClient) -> None:
        user = _make_user()
        analytics = MagicMock()
        analytics.get_avg_response_time = AsyncMock(
            return_value={"avg_days": 5.0, "sample_size": 3}
        )
        graph = _make_graph_mock()
        _override_assembly(client.app, user, graph, analytics=analytics)

        response = await client.get("/applications/analytics/response-time")

        assert response.status_code == 200
        assert response.json()["avg_days"] == 5.0


class TestAnalyticsInsights:
    async def test_insights(self, client: AsyncClient) -> None:
        user = _make_user()
        analytics = MagicMock()
        analytics.get_response_rate = AsyncMock(
            return_value={"total": 10, "response_rate": 0.3, "by_method": {}}
        )
        analytics.get_best_performing_strategies = AsyncMock(
            return_value={"strategies": []}
        )
        analytics.get_avg_response_time = AsyncMock(
            return_value={"avg_days": 5.0, "sample_size": 3}
        )
        graph = _make_graph_mock()
        _override_assembly(client.app, user, graph, analytics=analytics)

        # Mock the SuccessPatternAgent call
        from unittest.mock import patch as mock_patch

        mock_agent_instance = AsyncMock()
        mock_agent_instance.return_value = {"success_insights": "Use referrals more"}
        with mock_patch(
            "src.api.routes.application_assembly.SuccessPatternAgent",
            return_value=mock_agent_instance,
        ):
            response = await client.post("/applications/analytics/insights")

        assert response.status_code == 200
        assert "success_insights" in response.json()


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


class TestAuthRequired:
    async def test_assembly_endpoints_require_auth(self, client: AsyncClient) -> None:
        # Clear any overrides to test default auth behavior
        client.app.dependency_overrides.clear()

        endpoints = [
            ("POST", "/applications/build"),
            ("GET", "/applications/build/stream?thread_id=test"),
            ("GET", "/applications/build/test/status"),
            ("POST", "/applications/build/test/save"),
            ("GET", "/applications/analytics/response-rate"),
            ("GET", "/applications/analytics/strategies"),
            ("GET", "/applications/analytics/response-time"),
            ("POST", "/applications/analytics/insights"),
        ]

        for method, url in endpoints:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json={})
            assert response.status_code in (401, 403), f"{method} {url} returned {response.status_code}"
