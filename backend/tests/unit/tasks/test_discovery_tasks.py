"""Tests for discovery Celery tasks — source health checks."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestCheckAllSources:
    async def test_checks_all_registered_sources(self):
        mock_repo = MagicMock()
        mock_repo.record_check = AsyncMock()

        mock_client = MagicMock()
        mock_client.health_check = AsyncMock(return_value=True)

        mock_registry = {
            "indeed_api": MagicMock(return_value=mock_client),
            "naukri_scraper": MagicMock(return_value=mock_client),
        }

        with (
            patch(
                "src.repositories.data_source_health_repository.DataSourceHealthRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.integrations.job_source_clients.JOB_SOURCE_REGISTRY",
                mock_registry,
            ),
        ):
            from src.tasks.discovery_tasks import _check_all_sources

            result = await _check_all_sources()

        assert result["indeed_api"] == "healthy"
        assert result["naukri_scraper"] == "healthy"
        assert mock_repo.record_check.await_count == 2

    async def test_handles_unhealthy_source(self):
        mock_repo = MagicMock()
        mock_repo.record_check = AsyncMock()

        mock_client = MagicMock()
        mock_client.health_check = AsyncMock(return_value=False)

        mock_registry = {
            "indeed_api": MagicMock(return_value=mock_client),
        }

        with (
            patch(
                "src.repositories.data_source_health_repository.DataSourceHealthRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.integrations.job_source_clients.JOB_SOURCE_REGISTRY",
                mock_registry,
            ),
        ):
            from src.tasks.discovery_tasks import _check_all_sources

            result = await _check_all_sources()

        assert result["indeed_api"] == "degraded"

    async def test_handles_exception_during_check(self):
        mock_repo = MagicMock()
        mock_repo.record_check = AsyncMock()

        mock_client = MagicMock()
        mock_client.health_check = AsyncMock(side_effect=Exception("connection error"))

        mock_registry = {
            "indeed_api": MagicMock(return_value=mock_client),
        }

        with (
            patch(
                "src.repositories.data_source_health_repository.DataSourceHealthRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.integrations.job_source_clients.JOB_SOURCE_REGISTRY",
                mock_registry,
            ),
        ):
            from src.tasks.discovery_tasks import _check_all_sources

            result = await _check_all_sources()

        assert result["indeed_api"] == "error"
        mock_repo.record_check.assert_awaited_once()

    async def test_empty_registry(self):
        mock_repo = MagicMock()
        mock_repo.record_check = AsyncMock()

        with (
            patch(
                "src.repositories.data_source_health_repository.DataSourceHealthRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.integrations.job_source_clients.JOB_SOURCE_REGISTRY",
                {},
            ),
        ):
            from src.tasks.discovery_tasks import _check_all_sources

            result = await _check_all_sources()

        assert result == {}


class TestCeleryTaskRegistration:
    def test_health_check_task_registered(self):
        from src.tasks.discovery_tasks import check_source_health

        assert check_source_health.name == "tasks.batch.check_source_health"

    def test_beat_schedule_includes_health_check(self):
        from src.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "check-source-health" in schedule
        assert schedule["check-source-health"]["schedule"] == 300.0
