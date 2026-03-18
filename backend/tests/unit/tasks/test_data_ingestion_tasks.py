"""Tests for data ingestion Celery tasks — external data refresh."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestRefreshAll:
    async def test_calls_service(self):
        mock_service = MagicMock()
        mock_service.refresh_all_companies = AsyncMock(
            return_value={"refreshed": 5, "errors": 0}
        )
        mock_service.ingest_market_signals = AsyncMock(
            return_value={"signals_created": 3}
        )

        with (
            patch(
                "src.repositories.company_repository.CompanyRepository",
                return_value=MagicMock(),
            ),
            patch(
                "src.repositories.data_source_health_repository.DataSourceHealthRepository",
                return_value=MagicMock(),
            ),
            patch(
                "src.services.external_data_service.ExternalDataService",
                return_value=mock_service,
            ),
        ):
            from src.tasks.data_ingestion_tasks import _refresh_all

            result = await _refresh_all()

        assert result["companies_refreshed"] == 5
        assert result["company_errors"] == 0
        assert result["signals_created"] == 3


class TestCeleryTaskRegistration:
    def test_task_registered(self):
        from src.tasks.data_ingestion_tasks import refresh_external_data

        assert refresh_external_data.name == "tasks.batch.refresh_external_data"

    def test_beat_schedule(self):
        from src.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "refresh-external-data" in schedule
        assert schedule["refresh-external-data"]["schedule"] == 21600.0
