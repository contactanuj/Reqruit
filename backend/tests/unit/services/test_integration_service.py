"""Tests for IntegrationService OAuth lifecycle."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from src.core.exceptions import BusinessValidationError, ConflictError, NotFoundError
from src.db.documents.integration_connection import (
    IntegrationConnection,
    IntegrationProvider,
    IntegrationStatus,
)
from src.integrations.gmail_client import OAuthTokenResponse
from src.services.integration_service import IntegrationService

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
CONN_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
SIGNING_KEY = os.urandom(32)


def _service(repo=None, gmail_client=None):
    return IntegrationService(
        repo=repo or MagicMock(),
        gmail_client=gmail_client or MagicMock(),
        encryption_key=SIGNING_KEY,
    )


class TestInitiateConnection:
    def test_returns_redirect_url_and_state(self):
        gmail = MagicMock()
        gmail.generate_auth_url.return_value = "https://accounts.google.com/auth?..."
        svc = _service(gmail_client=gmail)

        result = svc.initiate_connection(USER_ID, IntegrationProvider.GMAIL)

        assert "redirect_url" in result
        assert "state" in result
        assert result["redirect_url"] == "https://accounts.google.com/auth?..."
        gmail.generate_auth_url.assert_called_once()

    def test_unsupported_provider_raises(self):
        svc = _service()
        with pytest.raises(BusinessValidationError, match="not supported"):
            svc.initiate_connection(USER_ID, IntegrationProvider.OUTLOOK)


class TestCompleteConnection:
    async def test_creates_connection_on_success(self):
        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=None)
        repo.create_connection = AsyncMock()

        gmail = MagicMock()
        gmail.exchange_code = AsyncMock(
            return_value=OAuthTokenResponse(
                access_token="ya29.access",
                refresh_token="1//refresh",
                expires_in=3600,
                scope="gmail.readonly gmail.metadata",
                token_type="Bearer",
            )
        )

        svc = _service(repo=repo, gmail_client=gmail)
        state = svc._generate_state(USER_ID)

        await svc.complete_connection(USER_ID, IntegrationProvider.GMAIL, "code", state)

        repo.create_connection.assert_awaited_once()
        call_kwargs = repo.create_connection.call_args[1]
        assert call_kwargs["user_id"] == USER_ID
        assert call_kwargs["provider"] == IntegrationProvider.GMAIL
        assert call_kwargs["oauth_token"] == "ya29.access"

    async def test_invalid_state_raises(self):
        svc = _service()
        with pytest.raises(BusinessValidationError, match="Invalid or expired"):
            await svc.complete_connection(
                USER_ID, IntegrationProvider.GMAIL, "code", "bad-state"
            )

    async def test_already_connected_raises_conflict(self):
        existing = MagicMock(spec=IntegrationConnection)
        existing.status = IntegrationStatus.CONNECTED

        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=existing)

        svc = _service(repo=repo)
        state = svc._generate_state(USER_ID)

        with pytest.raises(ConflictError, match="already connected"):
            await svc.complete_connection(
                USER_ID, IntegrationProvider.GMAIL, "code", state
            )

    async def test_reconnect_updates_existing(self):
        existing = MagicMock(spec=IntegrationConnection)
        existing.id = CONN_ID
        existing.status = IntegrationStatus.DISCONNECTED

        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=existing)
        repo.update_tokens = AsyncMock(return_value=existing)

        gmail = MagicMock()
        gmail.exchange_code = AsyncMock(
            return_value=OAuthTokenResponse(
                access_token="new_token",
                refresh_token="new_refresh",
                expires_in=3600,
                scope="gmail.readonly",
                token_type="Bearer",
            )
        )

        svc = _service(repo=repo, gmail_client=gmail)
        state = svc._generate_state(USER_ID)

        await svc.complete_connection(USER_ID, IntegrationProvider.GMAIL, "code", state)

        repo.update_tokens.assert_awaited_once()
        args = repo.update_tokens.call_args[0]
        assert args[0] == CONN_ID
        assert args[1] == "new_token"
        assert args[2] == "new_refresh"
        # expires_at should be ~1 hour from now
        assert abs((args[3] - datetime.now(UTC)).total_seconds() - 3600) < 10


class TestDisconnect:
    async def test_disconnects_and_revokes(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.id = CONN_ID
        conn.status = IntegrationStatus.CONNECTED

        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=conn)
        repo.decrypt_tokens = MagicMock(return_value=("oauth_tok", "refresh_tok"))
        repo.disconnect = AsyncMock()

        gmail = MagicMock()
        gmail.revoke_token = AsyncMock(return_value=True)

        svc = _service(repo=repo, gmail_client=gmail)
        await svc.disconnect(USER_ID, IntegrationProvider.GMAIL, purge=True)

        gmail.revoke_token.assert_awaited_once_with("oauth_tok")
        repo.disconnect.assert_awaited_once_with(CONN_ID, purge_tokens=True)

    async def test_not_found_raises(self):
        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=None)

        svc = _service(repo=repo)
        with pytest.raises(NotFoundError):
            await svc.disconnect(USER_ID, IntegrationProvider.GMAIL)

    async def test_revoke_failure_does_not_block_disconnect(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.id = CONN_ID
        conn.status = IntegrationStatus.CONNECTED

        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=conn)
        repo.decrypt_tokens = MagicMock(side_effect=Exception("decrypt fail"))
        repo.disconnect = AsyncMock()

        svc = _service(repo=repo)
        # Should not raise — revoke failure is best-effort
        await svc.disconnect(USER_ID, IntegrationProvider.GMAIL)
        repo.disconnect.assert_awaited_once()

    async def test_purge_false_still_purges_tokens(self):
        """Tokens are always purged on disconnect regardless of purge flag."""
        conn = MagicMock(spec=IntegrationConnection)
        conn.id = CONN_ID
        conn.status = IntegrationStatus.DISCONNECTED

        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=conn)
        repo.disconnect = AsyncMock()

        svc = _service(repo=repo)
        await svc.disconnect(USER_ID, IntegrationProvider.GMAIL, purge=False)
        repo.disconnect.assert_awaited_once_with(CONN_ID, purge_tokens=True)


class TestGetAllStatuses:
    async def test_returns_sanitized_list(self):
        conn = MagicMock()
        conn.provider = IntegrationProvider.GMAIL
        conn.status = IntegrationStatus.CONNECTED
        conn.connected_at = datetime(2026, 3, 16, tzinfo=UTC)
        conn.last_synced_at = None
        conn.scopes = ["gmail.readonly"]

        repo = MagicMock()
        repo.get_all_by_user = AsyncMock(return_value=[conn])

        svc = _service(repo=repo)
        result = await svc.get_all_statuses(USER_ID)

        assert len(result) == 1
        assert result[0].provider == "gmail"
        assert result[0].status == "connected"
        # Ensure no token fields in the response model
        assert not hasattr(result[0], "oauth_token")
        assert not hasattr(result[0], "refresh_token")

    async def test_empty_for_no_connections(self):
        repo = MagicMock()
        repo.get_all_by_user = AsyncMock(return_value=[])

        svc = _service(repo=repo)
        result = await svc.get_all_statuses(USER_ID)
        assert result == []


class TestCsrfState:
    def test_generated_state_validates(self):
        svc = _service()
        state = svc._generate_state(USER_ID)
        assert svc.validate_csrf_state(state, USER_ID) is True

    def test_state_for_wrong_user_fails(self):
        svc = _service()
        state = svc._generate_state(USER_ID)
        other_user = PydanticObjectId("cccccccccccccccccccccccc")
        assert svc.validate_csrf_state(state, other_user) is False

    def test_tampered_state_fails(self):
        svc = _service()
        state = svc._generate_state(USER_ID)
        tampered = state[:-5] + "xxxxx"
        assert svc.validate_csrf_state(tampered, USER_ID) is False

    def test_invalid_format_fails(self):
        svc = _service()
        assert svc.validate_csrf_state("not-a-valid-state", USER_ID) is False
        assert svc.validate_csrf_state("", USER_ID) is False


class TestDisconnectSignalHandling:
    async def test_purge_true_deletes_signals(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.id = CONN_ID
        conn.status = IntegrationStatus.DISCONNECTED

        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=conn)
        repo.disconnect = AsyncMock()

        signal_repo = MagicMock()
        signal_repo.delete_by_user_and_provider = AsyncMock(return_value=5)

        svc = IntegrationService(
            repo=repo, gmail_client=MagicMock(), encryption_key=SIGNING_KEY,
            signal_repo=signal_repo,
        )
        await svc.disconnect(USER_ID, IntegrationProvider.GMAIL, purge=True)

        signal_repo.delete_by_user_and_provider.assert_awaited_once_with(
            USER_ID, IntegrationProvider.GMAIL
        )

    async def test_purge_false_reattributes_signals(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.id = CONN_ID
        conn.status = IntegrationStatus.DISCONNECTED

        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=conn)
        repo.disconnect = AsyncMock()

        signal_repo = MagicMock()
        signal_repo.update_source_to_user_reported = AsyncMock(return_value=3)

        svc = IntegrationService(
            repo=repo, gmail_client=MagicMock(), encryption_key=SIGNING_KEY,
            signal_repo=signal_repo,
        )
        await svc.disconnect(USER_ID, IntegrationProvider.GMAIL, purge=False)

        signal_repo.update_source_to_user_reported.assert_awaited_once_with(
            USER_ID, IntegrationProvider.GMAIL
        )

    async def test_no_signal_repo_skips_signal_handling(self):
        conn = MagicMock(spec=IntegrationConnection)
        conn.id = CONN_ID
        conn.status = IntegrationStatus.DISCONNECTED

        repo = MagicMock()
        repo.get_by_user_provider = AsyncMock(return_value=conn)
        repo.disconnect = AsyncMock()

        svc = _service(repo=repo)  # no signal_repo
        await svc.disconnect(USER_ID, IntegrationProvider.GMAIL, purge=True)
        repo.disconnect.assert_awaited_once()


class TestLinkSignalToApplication:
    async def test_links_signal(self):
        signal_repo = MagicMock()
        signal_repo.get_by_id = AsyncMock(return_value=MagicMock())
        signal_repo.update = AsyncMock()

        svc = IntegrationService(
            repo=MagicMock(), gmail_client=MagicMock(), encryption_key=SIGNING_KEY,
            signal_repo=signal_repo,
        )
        signal_id = PydanticObjectId("dddddddddddddddddddddddd")
        app_id = PydanticObjectId("eeeeeeeeeeeeeeeeeeeeeeee")
        await svc.link_signal_to_application(signal_id, app_id)

        signal_repo.update.assert_awaited_once_with(
            signal_id, {"application_id": app_id}
        )

    async def test_signal_not_found_raises(self):
        signal_repo = MagicMock()
        signal_repo.get_by_id = AsyncMock(return_value=None)

        svc = IntegrationService(
            repo=MagicMock(), gmail_client=MagicMock(), encryption_key=SIGNING_KEY,
            signal_repo=signal_repo,
        )
        with pytest.raises(NotFoundError):
            await svc.link_signal_to_application(
                PydanticObjectId("dddddddddddddddddddddddd"),
                PydanticObjectId("eeeeeeeeeeeeeeeeeeeeeeee"),
            )

    async def test_no_signal_repo_raises(self):
        svc = _service()
        with pytest.raises(BusinessValidationError, match="not configured"):
            await svc.link_signal_to_application(
                PydanticObjectId("dddddddddddddddddddddddd"),
                PydanticObjectId("eeeeeeeeeeeeeeeeeeeeeeee"),
            )


class TestGetSignalsForUser:
    async def test_returns_signals(self):
        signal_repo = MagicMock()
        signal_repo.get_by_user = AsyncMock(return_value=[MagicMock(), MagicMock()])

        svc = IntegrationService(
            repo=MagicMock(), gmail_client=MagicMock(), encryption_key=SIGNING_KEY,
            signal_repo=signal_repo,
        )
        result = await svc.get_signals_for_user(USER_ID)
        assert len(result) == 2

    async def test_returns_empty_without_signal_repo(self):
        svc = _service()
        result = await svc.get_signals_for_user(USER_ID)
        assert result == []
