"""
TaskRecord document — persistent background task state in MongoDB.

While Celery stores results in Redis (ephemeral), TaskRecord provides durable
task state that survives Redis restarts, supports complex queries (by user,
status, date range), and records LLM cost data for billing.

BaseTask lifecycle hooks (src/tasks/base.py) keep TaskRecord synchronized
with Celery task lifecycle events.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from beanie import PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class TaskStatus(StrEnum):
    """Task lifecycle states."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    """Task priority levels mapped to Celery queues."""

    INTERACTIVE = "interactive"
    BATCH = "batch"


class TaskRecord(TimestampedDocument):
    """
    Persistent record of a background task submitted to Celery.

    One TaskRecord is created per task submission. The BaseTask callbacks
    update status, timestamps, and result/error fields as the task moves
    through its lifecycle.

    Fields:
        user_id: The user who submitted this task.
        task_id: Unique identifier (UUID4 string) for this task.
        task_type: The Celery task name (e.g., "tasks.batch.tailor_resume").
        priority: Queue assignment — interactive (fast) or batch (background).
        status: Current lifecycle state.
        input_payload: Arguments passed to the task.
        result_payload: Task return value (set on success).
        error_message: Exception message (set on failure).
        error_traceback: Full traceback string (set on failure).
        retry_count: Number of retries attempted so far.
        max_retries: Maximum retries before dead-lettering.
        submitted_at: When the task was submitted to the queue.
        started_at: When a worker began processing.
        completed_at: When processing finished (success or final failure).
        llm_tokens_used: Total LLM tokens consumed (extracted from result).
        llm_cost_usd: Total LLM cost in USD (extracted from result).
        celery_task_id: The Celery-assigned task ID for correlation.
    """

    user_id: PydanticObjectId
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: str
    priority: TaskPriority = TaskPriority.BATCH
    status: TaskStatus = TaskStatus.QUEUED
    input_payload: dict = Field(default_factory=dict)
    result_payload: dict | None = None
    error_message: str | None = None
    error_traceback: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    llm_tokens_used: int | None = None
    llm_cost_usd: float | None = None
    celery_task_id: str | None = None

    class Settings:
        name = "task_records"
        indexes = [
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("priority", ASCENDING)]),
            IndexModel([("task_id", ASCENDING)], unique=True),
        ]
