"""
Task submission and status management service.

Orchestrates background task lifecycle: submit to Celery, query status,
retrieve results. All queries are user-scoped — a user can only see
their own tasks.

Performance budgets (from NFR-6.2, NFR-6.3):
    - submit_task: <200ms (MongoDB insert + Redis enqueue only)
    - get_task_status: <100ms (indexed MongoDB read)
"""

from datetime import UTC, datetime
from uuid import uuid4

import structlog
from beanie import PydanticObjectId
from celery import Celery

from src.db.documents.task_record import TaskPriority, TaskRecord, TaskStatus
from src.repositories.task_record_repository import TaskRecordRepository

logger = structlog.get_logger()

VALID_TASK_TYPES = frozenset({
    "application_assembly",
    "cover_letter",
    "interview_prep",
    "skills_analysis",
    "jd_decode",
    "outreach",
    "negotiation",
    "onboarding",
    "resume_tailor",
    "weekly_review",
})


class TaskService:
    """Business logic for background task management."""

    def __init__(self, repo: TaskRecordRepository, celery: Celery) -> None:
        self._repo = repo
        self._celery = celery

    async def submit_task(
        self,
        user_id: PydanticObjectId,
        task_type: str,
        payload: dict,
        priority: TaskPriority = TaskPriority.BATCH,
    ) -> TaskRecord:
        """
        Create a TaskRecord and dispatch the task to Celery.

        Returns the persisted TaskRecord with celery_task_id set.
        """
        if task_type not in VALID_TASK_TYPES:
            raise ValueError(f"Invalid task_type '{task_type}'. Must be one of: {sorted(VALID_TASK_TYPES)}")

        task_id = str(uuid4())
        record = TaskRecord(
            user_id=user_id,
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            status=TaskStatus.QUEUED,
            input_payload=payload,
        )
        await self._repo.create(record)

        queue = "interactive" if priority == TaskPriority.INTERACTIVE else "batch"
        try:
            result = self._celery.send_task(
                f"tasks.{queue}.{task_type}",
                kwargs={"reqruit_task_id": task_id, **payload},
                queue=queue,
            )
        except Exception:
            await self._repo.update_status(task_id, TaskStatus.FAILED)
            logger.error("celery_dispatch_failed", task_id=task_id, task_type=task_type)
            raise
        record.celery_task_id = result.id
        await self._repo.update_status(
            task_id, TaskStatus.QUEUED, celery_task_id=result.id
        )

        logger.info(
            "task_submitted",
            task_id=task_id,
            task_type=task_type,
            priority=priority.value,
            user_id=str(user_id),
        )
        return record

    async def get_task_status(
        self, user_id: PydanticObjectId, task_id: str
    ) -> TaskRecord | None:
        """
        Fetch task status for the given user.

        Returns None if the task does not exist or belongs to another user
        (user isolation — indistinguishable from not found).
        """
        record = await self._repo.find_by_task_id(task_id)
        if record is None or record.user_id != user_id:
            return None

        logger.info("task_status_polled", task_id=task_id)
        return record

    async def get_task_result(
        self, user_id: PydanticObjectId, task_id: str
    ) -> TaskRecord | None:
        """
        Fetch full task result for the given user.

        Returns None if the task does not exist or belongs to another user.
        """
        record = await self._repo.find_by_task_id(task_id)
        if record is None or record.user_id != user_id:
            return None

        logger.info("task_result_fetched", task_id=task_id)
        return record

    async def list_user_tasks(
        self,
        user_id: PydanticObjectId,
        status: TaskStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[TaskRecord]:
        """List tasks for the authenticated user, optionally filtered by status."""
        return await self._repo.find_by_user_and_status(
            user_id=user_id, status=status, skip=skip, limit=limit
        )

    _TERMINAL_STATUSES = frozenset({
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.DEAD_LETTERED,
        TaskStatus.CANCELLED,
    })

    async def cancel_task(
        self, user_id: PydanticObjectId, task_id: str
    ) -> dict | None:
        """
        Cancel a task. Semantics depend on current state:
        - QUEUED: revoke + mark CANCELLED
        - PROCESSING: best-effort revoke (SIGTERM), don't change status
        - Terminal: return current state, no action
        Returns None if task not found or user mismatch.
        """
        record = await self._repo.find_by_task_id(task_id)
        if record is None or record.user_id != user_id:
            return None

        if record.status == TaskStatus.QUEUED:
            if record.celery_task_id:
                try:
                    self._celery.control.revoke(
                        record.celery_task_id, terminate=False
                    )
                except Exception:
                    logger.warning(
                        "celery_revoke_failed",
                        task_id=task_id,
                        reason="revoke_exception",
                    )
            await self._repo.update_status(
                task_id, TaskStatus.CANCELLED, completed_at=datetime.now(UTC)
            )
            logger.info(
                "task_cancelled",
                task_id=task_id,
                previous_status="queued",
                user_id=str(user_id),
            )
            return {
                "task_id": task_id,
                "status": "cancelled",
                "message": "Task cancelled successfully",
            }

        if record.status == TaskStatus.PROCESSING:
            if record.celery_task_id:
                try:
                    self._celery.control.revoke(
                        record.celery_task_id, terminate=True, signal="SIGTERM"
                    )
                except Exception:
                    logger.warning(
                        "celery_revoke_failed",
                        task_id=task_id,
                        reason="revoke_exception",
                    )
            logger.info(
                "task_cancel_best_effort",
                task_id=task_id,
                user_id=str(user_id),
            )
            return {
                "task_id": task_id,
                "status": "processing",
                "message": (
                    "Cancellation requested; task is already processing "
                    "and may complete before cancellation takes effect"
                ),
            }

        # Terminal states
        return {
            "task_id": task_id,
            "status": record.status.value,
            "message": "Task is already in terminal state and cannot be cancelled",
        }
