"""Tests for OAuth token refresh Celery task."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.db.documents.integration_connection import IntegrationProvider
from src.tasks.integration_tasks import _refresh_all_expiring_tokens


class TestRefreshAllExpiringTokens:
    async def test_refreshes_gmail_token(self):
        conn = MagicMock()
        conn.id = "conn_gmail"
        conn.provider = IntegrationProvider.GMAIL

        mock_repo = MagicMock()
        mock_repo.get_connections_needing_refresh = AsyncMock(return_value=[conn])
        mock_repo.decrypt_tokens = MagicMock(
            return_value=("old_access", "old_refresh")
        )
        mock_repo.update_tokens = AsyncMock()

        mock_token_response = MagicMock()
        mock_token_response.access_token = "new_access"
        mock_token_response.refresh_token = None  # Google often omits this
        mock_token_response.expires_in = 3600

        mock_gmail_client = MagicMock()
        mock_gmail_client.refresh_access_token = AsyncMock(
            return_value=mock_token_response
        )

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch("src.core.config.get_settings") as mock_settings,
            patch(
                "src.integrations.gmail_client.GmailClient",
                return_value=mock_gmail_client,
            ),
        ):
            mock_settings.return_value.oauth.gmail_client_id = "id"
            mock_settings.return_value.oauth.gmail_client_secret = "secret"
            mock_settings.return_value.oauth.gmail_redirect_uri = "uri"

            result = await _refresh_all_expiring_tokens()

        assert result["refreshed"] == 1
        assert result["failed"] == 0
        mock_gmail_client.refresh_access_token.assert_awaited_once_with("old_refresh")
        mock_repo.update_tokens.assert_awaited_once()
        # When Google omits refresh_token, old one is preserved
        call_kwargs = mock_repo.update_tokens.call_args[1]
        assert call_kwargs["refresh_token"] == "old_refresh"
        assert call_kwargs["oauth_token"] == "new_access"

    async def test_refreshes_calendar_token(self):
        conn = MagicMock()
        conn.id = "conn_cal"
        conn.provider = IntegrationProvider.GOOGLE_CALENDAR

        mock_repo = MagicMock()
        mock_repo.get_connections_needing_refresh = AsyncMock(return_value=[conn])
        mock_repo.decrypt_tokens = MagicMock(
            return_value=("old_access", "old_refresh")
        )
        mock_repo.update_tokens = AsyncMock()

        mock_token_response = MagicMock()
        mock_token_response.access_token = "new_cal_access"
        mock_token_response.refresh_token = "new_cal_refresh"
        mock_token_response.expires_in = 3600

        mock_calendar_client = MagicMock()
        mock_calendar_client.refresh_access_token = AsyncMock(
            return_value=mock_token_response
        )

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch("src.core.config.get_settings") as mock_settings,
            patch(
                "src.integrations.google_calendar_client.GoogleCalendarClient",
                return_value=mock_calendar_client,
            ),
        ):
            mock_settings.return_value.oauth.google_calendar_client_id = "id"
            mock_settings.return_value.oauth.google_calendar_client_secret = "secret"
            mock_settings.return_value.oauth.google_calendar_redirect_uri = "uri"

            result = await _refresh_all_expiring_tokens()

        assert result["refreshed"] == 1
        assert result["failed"] == 0
        mock_calendar_client.refresh_access_token.assert_awaited_once_with(
            "old_refresh"
        )
        call_kwargs = mock_repo.update_tokens.call_args[1]
        assert call_kwargs["refresh_token"] == "new_cal_refresh"

    async def test_handles_refresh_failure_gracefully(self):
        conn1 = MagicMock()
        conn1.id = "conn_ok"
        conn1.provider = IntegrationProvider.GMAIL

        conn2 = MagicMock()
        conn2.id = "conn_fail"
        conn2.provider = IntegrationProvider.GMAIL

        mock_repo = MagicMock()
        mock_repo.get_connections_needing_refresh = AsyncMock(
            return_value=[conn1, conn2]
        )
        mock_repo.decrypt_tokens = MagicMock(
            return_value=("old_access", "old_refresh")
        )
        mock_repo.update_tokens = AsyncMock()

        mock_token_response = MagicMock()
        mock_token_response.access_token = "new_access"
        mock_token_response.refresh_token = None
        mock_token_response.expires_in = 3600

        mock_gmail_client = MagicMock()
        mock_gmail_client.refresh_access_token = AsyncMock(
            side_effect=[mock_token_response, Exception("Google API error")]
        )

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch("src.core.config.get_settings") as mock_settings,
            patch(
                "src.integrations.gmail_client.GmailClient",
                return_value=mock_gmail_client,
            ),
        ):
            mock_settings.return_value.oauth.gmail_client_id = "id"
            mock_settings.return_value.oauth.gmail_client_secret = "secret"
            mock_settings.return_value.oauth.gmail_redirect_uri = "uri"

            result = await _refresh_all_expiring_tokens()

        assert result["refreshed"] == 1
        assert result["failed"] == 1

    async def test_empty_connections_noop(self):
        mock_repo = MagicMock()
        mock_repo.get_connections_needing_refresh = AsyncMock(return_value=[])

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch("src.core.config.get_settings"),
        ):
            result = await _refresh_all_expiring_tokens()

        assert result["refreshed"] == 0
        assert result["failed"] == 0

    async def test_skips_unsupported_provider(self):
        conn = MagicMock()
        conn.id = "conn_outlook"
        conn.provider = IntegrationProvider.OUTLOOK

        mock_repo = MagicMock()
        mock_repo.get_connections_needing_refresh = AsyncMock(return_value=[conn])
        mock_repo.decrypt_tokens = MagicMock(
            return_value=("old_access", "old_refresh")
        )

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch("src.core.config.get_settings"),
        ):
            result = await _refresh_all_expiring_tokens()

        assert result["refreshed"] == 0
        assert result["failed"] == 0

    async def test_decrypt_failure_counted_as_failed(self):
        conn = MagicMock()
        conn.id = "conn_bad"
        conn.provider = IntegrationProvider.GMAIL

        mock_repo = MagicMock()
        mock_repo.get_connections_needing_refresh = AsyncMock(return_value=[conn])
        mock_repo.decrypt_tokens = MagicMock(side_effect=Exception("decrypt error"))

        with (
            patch("src.core.token_encryptor.get_token_encryptor"),
            patch(
                "src.repositories.integration_connection_repository.IntegrationConnectionRepository",
                return_value=mock_repo,
            ),
            patch("src.core.config.get_settings"),
        ):
            result = await _refresh_all_expiring_tokens()

        assert result["refreshed"] == 0
        assert result["failed"] == 1


class TestRefreshTaskRegistration:
    def test_task_registered(self):
        from src.tasks.integration_tasks import refresh_expiring_tokens

        assert refresh_expiring_tokens.name == "tasks.batch.refresh_expiring_tokens"

    def test_beat_schedule_includes_refresh(self):
        from src.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "refresh-expiring-tokens" in schedule
        assert schedule["refresh-expiring-tokens"]["schedule"] == 2700.0
