"""Tests for TaskRecordRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.db.documents.task_record import TaskPriority, TaskRecord, TaskStatus
from src.repositories.task_record_repository import TaskRecordRepository

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
TASK_ID = "test-task-id-uuid4"


def _make_task_record(**kwargs) -> MagicMock:
    defaults = {
        "user_id": USER_ID,
        "task_id": TASK_ID,
        "task_type": "tasks.batch.test_task",
        "priority": TaskPriority.BATCH,
        "status": TaskStatus.QUEUED,
        "input_payload": {},
        "result_payload": None,
        "error_message": None,
        "error_traceback": None,
        "retry_count": 0,
        "max_retries": 3,
        "submitted_at": datetime(2026, 3, 16, tzinfo=UTC),
        "started_at": None,
        "completed_at": None,
        "llm_tokens_used": None,
        "llm_cost_usd": None,
        "celery_task_id": None,
        "created_at": datetime(2026, 3, 16, tzinfo=UTC),
    }
    defaults.update(kwargs)
    doc = MagicMock(spec=TaskRecord)
    doc.set = AsyncMock()
    for k, v in defaults.items():
        setattr(doc, k, v)
    return doc


class TestFindByTaskId:
    async def test_returns_correct_record(self):
        """find_by_task_id delegates to find_one with task_id filter."""
        repo = TaskRecordRepository()
        record = _make_task_record()
        repo.find_one = AsyncMock(return_value=record)

        result = await repo.find_by_task_id(TASK_ID)

        assert result is record
        repo.find_one.assert_called_once_with({"task_id": TASK_ID})

    async def test_returns_none_when_not_found(self):
        """find_by_task_id returns None when task doesn't exist."""
        repo = TaskRecordRepository()
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.find_by_task_id("nonexistent-id")

        assert result is None


class TestFindByUserAndStatus:
    async def test_filters_by_user_and_status(self):
        """find_by_user_and_status filters by both user_id and status."""
        repo = TaskRecordRepository()
        records = [_make_task_record(), _make_task_record()]
        repo.find_many = AsyncMock(return_value=records)

        result = await repo.find_by_user_and_status(
            USER_ID, status=TaskStatus.QUEUED
        )

        assert len(result) == 2
        repo.find_many.assert_called_once_with(
            filters={"user_id": USER_ID, "status": "queued"},
            skip=0,
            limit=20,
            sort="-created_at",
        )

    async def test_filters_by_user_only(self):
        """find_by_user_and_status with status=None filters by user only."""
        repo = TaskRecordRepository()
        repo.find_many = AsyncMock(return_value=[])

        await repo.find_by_user_and_status(USER_ID, status=None)

        repo.find_many.assert_called_once_with(
            filters={"user_id": USER_ID},
            skip=0,
            limit=20,
            sort="-created_at",
        )

    async def test_pagination_params(self):
        """find_by_user_and_status passes skip and limit correctly."""
        repo = TaskRecordRepository()
        repo.find_many = AsyncMock(return_value=[])

        await repo.find_by_user_and_status(USER_ID, skip=10, limit=5)

        call_kwargs = repo.find_many.call_args[1]
        assert call_kwargs["skip"] == 10
        assert call_kwargs["limit"] == 5


class TestUpdateStatus:
    async def test_atomically_updates_fields(self):
        """update_status sets status and additional kwargs."""
        repo = TaskRecordRepository()
        record = _make_task_record()
        repo.find_by_task_id = AsyncMock(return_value=record)

        now = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)
        result = await repo.update_status(
            TASK_ID,
            TaskStatus.PROCESSING,
            started_at=now,
            celery_task_id="celery-123",
        )

        assert result is record
        record.set.assert_awaited_once()
        call_args = record.set.call_args[0][0]
        assert call_args["status"] == TaskStatus.PROCESSING
        assert call_args["started_at"] == now
        assert call_args["celery_task_id"] == "celery-123"

    async def test_returns_none_when_not_found(self):
        """update_status returns None when task doesn't exist."""
        repo = TaskRecordRepository()
        repo.find_by_task_id = AsyncMock(return_value=None)

        result = await repo.update_status(
            "nonexistent-id", TaskStatus.PROCESSING
        )

        assert result is None


class TestFindDeadLettered:
    async def test_returns_only_dead_lettered_tasks(self):
        """find_dead_lettered queries for DEAD_LETTERED status."""
        repo = TaskRecordRepository()
        dl_record = _make_task_record(status=TaskStatus.DEAD_LETTERED)
        repo.find_many = AsyncMock(return_value=[dl_record])

        result = await repo.find_dead_lettered()

        assert len(result) == 1
        repo.find_many.assert_called_once_with(
            filters={"status": "dead_lettered"},
            skip=0,
            limit=50,
            sort="-created_at",
        )


class TestCountByStatus:
    async def test_returns_correct_count(self):
        """count_by_status delegates to count with status filter."""
        repo = TaskRecordRepository()
        repo.count = AsyncMock(return_value=5)

        result = await repo.count_by_status(TaskStatus.QUEUED)

        assert result == 5
        repo.count.assert_called_once_with({"status": "queued"})


class TestTaskRecordDefaults:
    def test_default_status_is_queued(self):
        """TaskStatus default should be QUEUED."""
        assert TaskStatus.QUEUED == "queued"

    def test_default_priority_is_batch(self):
        """TaskPriority default should be BATCH."""
        assert TaskPriority.BATCH == "batch"

    def test_all_status_values(self):
        """All expected TaskStatus values exist."""
        expected = {"queued", "processing", "completed", "failed", "dead_lettered", "cancelled"}
        actual = {s.value for s in TaskStatus}
        assert actual == expected

    def test_all_priority_values(self):
        """All expected TaskPriority values exist."""
        expected = {"interactive", "batch"}
        actual = {p.value for p in TaskPriority}
        assert actual == expected


class TestTaskRecordIndexes:
    def test_indexes_are_defined(self):
        """TaskRecord Settings defines the required indexes."""
        indexes = TaskRecord.Settings.indexes
        assert len(indexes) == 4

    def test_collection_name(self):
        """TaskRecord Settings specifies task_records collection."""
        assert TaskRecord.Settings.name == "task_records"
