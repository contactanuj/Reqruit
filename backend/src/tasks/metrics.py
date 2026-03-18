"""Queue health metrics collection for monitoring and admin endpoints."""

from datetime import UTC, datetime, timedelta

import structlog

from src.repositories.task_record_repository import TaskRecordRepository

logger = structlog.get_logger()


class QueueMetrics:
    """Collects and computes queue health metrics from Redis and MongoDB."""

    def __init__(self, repo: TaskRecordRepository) -> None:
        self._repo = repo

    async def get_queue_depths(self) -> dict[str, int | None]:
        """Query Redis for message counts in interactive and batch queues."""
        try:
            from src.core.redis_client import get_redis

            redis = get_redis()
            interactive = await redis.llen("interactive")
            batch = await redis.llen("batch")
            return {"interactive": interactive, "batch": batch}
        except Exception:
            logger.warning("queue_depth_fetch_failed")
            return {"interactive": None, "batch": None}

    async def get_processing_time_percentiles(
        self, hours: int = 24
    ) -> dict[str, float | None]:
        """Calculate p50/p95/p99 processing time from completed tasks."""
        since = datetime.now(UTC) - timedelta(hours=hours)
        records = await self._repo.find_completed_since(since)

        durations_ms = [
            (r.completed_at - r.started_at).total_seconds() * 1000
            for r in records
            if r.started_at and r.completed_at
        ]

        if not durations_ms:
            return {"p50": None, "p95": None, "p99": None}

        durations_ms.sort()
        n = len(durations_ms)
        return {
            "p50": durations_ms[int(n * 0.50)],
            "p95": durations_ms[min(int(n * 0.95), n - 1)],
            "p99": durations_ms[min(int(n * 0.99), n - 1)],
        }

    async def get_failure_rate(self, hours: int = 24) -> float | None:
        """Calculate failure rate as (FAILED + DEAD_LETTERED) / total terminal tasks."""
        since = datetime.now(UTC) - timedelta(hours=hours)
        total = await self._repo.count_total_since(since)
        if total == 0:
            return None
        failed = await self._repo.count_failed_since(since)
        return round(failed / total * 100, 2)

    async def get_dlq_size(self) -> int:
        """Count DEAD_LETTERED tasks."""
        return await self._repo.count_dead_lettered()

    async def get_all_metrics(self) -> dict:
        """Aggregate all queue health metrics into a single dict."""
        queue_depths = await self.get_queue_depths()
        percentiles = await self.get_processing_time_percentiles()
        failure_rate = await self.get_failure_rate()
        dlq_size = await self.get_dlq_size()

        return {
            "queue_depths": queue_depths,
            "processing_time_percentiles": percentiles,
            "failure_rate_pct": failure_rate,
            "dlq_size": dlq_size,
        }
