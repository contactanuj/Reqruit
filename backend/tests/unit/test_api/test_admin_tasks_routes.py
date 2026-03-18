"""Tests for admin task routes: GET /admin/tasks/dlq, GET /admin/tasks/queue/health."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_admin_user, get_current_user
from src.db.documents.task_record import TaskPriority, TaskStatus

ADMIN_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
NOW = datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)


def _make_admin():
    user = MagicMock()
    user.id = ADMIN_ID
    user.email = "admin@example.com"
    user.is_active = True
    user.is_admin = True
    return user


def _make_dlq_record(**overrides):
    defaults = {
        "task_id": "dlq-task-001",
        "user_id": PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"),
        "task_type": "cover_letter_generation",
        "priority": TaskPriority.BATCH,
        "input_payload": {"job_id": "j123"},
        "error_message": "Connection refused",
        "error_traceback": "Traceback ...",
        "retry_count": 3,
        "max_retries": 3,
        "status": TaskStatus.DEAD_LETTERED,
        "submitted_at": NOW,
        "started_at": NOW,
        "completed_at": NOW,
    }
    defaults.update(overrides)
    record = MagicMock()
    for k, v in defaults.items():
        setattr(record, k, v)
    return record


class TestGetDeadLetterQueue:
    async def test_200_returns_dlq_tasks(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = AsyncMock()
        record = _make_dlq_record()
        repo.find_dead_lettered = AsyncMock(return_value=[record])
        repo.count_dead_lettered = AsyncMock(return_value=1)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with MagicMock() as mock_repo_cls:
            mock_repo_cls.return_value = repo
            with patch(
                "src.api.routes.admin_tasks.TaskRecordRepository",
                return_value=repo,
            ):
                response = await client.get("/admin/tasks/dlq")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "dlq-task-001"
        assert data["tasks"][0]["error_message"] == "Connection refused"

    async def test_200_empty_dlq(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = AsyncMock()
        repo.find_dead_lettered = AsyncMock(return_value=[])
        repo.count_dead_lettered = AsyncMock(return_value=0)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with patch(
            "src.api.routes.admin_tasks.TaskRecordRepository",
            return_value=repo,
        ):
            response = await client.get("/admin/tasks/dlq")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["tasks"] == []

    async def test_200_filters_by_task_type(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = AsyncMock()
        record = _make_dlq_record(task_type="resume_parse")
        repo.find_dead_lettered_by_type = AsyncMock(return_value=[record])
        repo.count_dead_lettered = AsyncMock(return_value=1)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with patch(
            "src.api.routes.admin_tasks.TaskRecordRepository",
            return_value=repo,
        ):
            response = await client.get(
                "/admin/tasks/dlq", params={"task_type": "resume_parse"}
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_type"] == "resume_parse"

    async def test_200_respects_pagination(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = AsyncMock()
        repo.find_dead_lettered = AsyncMock(return_value=[])
        repo.count_dead_lettered = AsyncMock(return_value=100)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with patch(
            "src.api.routes.admin_tasks.TaskRecordRepository",
            return_value=repo,
        ):
            response = await client.get(
                "/admin/tasks/dlq", params={"skip": 10, "limit": 5}
            )

        assert response.status_code == 200
        repo.find_dead_lettered.assert_called_once_with(skip=10, limit=5)

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/admin/tasks/dlq")
        assert response.status_code == 401

    async def test_403_non_admin_user(self, client: AsyncClient) -> None:
        """Non-admin user gets 403."""
        regular_user = MagicMock()
        regular_user.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        regular_user.email = "user@example.com"
        regular_user.is_active = True
        regular_user.is_admin = False

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: regular_user

        response = await client.get("/admin/tasks/dlq")
        assert response.status_code == 403

    async def test_response_includes_all_diagnostic_fields(
        self, client: AsyncClient
    ) -> None:
        """DLQ response includes full diagnostic context."""
        admin = _make_admin()
        repo = AsyncMock()
        record = _make_dlq_record(
            error_message="API timeout after 30s",
            error_traceback="Traceback (most recent call last):\n  ...",
            retry_count=3,
            max_retries=3,
        )
        repo.find_dead_lettered = AsyncMock(return_value=[record])
        repo.count_dead_lettered = AsyncMock(return_value=1)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with patch(
            "src.api.routes.admin_tasks.TaskRecordRepository",
            return_value=repo,
        ):
            response = await client.get("/admin/tasks/dlq")

        task = response.json()["tasks"][0]
        assert task["error_message"] == "API timeout after 30s"
        assert "Traceback" in task["error_traceback"]
        assert task["retry_count"] == 3
        assert task["max_retries"] == 3
        assert task["input_payload"] == {"job_id": "j123"}


def _make_health_repo():
    """Build a mock repo for queue health endpoint."""
    repo = AsyncMock()
    repo.count_dead_lettered = AsyncMock(return_value=3)
    repo.count_completed_since = AsyncMock(return_value=150)
    repo.find_completed_since = AsyncMock(return_value=[])
    repo.count_failed_since = AsyncMock(return_value=0)
    repo.count_total_since = AsyncMock(return_value=0)
    return repo


def _mock_metrics(queue_depths=None, percentiles=None, failure_rate=None):
    """Build a mock QueueMetrics."""
    m = AsyncMock()
    m.get_queue_depths = AsyncMock(
        return_value=queue_depths or {"interactive": 5, "batch": 12}
    )
    m.get_processing_time_percentiles = AsyncMock(
        return_value=percentiles or {"p50": None, "p95": None, "p99": None}
    )
    m.get_failure_rate = AsyncMock(return_value=failure_rate)
    return m


class TestGetQueueHealth:
    async def test_200_returns_health_fields(self, client: AsyncClient) -> None:
        """Health endpoint returns all expected fields."""
        admin = _make_admin()
        repo = _make_health_repo()
        mock_m = _mock_metrics()

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with (
            patch("src.api.routes.admin_tasks.TaskRecordRepository", return_value=repo),
            patch("src.api.routes.admin_tasks.QueueMetrics", return_value=mock_m),
            patch("src.tasks.celery_app.celery_app") as mock_celery,
        ):
            mock_celery.control.inspect.return_value.active.return_value = {
                "worker1@host": [],
                "worker2@host": [],
            }
            response = await client.get("/admin/tasks/queue/health")

        assert response.status_code == 200
        data = response.json()
        assert "lanes" in data
        assert "active_worker_count" in data
        assert data["active_worker_count"] == 2
        assert data["dlq_size"] == 3
        assert data["tasks_processed_24h"] == 150
        assert "timestamp" in data

    async def test_200_includes_queue_lane_depths(self, client: AsyncClient) -> None:
        """Health response includes interactive and batch queue depths."""
        admin = _make_admin()
        repo = _make_health_repo()
        mock_m = _mock_metrics(queue_depths={"interactive": 8, "batch": 20})

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with (
            patch("src.api.routes.admin_tasks.TaskRecordRepository", return_value=repo),
            patch("src.api.routes.admin_tasks.QueueMetrics", return_value=mock_m),
            patch("src.tasks.celery_app.celery_app") as mock_celery,
        ):
            mock_celery.control.inspect.return_value.active.return_value = None
            response = await client.get("/admin/tasks/queue/health")

        data = response.json()
        lane_names = [lane["queue_name"] for lane in data["lanes"]]
        assert "interactive" in lane_names
        assert "batch" in lane_names

    async def test_200_handles_no_workers(self, client: AsyncClient) -> None:
        """Health returns active_worker_count=0 when no workers connected."""
        admin = _make_admin()
        repo = _make_health_repo()
        mock_m = _mock_metrics()

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with (
            patch("src.api.routes.admin_tasks.TaskRecordRepository", return_value=repo),
            patch("src.api.routes.admin_tasks.QueueMetrics", return_value=mock_m),
            patch("src.tasks.celery_app.celery_app") as mock_celery,
        ):
            mock_celery.control.inspect.return_value.active.return_value = None
            response = await client.get("/admin/tasks/queue/health")

        assert response.json()["active_worker_count"] == 0

    async def test_200_includes_percentiles_when_data_exists(
        self, client: AsyncClient
    ) -> None:
        """Health includes processing time percentiles when tasks exist."""
        admin = _make_admin()
        repo = _make_health_repo()
        mock_m = _mock_metrics(
            percentiles={"p50": 150.0, "p95": 800.0, "p99": 1200.0}
        )

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with (
            patch("src.api.routes.admin_tasks.TaskRecordRepository", return_value=repo),
            patch("src.api.routes.admin_tasks.QueueMetrics", return_value=mock_m),
            patch("src.tasks.celery_app.celery_app") as mock_celery,
        ):
            mock_celery.control.inspect.return_value.active.return_value = {}
            response = await client.get("/admin/tasks/queue/health")

        data = response.json()
        assert data["processing_time_p50_ms"] == 150.0
        assert data["processing_time_p95_ms"] == 800.0
        assert data["processing_time_p99_ms"] == 1200.0

    async def test_200_percentiles_none_when_no_data(
        self, client: AsyncClient
    ) -> None:
        """Health returns None percentiles when no completed tasks."""
        admin = _make_admin()
        repo = _make_health_repo()
        mock_m = _mock_metrics()

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with (
            patch("src.api.routes.admin_tasks.TaskRecordRepository", return_value=repo),
            patch("src.api.routes.admin_tasks.QueueMetrics", return_value=mock_m),
            patch("src.tasks.celery_app.celery_app") as mock_celery,
        ):
            mock_celery.control.inspect.return_value.active.return_value = {}
            response = await client.get("/admin/tasks/queue/health")

        data = response.json()
        assert data["processing_time_p50_ms"] is None

    async def test_200_includes_failure_rate(self, client: AsyncClient) -> None:
        """Health response includes failure_rate_pct."""
        admin = _make_admin()
        repo = _make_health_repo()
        mock_m = _mock_metrics(failure_rate=2.5)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with (
            patch("src.api.routes.admin_tasks.TaskRecordRepository", return_value=repo),
            patch("src.api.routes.admin_tasks.QueueMetrics", return_value=mock_m),
            patch("src.tasks.celery_app.celery_app") as mock_celery,
        ):
            mock_celery.control.inspect.return_value.active.return_value = {}
            response = await client.get("/admin/tasks/queue/health")

        assert response.json()["failure_rate_pct"] == 2.5

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        """Unauthenticated request returns 401."""
        response = await client.get("/admin/tasks/queue/health")
        assert response.status_code == 401

    async def test_200_handles_celery_inspect_failure(
        self, client: AsyncClient
    ) -> None:
        """Health returns worker_count=0 when celery inspect fails."""
        admin = _make_admin()
        repo = _make_health_repo()
        mock_m = _mock_metrics()

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        with (
            patch("src.api.routes.admin_tasks.TaskRecordRepository", return_value=repo),
            patch("src.api.routes.admin_tasks.QueueMetrics", return_value=mock_m),
            patch("src.tasks.celery_app.celery_app") as mock_celery,
        ):
            mock_celery.control.inspect.side_effect = Exception("broker down")
            response = await client.get("/admin/tasks/queue/health")

        assert response.status_code == 200
        assert response.json()["active_worker_count"] == 0
