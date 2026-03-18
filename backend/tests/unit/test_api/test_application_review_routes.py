"""
Unit tests for application review, edit, get, delete routes (Story 7.4).

Covers:
    POST   /applications/build/review (approve, revise, reject, validation)
    PATCH  /applications/{id} (content edit)
    GET    /applications/{id} (full package)
    DELETE /applications/{id} (cleanup)
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_assembly_graph,
    get_application_repository,
    get_current_user,
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


def _make_app_mock(thread_id="t-1"):
    app = MagicMock()
    app.id = PydanticObjectId("cccccccccccccccccccccccc")
    app.user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    app.thread_id = thread_id
    return app


def _override(client_app, user, graph=None, app_repo=None):
    client_app.dependency_overrides[get_current_user] = lambda: user
    if graph:
        client_app.dependency_overrides[get_application_assembly_graph] = lambda: graph
    if app_repo:
        client_app.dependency_overrides[get_application_repository] = lambda: app_repo


# ---------------------------------------------------------------------------
# POST /applications/build/review
# ---------------------------------------------------------------------------


class TestReviewAssembly:
    async def test_approve_200(self, client: AsyncClient) -> None:
        """AC #2: approve returns 200 with status approved."""
        user = _make_user()
        graph = AsyncMock()
        state = MagicMock()
        state.values = {"status": "awaiting_review", "application_id": "cccccccccccccccccccccccc"}
        state.next = ("human_review",)
        graph.aget_state = AsyncMock(return_value=state)
        graph.ainvoke = AsyncMock(return_value={"status": "approved"})

        app_repo = MagicMock()
        app_repo.find_one = AsyncMock(return_value=_make_app_mock())
        app_repo.get_by_user_and_id = AsyncMock(return_value=_make_app_mock())
        app_repo.update = AsyncMock()
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.post(
            "/applications/build/review",
            json={"thread_id": "t-1", "action": "approve"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    async def test_revise_200(self, client: AsyncClient) -> None:
        """AC #4: revise returns 200 with revision_requested."""
        user = _make_user()
        graph = AsyncMock()
        state = MagicMock()
        state.values = {"status": "awaiting_review", "application_id": "cccccccccccccccccccccccc"}
        state.next = ("human_review",)
        graph.aget_state = AsyncMock(return_value=state)
        graph.ainvoke = AsyncMock(return_value={"status": "revision_requested"})

        app_repo = MagicMock()
        app_repo.find_one = AsyncMock(return_value=_make_app_mock())
        app_repo.get_by_user_and_id = AsyncMock(return_value=None)
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.post(
            "/applications/build/review",
            json={"thread_id": "t-1", "action": "revise", "feedback": "More Python detail"},
        )
        assert resp.status_code == 200

    async def test_reject_200(self, client: AsyncClient) -> None:
        """AC #5: reject returns 200 with status rejected."""
        user = _make_user()
        graph = AsyncMock()
        state = MagicMock()
        state.values = {"status": "awaiting_review", "application_id": "cccccccccccccccccccccccc"}
        state.next = ("human_review",)
        graph.aget_state = AsyncMock(return_value=state)
        graph.ainvoke = AsyncMock(return_value={"status": "rejected"})

        app_repo = MagicMock()
        app_repo.find_one = AsyncMock(return_value=_make_app_mock())
        app_repo.get_by_user_and_id = AsyncMock(return_value=_make_app_mock())
        app_repo.update = AsyncMock()
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.post(
            "/applications/build/review",
            json={"thread_id": "t-1", "action": "reject"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    async def test_thread_not_found_422(self, client: AsyncClient) -> None:
        """AC #7: Non-existent thread returns 422 THREAD_NOT_FOUND."""
        user = _make_user()
        graph = AsyncMock()
        state = MagicMock()
        state.values = {}
        graph.aget_state = AsyncMock(return_value=state)
        app_repo = MagicMock()
        app_repo.find_one = AsyncMock(return_value=_make_app_mock())
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.post(
            "/applications/build/review",
            json={"thread_id": "nonexistent", "action": "approve"},
        )
        assert resp.status_code == 422

    async def test_thread_expired_422(self, client: AsyncClient) -> None:
        """Graph already completed returns 422 THREAD_EXPIRED."""
        user = _make_user()
        graph = AsyncMock()
        state = MagicMock()
        state.values = {"status": "completed"}
        state.next = ()
        graph.aget_state = AsyncMock(return_value=state)
        app_repo = MagicMock()
        app_repo.find_one = AsyncMock(return_value=_make_app_mock())
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.post(
            "/applications/build/review",
            json={"thread_id": "t-1", "action": "approve"},
        )
        assert resp.status_code == 422

    async def test_thread_not_ready_422(self, client: AsyncClient) -> None:
        """Graph not at human_review returns 422 THREAD_NOT_READY."""
        user = _make_user()
        graph = AsyncMock()
        state = MagicMock()
        state.values = {"status": "scoring"}
        state.next = ("score_fit",)
        graph.aget_state = AsyncMock(return_value=state)
        app_repo = MagicMock()
        app_repo.find_one = AsyncMock(return_value=_make_app_mock())
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.post(
            "/applications/build/review",
            json={"thread_id": "t-1", "action": "approve"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /applications/{id}
# ---------------------------------------------------------------------------


class TestEditApplication:
    async def test_patch_updates_checkpoint(self, client: AsyncClient) -> None:
        """AC #3: PATCH updates checkpoint state."""
        user = _make_user()
        graph = AsyncMock()
        state = MagicMock()
        state.next = ("human_review",)
        graph.aget_state = AsyncMock(return_value=state)
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=_make_app_mock())
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.patch(
            "/applications/cccccccccccccccccccccccc",
            json={"cover_letter": "Updated CL content"},
        )
        assert resp.status_code == 200
        assert "cover_letter" in resp.json()["updated_fields"]
        graph.aupdate_state.assert_called_once()

    async def test_patch_not_found_404(self, client: AsyncClient) -> None:
        """PATCH on non-existent application returns 404."""
        user = _make_user()
        graph = AsyncMock()
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=None)
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.patch(
            "/applications/cccccccccccccccccccccccc",
            json={"cover_letter": "Updated"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /applications/{id}
# ---------------------------------------------------------------------------


class TestGetApplication:
    async def test_get_returns_full_package(self, client: AsyncClient) -> None:
        """AC #8: GET returns full application package."""
        user = _make_user()
        graph = AsyncMock()
        state = MagicMock()
        state.values = {
            "tailored_resume": "R",
            "cover_letter": "CL",
            "micro_pitch": "P",
            "fit_analysis": "F",
            "application_strategy": "S",
            "decoded_jd": "DJ",
            "status": "approved",
        }
        graph.aget_state = AsyncMock(return_value=state)
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=_make_app_mock())
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.get("/applications/cccccccccccccccccccccccc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tailored_resume"] == "R"
        assert data["cover_letter"] == "CL"
        assert data["micro_pitch"] == "P"
        assert data["fit_analysis"] == "F"
        assert data["application_strategy"] == "S"

    async def test_get_not_found_404(self, client: AsyncClient) -> None:
        """GET on non-existent application returns 404."""
        user = _make_user()
        graph = AsyncMock()
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=None)
        _override(client.app, user, graph=graph, app_repo=app_repo)

        resp = await client.get("/applications/cccccccccccccccccccccccc")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /applications/{id}
# ---------------------------------------------------------------------------


class TestDeleteApplication:
    async def test_delete_204(self, client: AsyncClient) -> None:
        """AC #9: DELETE returns 204."""
        user = _make_user()
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=_make_app_mock())
        app_repo.delete = AsyncMock(return_value=True)
        _override(client.app, user, app_repo=app_repo)

        resp = await client.delete("/applications/cccccccccccccccccccccccc")
        assert resp.status_code == 204

    async def test_delete_not_found_404(self, client: AsyncClient) -> None:
        """DELETE on non-existent application returns 404."""
        user = _make_user()
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=None)
        _override(client.app, user, app_repo=app_repo)

        resp = await client.delete("/applications/cccccccccccccccccccccccc")
        assert resp.status_code == 404
