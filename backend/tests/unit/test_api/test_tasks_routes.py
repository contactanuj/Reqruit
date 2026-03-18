"""Tests for background task API routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_task_service
from src.db.documents.task_record import TaskPriority, TaskStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
OTHER_USER_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
NOW = datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)


def _make_user(user_id=USER_ID):
    user = MagicMock()
    user.id = user_id
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_record(
    task_id="task-abc-123",
    status=TaskStatus.QUEUED,
    task_type="tailor_resume",
    priority=TaskPriority.BATCH,
    result_payload=None,
    error_message=None,
    llm_tokens_used=None,
    llm_cost_usd=None,
):
    record = MagicMock()
    record.task_id = task_id
    record.status = status
    record.task_type = task_type
    record.priority = priority
    record.submitted_at = NOW
    record.started_at = None
    record.completed_at = None
    record.result_payload = result_payload
    record.error_message = error_message
    record.llm_tokens_used = llm_tokens_used
    record.llm_cost_usd = llm_cost_usd
    return record


def _override(app, user=None, task_service=None):
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    if task_service is not None:
        app.dependency_overrides[get_task_service] = lambda: task_service


# ---------------------------------------------------------------------------
# POST /tasks/submit
# ---------------------------------------------------------------------------


class TestSubmitEndpoint:
    async def test_returns_200_with_task_id(self, client: AsyncClient):
        """POST /tasks/submit returns task_id and status=queued."""
        user = _make_user()
        svc = AsyncMock()
        record = _make_record()
        svc.submit_task.return_value = record

        _override(client.app, user=user, task_service=svc)

        resp = await client.post(
            "/tasks/submit",
            json={"task_type": "tailor_resume", "payload": {"key": "val"}},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc-123"
        assert data["status"] == "queued"

    async def test_returns_401_without_auth(self, client: AsyncClient):
        """POST /tasks/submit returns 401 without auth token."""
        resp = await client.post(
            "/tasks/submit",
            json={"task_type": "test", "payload": {}},
        )

        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/status
# ---------------------------------------------------------------------------


class TestStatusEndpoint:
    async def test_returns_200_with_status(self, client: AsyncClient):
        """GET /tasks/{task_id}/status returns task status fields."""
        user = _make_user()
        svc = AsyncMock()
        svc.get_task_status.return_value = _make_record()

        _override(client.app, user=user, task_service=svc)

        resp = await client.get("/tasks/task-abc-123/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc-123"
        assert data["status"] == "queued"
        assert data["task_type"] == "tailor_resume"
        assert data["priority"] == "batch"

    async def test_returns_404_for_nonexistent(self, client: AsyncClient):
        """GET /tasks/{task_id}/status returns 404 with error code 4240."""
        user = _make_user()
        svc = AsyncMock()
        svc.get_task_status.return_value = None

        _override(client.app, user=user, task_service=svc)

        resp = await client.get("/tasks/no-such-task/status")

        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["code"] == 4240

    async def test_returns_404_for_other_users_task(self, client: AsyncClient):
        """GET /tasks/{task_id}/status returns 404 for another user's task."""
        user = _make_user()
        svc = AsyncMock()
        svc.get_task_status.return_value = None  # Service returns None for isolation

        _override(client.app, user=user, task_service=svc)

        resp = await client.get("/tasks/other-user-task/status")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/result
# ---------------------------------------------------------------------------


class TestResultEndpoint:
    async def test_returns_200_with_result(self, client: AsyncClient):
        """GET /tasks/{task_id}/result returns result_payload for completed task."""
        user = _make_user()
        svc = AsyncMock()
        record = _make_record(
            status=TaskStatus.COMPLETED,
            result_payload={"output": "success"},
            llm_tokens_used=100,
            llm_cost_usd=0.05,
        )
        record.completed_at = NOW
        svc.get_task_result.return_value = record

        _override(client.app, user=user, task_service=svc)

        resp = await client.get("/tasks/task-abc-123/result")

        assert resp.status_code == 200
        data = resp.json()
        assert data["result_payload"] == {"output": "success"}
        assert data["llm_tokens_used"] == 100
        assert data["llm_cost_usd"] == 0.05

    async def test_returns_200_with_null_result_for_pending(self, client: AsyncClient):
        """GET /tasks/{task_id}/result returns null result for non-completed task."""
        user = _make_user()
        svc = AsyncMock()
        record = _make_record(status=TaskStatus.PROCESSING)
        svc.get_task_result.return_value = record

        _override(client.app, user=user, task_service=svc)

        resp = await client.get("/tasks/task-abc-123/result")

        assert resp.status_code == 200
        data = resp.json()
        assert data["result_payload"] is None

    async def test_returns_404_for_other_users_task(self, client: AsyncClient):
        """GET /tasks/{task_id}/result returns 404 for another user's task."""
        user = _make_user()
        svc = AsyncMock()
        svc.get_task_result.return_value = None

        _override(client.app, user=user, task_service=svc)

        resp = await client.get("/tasks/other-user-task/result")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /tasks/
# ---------------------------------------------------------------------------


class TestListEndpoint:
    async def test_returns_paginated_list(self, client: AsyncClient):
        """GET /tasks/ returns paginated list of user's tasks."""
        user = _make_user()
        svc = AsyncMock()
        svc.list_user_tasks.return_value = [
            _make_record(task_id="t-1"),
            _make_record(task_id="t-2"),
        ]

        _override(client.app, user=user, task_service=svc)

        resp = await client.get("/tasks/")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) == 2
        assert data["total"] == 2

    async def test_filters_by_status(self, client: AsyncClient):
        """GET /tasks/?status=completed filters by status query param."""
        user = _make_user()
        svc = AsyncMock()
        svc.list_user_tasks.return_value = []

        _override(client.app, user=user, task_service=svc)

        resp = await client.get("/tasks/?status=completed")

        assert resp.status_code == 200
        svc.list_user_tasks.assert_called_once()
        call_kwargs = svc.list_user_tasks.call_args[1]
        assert call_kwargs["status"] == TaskStatus.COMPLETED

    async def test_submit_no_blocking(self, client: AsyncClient):
        """POST /tasks/submit only calls repo.create + celery.send_task (no blocking)."""
        user = _make_user()
        svc = AsyncMock()
        record = _make_record()
        svc.submit_task.return_value = record

        _override(client.app, user=user, task_service=svc)

        resp = await client.post(
            "/tasks/submit",
            json={"task_type": "test", "payload": {}},
        )

        assert resp.status_code == 200
        svc.submit_task.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}
# ---------------------------------------------------------------------------


class TestCancelEndpoint:
    async def test_returns_200_for_queued_task(self, client: AsyncClient):
        """DELETE /tasks/{task_id} returns 200 with cancellation response."""
        user = _make_user()
        svc = AsyncMock()
        svc.cancel_task.return_value = {
            "task_id": "task-abc-123",
            "status": "cancelled",
            "message": "Task cancelled successfully",
        }

        _override(client.app, user=user, task_service=svc)

        resp = await client.delete("/tasks/task-abc-123")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["message"] == "Task cancelled successfully"

    async def test_returns_200_for_processing_task(self, client: AsyncClient):
        """DELETE /tasks/{task_id} returns 200 with best-effort message."""
        user = _make_user()
        svc = AsyncMock()
        svc.cancel_task.return_value = {
            "task_id": "task-abc-123",
            "status": "processing",
            "message": "Cancellation requested; task is already processing and may complete before cancellation takes effect",
        }

        _override(client.app, user=user, task_service=svc)

        resp = await client.delete("/tasks/task-abc-123")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processing"
        assert "already processing" in data["message"]

    async def test_returns_404_for_nonexistent(self, client: AsyncClient):
        """DELETE /tasks/{task_id} returns 404 with error code 4240."""
        user = _make_user()
        svc = AsyncMock()
        svc.cancel_task.return_value = None

        _override(client.app, user=user, task_service=svc)

        resp = await client.delete("/tasks/no-such-task")

        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["code"] == 4240

    async def test_returns_404_for_other_users_task(self, client: AsyncClient):
        """DELETE /tasks/{task_id} returns 404 for another user's task."""
        user = _make_user()
        svc = AsyncMock()
        svc.cancel_task.return_value = None

        _override(client.app, user=user, task_service=svc)

        resp = await client.delete("/tasks/other-user-task")

        assert resp.status_code == 404

    async def test_returns_401_without_auth(self, client: AsyncClient):
        """DELETE /tasks/{task_id} returns 401 without auth token."""
        resp = await client.delete("/tasks/task-abc-123")

        assert resp.status_code in (401, 403)
