"""Tests for QueueMetrics queue health data collection."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.tasks.metrics import QueueMetrics


def _make_repo():
    repo = AsyncMock()
    repo.count_dead_lettered = AsyncMock(return_value=5)
    repo.count_completed_since = AsyncMock(return_value=100)
    repo.find_completed_since = AsyncMock(return_value=[])
    repo.count_failed_since = AsyncMock(return_value=3)
    repo.count_total_since = AsyncMock(return_value=100)
    return repo


def _make_record(started_at, completed_at):
    record = MagicMock()
    record.started_at = started_at
    record.completed_at = completed_at
    return record


class TestGetQueueDepths:
    async def test_returns_queue_depths_from_redis(self):
        """get_queue_depths returns interactive and batch depths."""
        repo = _make_repo()
        metrics = QueueMetrics(repo=repo)

        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(side_effect=[10, 25])

        with patch("src.core.redis_client.get_redis", return_value=mock_redis):
            result = await metrics.get_queue_depths()

        assert result == {"interactive": 10, "batch": 25}

    async def test_returns_none_on_redis_failure(self):
        """get_queue_depths returns None depths when Redis is unavailable."""
        repo = _make_repo()
        metrics = QueueMetrics(repo=repo)

        with patch("src.core.redis_client.get_redis", side_effect=RuntimeError("not init")):
            result = await metrics.get_queue_depths()

        assert result == {"interactive": None, "batch": None}


class TestGetProcessingTimePercentiles:
    async def test_calculates_percentiles_correctly(self):
        """get_processing_time_percentiles returns p50/p95/p99."""
        repo = _make_repo()
        now = datetime.now(UTC)

        # Create 100 records with varying durations (100ms to 10000ms)
        records = [
            _make_record(
                started_at=now - timedelta(milliseconds=i * 100 + 100),
                completed_at=now - timedelta(milliseconds=i * 100 + 100) + timedelta(milliseconds=i * 100 + 100),
            )
            for i in range(100)
        ]
        repo.find_completed_since = AsyncMock(return_value=records)

        metrics = QueueMetrics(repo=repo)
        result = await metrics.get_processing_time_percentiles()

        assert result["p50"] is not None
        assert result["p95"] is not None
        assert result["p99"] is not None
        # p95 should be greater than p50
        assert result["p95"] >= result["p50"]

    async def test_returns_none_when_no_data(self):
        """get_processing_time_percentiles returns None when no completed tasks."""
        repo = _make_repo()
        repo.find_completed_since = AsyncMock(return_value=[])

        metrics = QueueMetrics(repo=repo)
        result = await metrics.get_processing_time_percentiles()

        assert result == {"p50": None, "p95": None, "p99": None}

    async def test_handles_records_with_missing_timestamps(self):
        """Records without started_at or completed_at are skipped."""
        repo = _make_repo()
        now = datetime.now(UTC)

        records = [
            _make_record(started_at=None, completed_at=now),
            _make_record(started_at=now - timedelta(seconds=1), completed_at=None),
            _make_record(started_at=now - timedelta(seconds=2), completed_at=now),
        ]
        repo.find_completed_since = AsyncMock(return_value=records)

        metrics = QueueMetrics(repo=repo)
        result = await metrics.get_processing_time_percentiles()

        # Only 1 valid record
        assert result["p50"] is not None


class TestGetFailureRate:
    async def test_calculates_failure_rate(self):
        """get_failure_rate returns correct percentage."""
        repo = _make_repo()
        repo.count_failed_since = AsyncMock(return_value=5)
        repo.count_total_since = AsyncMock(return_value=100)

        metrics = QueueMetrics(repo=repo)
        result = await metrics.get_failure_rate()

        assert result == 5.0

    async def test_returns_none_when_no_tasks(self):
        """get_failure_rate returns None when no terminal tasks exist."""
        repo = _make_repo()
        repo.count_total_since = AsyncMock(return_value=0)

        metrics = QueueMetrics(repo=repo)
        result = await metrics.get_failure_rate()

        assert result is None

    async def test_returns_zero_when_no_failures(self):
        """get_failure_rate returns 0.0 when all tasks succeed."""
        repo = _make_repo()
        repo.count_failed_since = AsyncMock(return_value=0)
        repo.count_total_since = AsyncMock(return_value=50)

        metrics = QueueMetrics(repo=repo)
        result = await metrics.get_failure_rate()

        assert result == 0.0


class TestGetDlqSize:
    async def test_returns_count_from_repo(self):
        """get_dlq_size delegates to repo.count_dead_lettered."""
        repo = _make_repo()
        repo.count_dead_lettered = AsyncMock(return_value=42)

        metrics = QueueMetrics(repo=repo)
        result = await metrics.get_dlq_size()

        assert result == 42


class TestGetAllMetrics:
    async def test_aggregates_all_metrics(self):
        """get_all_metrics returns combined dict from all metric sources."""
        repo = _make_repo()
        repo.count_dead_lettered = AsyncMock(return_value=3)
        repo.count_total_since = AsyncMock(return_value=0)

        metrics = QueueMetrics(repo=repo)

        with patch.object(metrics, "get_queue_depths", return_value={"interactive": 5, "batch": 10}):
            result = await metrics.get_all_metrics()

        assert "queue_depths" in result
        assert "processing_time_percentiles" in result
        assert "failure_rate_pct" in result
        assert "dlq_size" in result
        assert result["dlq_size"] == 3
