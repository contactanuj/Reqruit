"""Tests for TaskService — task submission, status, result, listing, and cancellation."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.db.documents.task_record import TaskPriority, TaskRecord, TaskStatus
from src.services.task_service import TaskService

USER_A = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
USER_B = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


def _make_service(repo=None, celery=None):
    repo = repo or AsyncMock()
    celery = celery or MagicMock()
    return TaskService(repo=repo, celery=celery), repo, celery


def _make_record(user_id=USER_A, task_id="task-123", **kwargs):
    defaults = {
        "user_id": user_id,
        "task_id": task_id,
        "task_type": "test_task",
        "priority": TaskPriority.BATCH,
        "status": TaskStatus.QUEUED,
    }
    defaults.update(kwargs)
    record = MagicMock(spec=TaskRecord)
    for k, v in defaults.items():
        setattr(record, k, v)
    return record


# ---------------------------------------------------------------------------
# submit_task
# ---------------------------------------------------------------------------


class TestSubmitTask:
    async def test_creates_record_with_queued_status(self):
        """submit_task creates a TaskRecord via repo.create."""
        svc, repo, celery = _make_service()
        celery.send_task.return_value = MagicMock(id="celery-xyz")

        await svc.submit_task(USER_A, "resume_tailor", {"key": "val"})

        repo.create.assert_called_once()
        created = repo.create.call_args[0][0]
        assert created.status == TaskStatus.QUEUED
        assert created.user_id == USER_A
        assert created.task_type == "resume_tailor"

    async def test_dispatches_to_interactive_queue(self):
        """submit_task routes INTERACTIVE priority to interactive queue."""
        svc, repo, celery = _make_service()
        celery.send_task.return_value = MagicMock(id="celery-xyz")

        await svc.submit_task(USER_A, "cover_letter", {}, TaskPriority.INTERACTIVE)

        celery.send_task.assert_called_once()
        call_kwargs = celery.send_task.call_args
        assert call_kwargs[1]["queue"] == "interactive"
        assert call_kwargs[0][0] == "tasks.interactive.cover_letter"

    async def test_dispatches_to_batch_queue(self):
        """submit_task routes BATCH priority to batch queue."""
        svc, repo, celery = _make_service()
        celery.send_task.return_value = MagicMock(id="celery-xyz")

        await svc.submit_task(USER_A, "skills_analysis", {}, TaskPriority.BATCH)

        call_kwargs = celery.send_task.call_args
        assert call_kwargs[1]["queue"] == "batch"
        assert call_kwargs[0][0] == "tasks.batch.skills_analysis"

    async def test_stores_celery_task_id(self):
        """submit_task stores celery_task_id from send_task return."""
        svc, repo, celery = _make_service()
        celery.send_task.return_value = MagicMock(id="celery-abc-456")

        await svc.submit_task(USER_A, "jd_decode", {})

        repo.update_status.assert_called_once()
        call_kwargs = repo.update_status.call_args
        assert call_kwargs[1]["celery_task_id"] == "celery-abc-456"


# ---------------------------------------------------------------------------
# get_task_status
# ---------------------------------------------------------------------------


class TestGetTaskStatus:
    async def test_returns_record_for_matching_user(self):
        """get_task_status returns the record when user_id matches."""
        svc, repo, _ = _make_service()
        record = _make_record(user_id=USER_A)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.get_task_status(USER_A, "task-123")

        assert result is record

    async def test_returns_none_for_mismatched_user(self):
        """get_task_status returns None when user_id does not match (isolation)."""
        svc, repo, _ = _make_service()
        record = _make_record(user_id=USER_A)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.get_task_status(USER_B, "task-123")

        assert result is None

    async def test_returns_none_for_nonexistent_task(self):
        """get_task_status returns None for non-existent task_id."""
        svc, repo, _ = _make_service()
        repo.find_by_task_id = AsyncMock(return_value=None)

        result = await svc.get_task_status(USER_A, "no-such-task")

        assert result is None


# ---------------------------------------------------------------------------
# get_task_result
# ---------------------------------------------------------------------------


class TestGetTaskResult:
    async def test_returns_full_record(self):
        """get_task_result returns record including result_payload."""
        svc, repo, _ = _make_service()
        record = _make_record(
            user_id=USER_A,
            result_payload={"output": "done"},
            llm_tokens_used=500,
            llm_cost_usd=0.01,
        )
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.get_task_result(USER_A, "task-123")

        assert result is record
        assert result.result_payload == {"output": "done"}

    async def test_returns_none_for_mismatched_user(self):
        """get_task_result returns None when user_id does not match."""
        svc, repo, _ = _make_service()
        record = _make_record(user_id=USER_A)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.get_task_result(USER_B, "task-123")

        assert result is None


# ---------------------------------------------------------------------------
# list_user_tasks
# ---------------------------------------------------------------------------


class TestListUserTasks:
    async def test_returns_tasks_for_user(self):
        """list_user_tasks returns tasks from repo for the given user."""
        svc, repo, _ = _make_service()
        records = [_make_record(user_id=USER_A, task_id=f"t-{i}") for i in range(3)]
        repo.find_by_user_and_status = AsyncMock(return_value=records)

        result = await svc.list_user_tasks(USER_A)

        assert len(result) == 3
        repo.find_by_user_and_status.assert_called_once_with(
            user_id=USER_A, status=None, skip=0, limit=20
        )

    async def test_filters_by_status(self):
        """list_user_tasks passes status filter to repo."""
        svc, repo, _ = _make_service()
        repo.find_by_user_and_status = AsyncMock(return_value=[])

        await svc.list_user_tasks(USER_A, status=TaskStatus.COMPLETED)

        repo.find_by_user_and_status.assert_called_once_with(
            user_id=USER_A, status=TaskStatus.COMPLETED, skip=0, limit=20
        )

    async def test_pagination(self):
        """list_user_tasks passes skip/limit to repo."""
        svc, repo, _ = _make_service()
        repo.find_by_user_and_status = AsyncMock(return_value=[])

        await svc.list_user_tasks(USER_A, skip=10, limit=5)

        repo.find_by_user_and_status.assert_called_once_with(
            user_id=USER_A, status=None, skip=10, limit=5
        )


# ---------------------------------------------------------------------------
# cancel_task
# ---------------------------------------------------------------------------


class TestCancelTask:
    async def test_queued_task_revoked_and_cancelled(self):
        """cancel_task for QUEUED: revoke(terminate=False), status=CANCELLED."""
        svc, repo, celery = _make_service()
        record = _make_record(status=TaskStatus.QUEUED, celery_task_id="cel-1")
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.cancel_task(USER_A, "task-123")

        assert result["status"] == "cancelled"
        assert result["message"] == "Task cancelled successfully"
        celery.control.revoke.assert_called_once_with("cel-1", terminate=False)
        repo.update_status.assert_called_once()

    async def test_processing_task_best_effort(self):
        """cancel_task for PROCESSING: revoke(terminate=True, signal=SIGTERM)."""
        svc, repo, celery = _make_service()
        record = _make_record(status=TaskStatus.PROCESSING, celery_task_id="cel-2")
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.cancel_task(USER_A, "task-123")

        assert result["status"] == "processing"
        assert "already processing" in result["message"]
        celery.control.revoke.assert_called_once_with(
            "cel-2", terminate=True, signal="SIGTERM"
        )
        repo.update_status.assert_not_called()

    async def test_completed_task_terminal(self):
        """cancel_task for COMPLETED: returns terminal state, no revoke."""
        svc, repo, celery = _make_service()
        record = _make_record(status=TaskStatus.COMPLETED)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.cancel_task(USER_A, "task-123")

        assert result["status"] == "completed"
        assert "terminal state" in result["message"]
        celery.control.revoke.assert_not_called()

    async def test_failed_task_terminal(self):
        """cancel_task for FAILED: returns terminal state."""
        svc, repo, celery = _make_service()
        record = _make_record(status=TaskStatus.FAILED)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.cancel_task(USER_A, "task-123")

        assert result["status"] == "failed"
        celery.control.revoke.assert_not_called()

    async def test_dead_lettered_task_terminal(self):
        """cancel_task for DEAD_LETTERED: returns terminal state."""
        svc, repo, celery = _make_service()
        record = _make_record(status=TaskStatus.DEAD_LETTERED)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.cancel_task(USER_A, "task-123")

        assert result["status"] == "dead_lettered"

    async def test_cancelled_task_idempotent(self):
        """cancel_task for already CANCELLED: returns terminal state."""
        svc, repo, celery = _make_service()
        record = _make_record(status=TaskStatus.CANCELLED)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.cancel_task(USER_A, "task-123")

        assert result["status"] == "cancelled"
        assert "terminal state" in result["message"]

    async def test_nonexistent_task_returns_none(self):
        """cancel_task for non-existent task returns None."""
        svc, repo, _celery = _make_service()
        repo.find_by_task_id = AsyncMock(return_value=None)

        result = await svc.cancel_task(USER_A, "no-such-task")

        assert result is None

    async def test_other_users_task_returns_none(self):
        """cancel_task for another user's task returns None."""
        svc, repo, _celery = _make_service()
        record = _make_record(user_id=USER_A)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.cancel_task(USER_B, "task-123")

        assert result is None

    async def test_no_celery_task_id_skips_revoke(self):
        """cancel_task when celery_task_id is None: updates status without revoke."""
        svc, repo, celery = _make_service()
        record = _make_record(status=TaskStatus.QUEUED, celery_task_id=None)
        repo.find_by_task_id = AsyncMock(return_value=record)

        result = await svc.cancel_task(USER_A, "task-123")

        assert result["status"] == "cancelled"
        celery.control.revoke.assert_not_called()
        repo.update_status.assert_called_once()

    async def test_revoke_exception_still_cancels(self):
        """cancel_task when Celery revoke raises: still updates to CANCELLED."""
        svc, repo, celery = _make_service()
        record = _make_record(status=TaskStatus.QUEUED, celery_task_id="cel-fail")
        repo.find_by_task_id = AsyncMock(return_value=record)
        celery.control.revoke.side_effect = ConnectionError("Redis down")

        result = await svc.cancel_task(USER_A, "task-123")

        assert result["status"] == "cancelled"
        repo.update_status.assert_called_once()
