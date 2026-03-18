"""Tests for DataSourceHealthRepository — health check recording and queries."""

from unittest.mock import AsyncMock, MagicMock, patch

from src.repositories.data_source_health_repository import DataSourceHealthRepository


def _make_health(**overrides):
    defaults = {
        "source_name": "indeed_api",
        "status": "healthy",
        "consecutive_failures": 0,
        "avg_response_ms": 50.0,
        "last_error": "",
        "disabled": False,
    }
    defaults.update(overrides)
    health = MagicMock()
    for k, v in defaults.items():
        setattr(health, k, v)
    health.id = "health_id"
    return health


class TestRecordCheckNewSource:
    async def test_creates_record_on_success(self):
        repo = DataSourceHealthRepository()
        created = _make_health()
        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None),
            patch.object(repo, "create", new_callable=AsyncMock, return_value=created),
        ):
            result = await repo.record_check("indeed_api", success=True, response_ms=42.0)
        assert result == created

    async def test_creates_record_on_failure(self):
        repo = DataSourceHealthRepository()
        created = _make_health(status="degraded", consecutive_failures=1)
        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None),
            patch.object(repo, "create", new_callable=AsyncMock, return_value=created),
        ):
            result = await repo.record_check(
                "indeed_api", success=False, error="timeout"
            )
        assert result == created


class TestRecordCheckExistingSource:
    async def test_success_resets_failures(self):
        repo = DataSourceHealthRepository()
        existing = _make_health(consecutive_failures=2, status="degraded")
        updated = _make_health(consecutive_failures=0, status="healthy")
        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=existing),
            patch.object(repo, "update", new_callable=AsyncMock, return_value=updated) as mock_update,
        ):
            result = await repo.record_check("indeed_api", success=True, response_ms=30.0)
        assert result == updated
        call_args = mock_update.call_args[0][1]
        assert call_args["consecutive_failures"] == 0
        assert call_args["status"] == "healthy"

    async def test_failure_increments_count(self):
        repo = DataSourceHealthRepository()
        existing = _make_health(consecutive_failures=1, status="degraded")
        updated = _make_health(consecutive_failures=2, status="degraded")
        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=existing),
            patch.object(repo, "update", new_callable=AsyncMock, return_value=updated) as mock_update,
        ):
            await repo.record_check("indeed_api", success=False, error="err")
        call_args = mock_update.call_args[0][1]
        assert call_args["consecutive_failures"] == 2
        assert call_args["status"] == "degraded"

    async def test_third_failure_marks_down(self):
        repo = DataSourceHealthRepository()
        existing = _make_health(consecutive_failures=2, status="degraded")
        updated = _make_health(consecutive_failures=3, status="down")
        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=existing),
            patch.object(repo, "update", new_callable=AsyncMock, return_value=updated) as mock_update,
        ):
            await repo.record_check("indeed_api", success=False, error="err")
        call_args = mock_update.call_args[0][1]
        assert call_args["consecutive_failures"] == 3
        assert call_args["status"] == "down"

    async def test_recovery_from_down(self):
        repo = DataSourceHealthRepository()
        existing = _make_health(consecutive_failures=5, status="down")
        updated = _make_health(consecutive_failures=0, status="healthy")
        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=existing),
            patch.object(repo, "update", new_callable=AsyncMock, return_value=updated) as mock_update,
        ):
            await repo.record_check("indeed_api", success=True, response_ms=25.0)
        call_args = mock_update.call_args[0][1]
        assert call_args["status"] == "healthy"
        assert call_args["consecutive_failures"] == 0


class TestGetAllSources:
    async def test_returns_all(self):
        repo = DataSourceHealthRepository()
        sources = [_make_health(), _make_health(source_name="naukri")]
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=sources):
            result = await repo.get_all_sources()
        assert len(result) == 2


class TestGetHealthySources:
    async def test_excludes_down_and_disabled(self):
        repo = DataSourceHealthRepository()
        sources = [_make_health()]
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=sources) as mock_find:
            result = await repo.get_healthy_sources()
        assert len(result) == 1
        mock_find.assert_awaited_once_with(
            filters={"status": {"$ne": "down"}, "disabled": False}
        )


class TestSetDisabled:
    async def test_disables_source(self):
        repo = DataSourceHealthRepository()
        existing = _make_health()
        updated = _make_health(disabled=True)
        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=existing),
            patch.object(repo, "update", new_callable=AsyncMock, return_value=updated),
        ):
            result = await repo.set_disabled("indeed_api", True)
        assert result == updated

    async def test_returns_none_if_not_found(self):
        repo = DataSourceHealthRepository()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None):
            result = await repo.set_disabled("unknown", True)
        assert result is None
