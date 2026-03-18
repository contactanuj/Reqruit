"""Tests for email integration Celery tasks."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.tasks.integration_tasks import (
    _run_initial_sync,
    _sync_all_connections,
    _sync_single_connection,
)


class TestSyncAllConnections:
    async def test_processes_all_connected_integrations(self):
        conn1 = MagicMock()
        conn1.id = "conn1"
        conn2 = MagicMock()
        conn2.id = "conn2"

        mock_repo = MagicMock()
        mock_repo.find_many = AsyncMock(return_value=[conn1, conn2])

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.tasks.integration_tasks._sync_single_connection",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_sync,
        ):
            result = await _sync_all_connections()

        assert result["connections"] == 2
        assert mock_sync.await_count == 2

    async def test_handles_connection_failure_gracefully(self):
        conn = MagicMock()
        conn.id = "failing_conn"

        mock_repo = MagicMock()
        mock_repo.find_many = AsyncMock(return_value=[conn])

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.tasks.integration_tasks._sync_single_connection",
                new_callable=AsyncMock,
                side_effect=Exception("sync error"),
            ),
        ):
            result = await _sync_all_connections()

        assert result["connections"] == 1
        assert result["signals"] == 0

    async def test_empty_connections_list(self):
        mock_repo = MagicMock()
        mock_repo.find_many = AsyncMock(return_value=[])

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
        ):
            result = await _sync_all_connections()

        assert result["connections"] == 0
        assert result["signals"] == 0


class TestRunInitialSync:
    async def test_runs_sync_for_connection(self):
        conn = MagicMock()
        conn.id = "abc123"

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=conn)

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.tasks.integration_tasks._sync_single_connection",
                new_callable=AsyncMock,
                return_value=3,
            ) as mock_sync,
        ):
            result = await _run_initial_sync("aaaaaaaaaaaaaaaaaaaaaaaa")

        assert result["signals"] == 3
        mock_sync.assert_awaited_once_with(mock_repo, conn, initial=True)

    async def test_not_found_returns_zero(self):
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
        ):
            result = await _run_initial_sync("aaaaaaaaaaaaaaaaaaaaaaaa")

        assert result["signals"] == 0


class TestSyncSingleConnection:
    async def test_updates_sync_cursor(self):
        conn = MagicMock()
        conn.id = "conn_id"
        conn.sync_cursor = "prev_cursor"
        conn.last_synced_at = datetime.now(UTC) - timedelta(hours=1)

        mock_repo = MagicMock()
        mock_repo.decrypt_tokens = MagicMock(return_value=("token", "refresh"))
        mock_repo.update_sync_cursor = AsyncMock()

        with (
            patch("src.core.config.get_settings") as mock_settings,
            patch("src.integrations.gmail_client.GmailClient"),
            patch("src.integrations.email_parser.EmailParser"),
            patch("src.repositories.email_signal_repository.EmailSignalRepository"),
        ):
            mock_settings.return_value.oauth.gmail_client_id = "id"
            mock_settings.return_value.oauth.gmail_client_secret = "secret"
            mock_settings.return_value.oauth.gmail_redirect_uri = "uri"

            result = await _sync_single_connection(mock_repo, conn)

        assert result == 0
        mock_repo.update_sync_cursor.assert_awaited_once()

    async def test_token_decrypt_failure_marks_expired(self):
        conn = MagicMock()
        conn.id = "conn_id"

        mock_repo = MagicMock()
        mock_repo.decrypt_tokens = MagicMock(side_effect=Exception("decrypt fail"))
        mock_repo.update = AsyncMock()

        result = await _sync_single_connection(mock_repo, conn)

        assert result == 0
        mock_repo.update.assert_awaited_once()

    async def test_initial_sync_uses_lookback_period(self):
        conn = MagicMock()
        conn.id = "conn_id"
        conn.sync_cursor = None
        conn.last_synced_at = None

        mock_repo = MagicMock()
        mock_repo.decrypt_tokens = MagicMock(return_value=("token", "refresh"))
        mock_repo.update_sync_cursor = AsyncMock()

        with (
            patch("src.core.config.get_settings") as mock_settings,
            patch("src.integrations.gmail_client.GmailClient"),
            patch("src.integrations.email_parser.EmailParser"),
            patch("src.repositories.email_signal_repository.EmailSignalRepository"),
        ):
            mock_settings.return_value.oauth.gmail_client_id = "id"
            mock_settings.return_value.oauth.gmail_client_secret = "secret"
            mock_settings.return_value.oauth.gmail_redirect_uri = "uri"

            result = await _sync_single_connection(mock_repo, conn, initial=True)

        assert result == 0
        mock_repo.update_sync_cursor.assert_awaited_once()


class TestCeleryTaskRegistration:
    def test_sync_task_registered(self):
        from src.tasks.integration_tasks import sync_email_integrations

        assert sync_email_integrations.name == "tasks.batch.sync_email_integrations"

    def test_initial_sync_task_registered(self):
        from src.tasks.integration_tasks import initial_email_sync

        assert initial_email_sync.name == "tasks.batch.initial_email_sync"

    def test_beat_schedule_includes_sync(self):
        from src.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "sync-email-integrations" in schedule
        assert schedule["sync-email-integrations"]["schedule"] == 1800.0

    def test_check_nudges_task_registered(self):
        from src.tasks.integration_tasks import check_nudges

        assert check_nudges.name == "tasks.batch.check_nudges"

    def test_beat_schedule_includes_nudges(self):
        from src.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "check-nudges" in schedule
        assert schedule["check-nudges"]["schedule"] == 21600.0


class TestCheckAllNudges:
    async def test_processes_active_applications(self):
        app1 = MagicMock()
        app1.id = "app1"
        app1.user_id = "user1"
        app1.status = "applied"
        app1.company_name = "Acme"
        app1.role = "SWE"
        app1.updated_at = datetime.now(UTC) - timedelta(days=10)
        app1.created_at = datetime.now(UTC) - timedelta(days=10)
        app1.last_interview_date = None

        mock_app_repo = MagicMock()
        mock_app_repo.find_many = AsyncMock(return_value=[app1])

        mock_engine = MagicMock()
        mock_engine.evaluate_application = AsyncMock(return_value=[MagicMock()])

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.application_repository.ApplicationRepository",
                return_value=mock_app_repo,
            ),
            patch("src.repositories.nudge_repository.NudgeRepository"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
            ),
            patch(
                "src.services.nudge_engine.NudgeEngine",
                return_value=mock_engine,
            ),
        ):
            from src.tasks.integration_tasks import _check_all_nudges

            result = await _check_all_nudges()

        assert result["applications"] == 1
        assert result["nudges"] == 1

    async def test_handles_application_failure(self):
        app1 = MagicMock()
        app1.id = "app1"
        app1.user_id = "user1"
        app1.status = "applied"
        app1.company_name = "Acme"
        app1.role = "SWE"
        app1.updated_at = datetime.now(UTC) - timedelta(days=10)
        app1.created_at = datetime.now(UTC) - timedelta(days=10)
        app1.last_interview_date = None

        mock_app_repo = MagicMock()
        mock_app_repo.find_many = AsyncMock(return_value=[app1])

        mock_engine = MagicMock()
        mock_engine.evaluate_application = AsyncMock(side_effect=Exception("fail"))

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.application_repository.ApplicationRepository",
                return_value=mock_app_repo,
            ),
            patch("src.repositories.nudge_repository.NudgeRepository"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
            ),
            patch(
                "src.services.nudge_engine.NudgeEngine",
                return_value=mock_engine,
            ),
        ):
            from src.tasks.integration_tasks import _check_all_nudges

            result = await _check_all_nudges()

        assert result["applications"] == 1
        assert result["nudges"] == 0

    async def test_empty_applications(self):
        mock_app_repo = MagicMock()
        mock_app_repo.find_many = AsyncMock(return_value=[])

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.application_repository.ApplicationRepository",
                return_value=mock_app_repo,
            ),
            patch("src.repositories.nudge_repository.NudgeRepository"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
            ),
            patch("src.services.nudge_engine.NudgeEngine"),
        ):
            from src.tasks.integration_tasks import _check_all_nudges

            result = await _check_all_nudges()

        assert result["applications"] == 0
        assert result["nudges"] == 0
