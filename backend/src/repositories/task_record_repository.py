"""Repository for TaskRecord documents — background task state queries."""

from datetime import datetime

import structlog
from beanie import PydanticObjectId

from src.db.documents.task_record import TaskRecord, TaskStatus
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class TaskRecordRepository(BaseRepository[TaskRecord]):
    """Data access for background task records."""

    def __init__(self) -> None:
        super().__init__(TaskRecord)

    async def find_by_task_id(self, task_id: str) -> TaskRecord | None:
        """Find a task record by its unique task_id (UUID string)."""
        return await self.find_one({"task_id": task_id})

    async def find_by_user_and_status(
        self,
        user_id: PydanticObjectId,
        status: TaskStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[TaskRecord]:
        """
        Find tasks for a user, optionally filtered by status.

        Returns tasks ordered by created_at descending (newest first).
        """
        filters: dict = {"user_id": user_id}
        if status is not None:
            filters["status"] = status.value
        return await self.find_many(
            filters=filters,
            skip=skip,
            limit=limit,
            sort="-created_at",
        )

    async def update_status(
        self, task_id: str, status: TaskStatus, **kwargs
    ) -> TaskRecord | None:
        """
        Atomically update a task's status and any additional fields.

        Additional keyword arguments are passed directly to the $set operation.
        Common kwargs: started_at, completed_at, result_payload, error_message,
        error_traceback, retry_count, celery_task_id, llm_tokens_used, llm_cost_usd.
        """
        record = await self.find_by_task_id(task_id)
        if record is None:
            return None

        update_data = {"status": status, **kwargs}
        await record.set(update_data)

        logger.info(
            "task_status_updated",
            task_id=task_id,
            new_status=status.value,
        )
        return record

    async def find_dead_lettered(
        self, skip: int = 0, limit: int = 50
    ) -> list[TaskRecord]:
        """Find tasks that exhausted all retries, ordered by created_at descending."""
        return await self.find_many(
            filters={"status": TaskStatus.DEAD_LETTERED.value},
            skip=skip,
            limit=limit,
            sort="-created_at",
        )

    async def count_by_status(self, status: TaskStatus) -> int:
        """Count tasks in a given status."""
        return await self.count({"status": status.value})

    async def count_dead_lettered(self) -> int:
        """Count tasks with DEAD_LETTERED status."""
        return await self.count({"status": TaskStatus.DEAD_LETTERED.value})

    async def find_dead_lettered_by_type(
        self, task_type: str, skip: int = 0, limit: int = 50
    ) -> list[TaskRecord]:
        """Find dead-lettered tasks filtered by task_type."""
        return await self.find_many(
            filters={
                "status": TaskStatus.DEAD_LETTERED.value,
                "task_type": task_type,
            },
            skip=skip,
            limit=limit,
            sort="-created_at",
        )

    async def count_completed_since(self, since: datetime) -> int:
        """Count tasks completed since a given datetime."""
        return await self.count({
            "status": TaskStatus.COMPLETED.value,
            "completed_at": {"$gte": since},
        })

    async def find_completed_since(
        self, since: datetime, limit: int = 10000
    ) -> list[TaskRecord]:
        """Fetch completed tasks since a given datetime for percentile calculation."""
        return await self.find_many(
            filters={
                "status": TaskStatus.COMPLETED.value,
                "completed_at": {"$gte": since},
            },
            skip=0,
            limit=limit,
            sort="-completed_at",
        )

    async def count_failed_since(self, since: datetime) -> int:
        """Count tasks with FAILED or DEAD_LETTERED status since a given datetime."""
        return await self.count({
            "status": {"$in": [TaskStatus.FAILED.value, TaskStatus.DEAD_LETTERED.value]},
            "completed_at": {"$gte": since},
        })

    async def count_total_since(self, since: datetime) -> int:
        """Count all terminal tasks since a given datetime."""
        terminal = [
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.DEAD_LETTERED.value,
        ]
        return await self.count({
            "status": {"$in": terminal},
            "completed_at": {"$gte": since},
        })
