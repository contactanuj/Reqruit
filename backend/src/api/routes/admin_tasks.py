"""
Admin endpoints for background task management.

Endpoints
---------
    GET /admin/tasks/dlq             Query dead-lettered tasks with full diagnostic context
    GET /admin/tasks/queue/health    Queue health metrics for monitoring
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.dependencies import get_current_admin_user
from src.db.documents.user import User
from src.repositories.task_record_repository import TaskRecordRepository
from src.tasks.metrics import QueueMetrics

logger = structlog.get_logger()

router = APIRouter(prefix="/admin/tasks", tags=["admin-tasks"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DLQEntryResponse(BaseModel):
    task_id: str
    user_id: str
    task_type: str
    priority: str
    input_payload: dict
    error_message: str | None = None
    error_traceback: str | None = None
    retry_count: int
    max_retries: int
    submitted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class DLQListResponse(BaseModel):
    tasks: list[DLQEntryResponse]
    total: int


class QueueLaneHealth(BaseModel):
    queue_name: str
    depth: int | None = None


class QueueHealthResponse(BaseModel):
    lanes: list[QueueLaneHealth]
    active_worker_count: int
    dlq_size: int
    tasks_processed_24h: int
    processing_time_p50_ms: float | None = None
    processing_time_p95_ms: float | None = None
    processing_time_p99_ms: float | None = None
    failure_rate_pct: float | None = None
    timestamp: datetime


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/dlq", response_model=DLQListResponse)
async def get_dead_letter_queue(
    admin_user: User = Depends(get_current_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    task_type: str | None = Query(None),
) -> DLQListResponse:
    """Query dead-lettered tasks with full diagnostic context."""
    repo = TaskRecordRepository()

    if task_type:
        tasks = await repo.find_dead_lettered_by_type(
            task_type=task_type, skip=skip, limit=limit
        )
    else:
        tasks = await repo.find_dead_lettered(skip=skip, limit=limit)

    total = await repo.count_dead_lettered()

    logger.info(
        "dlq_queried",
        admin_user_id=str(admin_user.id),
        result_count=len(tasks),
        filters={"task_type": task_type} if task_type else {},
    )

    return DLQListResponse(
        tasks=[
            DLQEntryResponse(
                task_id=t.task_id,
                user_id=str(t.user_id),
                task_type=t.task_type,
                priority=t.priority.value,
                input_payload=t.input_payload,
                error_message=t.error_message,
                error_traceback=t.error_traceback,
                retry_count=t.retry_count,
                max_retries=t.max_retries,
                submitted_at=t.submitted_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
            )
            for t in tasks
        ],
        total=total,
    )


@router.get("/queue/health", response_model=QueueHealthResponse)
async def get_queue_health(
    admin_user: User = Depends(get_current_admin_user),
) -> QueueHealthResponse:
    """Queue health metrics: depths, worker count, DLQ size, throughput, percentiles."""
    from datetime import UTC, timedelta

    repo = TaskRecordRepository()
    metrics = QueueMetrics(repo=repo)

    # Queue depths from Redis
    queue_depths = await metrics.get_queue_depths()

    # Active workers from Celery
    try:
        from src.tasks.celery_app import celery_app

        active = celery_app.control.inspect(timeout=2.0).active()
        worker_count = len(active) if active else 0
    except Exception:
        worker_count = 0

    # MongoDB aggregates
    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)
    dlq_size = await repo.count_dead_lettered()
    tasks_processed_24h = await repo.count_completed_since(since_24h)

    # Processing time percentiles and failure rate
    percentiles = await metrics.get_processing_time_percentiles()
    failure_rate = await metrics.get_failure_rate()

    logger.info(
        "queue_health_checked",
        admin_user_id=str(admin_user.id),
        dlq_size=dlq_size,
        tasks_processed_24h=tasks_processed_24h,
        worker_count=worker_count,
        failure_rate_pct=failure_rate,
    )

    return QueueHealthResponse(
        lanes=[
            QueueLaneHealth(queue_name=name, depth=depth)
            for name, depth in queue_depths.items()
        ],
        active_worker_count=worker_count,
        dlq_size=dlq_size,
        tasks_processed_24h=tasks_processed_24h,
        processing_time_p50_ms=percentiles.get("p50"),
        processing_time_p95_ms=percentiles.get("p95"),
        processing_time_p99_ms=percentiles.get("p99"),
        failure_rate_pct=failure_rate,
        timestamp=now,
    )
