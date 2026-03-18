"""
Background task submission, status polling, and result retrieval routes.

Endpoints
---------
    POST   /tasks/submit            Submit a new background task
    GET    /tasks/{task_id}/status  Poll task status (lightweight)
    GET    /tasks/{task_id}/result  Retrieve full task result
    GET    /tasks/                  List user's tasks (paginated)
    DELETE /tasks/{task_id}         Cancel a queued or processing task
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.dependencies import get_current_user, get_task_service
from src.db.documents.task_record import TaskPriority, TaskStatus
from src.db.documents.user import User
from src.services.task_service import TaskService

logger = structlog.get_logger()

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class TaskSubmitRequest(BaseModel):
    task_type: str
    payload: dict
    priority: TaskPriority = TaskPriority.BATCH


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str = "queued"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    task_type: str
    priority: str
    submitted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    result_payload: dict | None = None
    error_message: str | None = None
    completed_at: datetime | None = None
    llm_tokens_used: int | None = None
    llm_cost_usd: float | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskStatusResponse]
    total: int


class TaskCancelResponse(BaseModel):
    task_id: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": 4240, "message": "Task not found"},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/submit", response_model=TaskSubmitResponse)
async def submit_task(
    body: TaskSubmitRequest,
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskSubmitResponse:
    """Submit a new background task to the appropriate Celery queue."""
    priority = TaskPriority(body.priority)
    record = await task_service.submit_task(
        user_id=current_user.id,
        task_type=body.task_type,
        payload=body.payload,
        priority=priority,
    )
    return TaskSubmitResponse(task_id=record.task_id, status=record.status.value)


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskStatusResponse:
    """Poll the current status of a background task."""
    record = await task_service.get_task_status(current_user.id, task_id)
    if record is None:
        raise _task_not_found()
    return TaskStatusResponse(
        task_id=record.task_id,
        status=record.status.value,
        task_type=record.task_type,
        priority=record.priority.value,
        submitted_at=record.submitted_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )


@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(
    task_id: str,
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResultResponse:
    """Retrieve the full result of a completed background task."""
    record = await task_service.get_task_result(current_user.id, task_id)
    if record is None:
        raise _task_not_found()
    return TaskResultResponse(
        task_id=record.task_id,
        status=record.status.value,
        result_payload=record.result_payload,
        error_message=record.error_message,
        completed_at=record.completed_at,
        llm_tokens_used=record.llm_tokens_used,
        llm_cost_usd=record.llm_cost_usd,
    )


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> TaskListResponse:
    """List the authenticated user's background tasks with optional status filter."""
    task_status = TaskStatus(status) if status else None
    tasks = await task_service.list_user_tasks(
        user_id=current_user.id, status=task_status, skip=skip, limit=limit
    )
    return TaskListResponse(
        tasks=[
            TaskStatusResponse(
                task_id=t.task_id,
                status=t.status.value,
                task_type=t.task_type,
                priority=t.priority.value,
                submitted_at=t.submitted_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
            )
            for t in tasks
        ],
        total=len(tasks),
    )


@router.delete("/{task_id}", response_model=TaskCancelResponse)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskCancelResponse:
    """Cancel a queued or processing background task."""
    result = await task_service.cancel_task(current_user.id, task_id)
    if result is None:
        raise _task_not_found()
    return TaskCancelResponse(**result)
