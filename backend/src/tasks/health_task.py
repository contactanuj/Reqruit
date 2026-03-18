"""Periodic Celery beat task for queue health logging."""

import structlog
from celery import shared_task

from src.tasks.base import BaseTask, _run_async

logger = structlog.get_logger()


@shared_task(bind=True, base=BaseTask, name="tasks.batch.log_queue_health")
def log_queue_health(self):
    """
    Periodic task that logs queue health metrics via structlog.

    Runs every 5 minutes via Celery beat. This is an internal monitoring
    task — it does NOT create a TaskRecord.
    """
    from src.repositories.task_record_repository import TaskRecordRepository
    from src.tasks.metrics import QueueMetrics

    async def _collect_and_log():
        repo = TaskRecordRepository()
        metrics = QueueMetrics(repo=repo)
        data = await metrics.get_all_metrics()
        logger.info("queue_health_metrics", **data)
        return data

    return _run_async(_collect_and_log())
