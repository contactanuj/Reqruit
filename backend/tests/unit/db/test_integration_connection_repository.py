"""Tests for IntegrationConnectionRepository with token encryption."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId

from src.core.token_encryptor import TokenEncryptor
from src.db.documents.integration_connection import (
    IntegrationConnection,
    IntegrationProvider,
    IntegrationStatus,
)
from src.repositories.integration_connection_repository import (
    IntegrationConnectionRepository,
)

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
CONN_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


def _encryptor() -> TokenEncryptor:
    return TokenEncryptor(os.urandom(32))


def _make_connection(
    encryptor: TokenEncryptor,
    oauth_token: str = "oauth_tok",
    refresh_token: str = "refresh_tok",
    status: IntegrationStatus = IntegrationStatus.CONNECTED,
) -> IntegrationConnection:
    conn = MagicMock(spec=IntegrationConnection)
    conn.id = CONN_ID
    conn.user_id = USER_ID
    conn.provider = IntegrationProvider.GMAIL
    conn.oauth_token_encrypted = encryptor.encrypt(oauth_token)
    conn.refresh_token_encrypted = encryptor.encrypt(refresh_token)
    conn.token_expires_at = datetime.now(UTC) + timedelta(hours=1)
    conn.scopes = ["https://mail.google.com/"]
    conn.connected_at = datetime.now(UTC)
    conn.status = status
    conn.last_synced_at = None
    conn.sync_cursor = None
    return conn


class TestCreateConnection:
    @patch.object(IntegrationConnection, "insert", new_callable=AsyncMock)
    async def test_create_encrypts_tokens(self, mock_insert):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)

        mock_insert.return_value = None  # insert() modifies in-place
        conn = await repo.create_connection(
            user_id=USER_ID,
            provider=IntegrationProvider.GMAIL,
            oauth_token="my_oauth_token",
            refresh_token="my_refresh_token",
            token_expires_at=datetime(2026, 4, 1, tzinfo=UTC),
            scopes=["https://mail.google.com/"],
        )

        # Tokens stored as encrypted bytes, not plaintext
        assert isinstance(conn.oauth_token_encrypted, bytes)
        assert isinstance(conn.refresh_token_encrypted, bytes)
        assert conn.oauth_token_encrypted != b"my_oauth_token"
        assert conn.refresh_token_encrypted != b"my_refresh_token"

        # Encrypted tokens can be decrypted back
        assert enc.decrypt(conn.oauth_token_encrypted) == "my_oauth_token"
        assert enc.decrypt(conn.refresh_token_encrypted) == "my_refresh_token"

    @patch.object(IntegrationConnection, "insert", new_callable=AsyncMock)
    async def test_create_sets_connected_status(self, mock_insert):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)

        conn = await repo.create_connection(
            user_id=USER_ID,
            provider=IntegrationProvider.GOOGLE_CALENDAR,
            oauth_token="tok",
            refresh_token="ref",
            token_expires_at=datetime(2026, 4, 1, tzinfo=UTC),
            scopes=[],
        )

        assert conn.status == IntegrationStatus.CONNECTED
        assert conn.connected_at is not None


class TestGetByUserProvider:
    @patch.object(IntegrationConnection, "find_one", new_callable=AsyncMock)
    async def test_returns_connection(self, mock_find_one):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)
        expected = _make_connection(enc)
        mock_find_one.return_value = expected

        result = await repo.get_by_user_provider(USER_ID, IntegrationProvider.GMAIL)

        assert result is expected
        mock_find_one.assert_awaited_once_with(
            {"user_id": USER_ID, "provider": "gmail"}
        )

    @patch.object(IntegrationConnection, "find_one", new_callable=AsyncMock)
    async def test_returns_none_for_missing(self, mock_find_one):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)
        mock_find_one.return_value = None

        result = await repo.get_by_user_provider(USER_ID, IntegrationProvider.OUTLOOK)

        assert result is None


class TestGetAllByUser:
    @patch.object(IntegrationConnection, "find")
    async def test_returns_all_providers(self, mock_find):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)
        connections = [_make_connection(enc), _make_connection(enc)]

        query = MagicMock()
        query.sort.return_value = query
        query.skip.return_value = query
        query.limit.return_value = query
        query.to_list = AsyncMock(return_value=connections)
        mock_find.return_value = query

        result = await repo.get_all_by_user(USER_ID)

        assert len(result) == 2


class TestGetConnectionsNeedingRefresh:
    @patch.object(IntegrationConnection, "find")
    async def test_returns_expiring_tokens(self, mock_find):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)
        conn = _make_connection(enc)

        query = MagicMock()
        query.sort.return_value = query
        query.skip.return_value = query
        query.limit.return_value = query
        query.to_list = AsyncMock(return_value=[conn])
        mock_find.return_value = query

        result = await repo.get_connections_needing_refresh(buffer_minutes=15)

        assert len(result) == 1
        # Verify the filter includes status=connected
        call_args = mock_find.call_args[0][0]
        assert call_args["status"] == "connected"
        assert "token_expires_at" in call_args


class TestUpdateTokens:
    @patch.object(IntegrationConnection, "get", new_callable=AsyncMock)
    async def test_reencrypts_with_new_values(self, mock_get):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)

        existing = MagicMock(spec=IntegrationConnection)
        existing.set = AsyncMock()
        mock_get.return_value = existing

        new_expires = datetime(2026, 5, 1, tzinfo=UTC)
        result = await repo.update_tokens(
            CONN_ID, "new_oauth", "new_refresh", new_expires
        )

        assert result is existing
        set_call = existing.set.call_args[0][0]
        # Tokens should be encrypted bytes, not plaintext
        assert isinstance(set_call["oauth_token_encrypted"], bytes)
        assert isinstance(set_call["refresh_token_encrypted"], bytes)
        assert enc.decrypt(set_call["oauth_token_encrypted"]) == "new_oauth"
        assert enc.decrypt(set_call["refresh_token_encrypted"]) == "new_refresh"
        assert set_call["token_expires_at"] == new_expires
        assert set_call["status"] == "connected"


class TestUpdateSyncCursor:
    @patch.object(IntegrationConnection, "get", new_callable=AsyncMock)
    async def test_persists_cursor_and_timestamp(self, mock_get):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)

        existing = MagicMock(spec=IntegrationConnection)
        existing.set = AsyncMock()
        mock_get.return_value = existing

        synced_at = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)
        result = await repo.update_sync_cursor(CONN_ID, "cursor_abc", synced_at)

        assert result is existing
        set_call = existing.set.call_args[0][0]
        assert set_call["sync_cursor"] == "cursor_abc"
        assert set_call["last_synced_at"] == synced_at


class TestDisconnect:
    @patch.object(IntegrationConnection, "get", new_callable=AsyncMock)
    async def test_purge_true_nulls_tokens(self, mock_get):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)

        existing = MagicMock(spec=IntegrationConnection)
        existing.set = AsyncMock()
        mock_get.return_value = existing

        result = await repo.disconnect(CONN_ID, purge_tokens=True)

        assert result is existing
        set_call = existing.set.call_args[0][0]
        assert set_call["status"] == "disconnected"
        assert set_call["oauth_token_encrypted"] == b""
        assert set_call["refresh_token_encrypted"] == b""

    @patch.object(IntegrationConnection, "get", new_callable=AsyncMock)
    async def test_purge_false_retains_tokens(self, mock_get):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)

        existing = MagicMock(spec=IntegrationConnection)
        existing.set = AsyncMock()
        mock_get.return_value = existing

        result = await repo.disconnect(CONN_ID, purge_tokens=False)

        assert result is existing
        set_call = existing.set.call_args[0][0]
        assert set_call["status"] == "disconnected"
        assert "oauth_token_encrypted" not in set_call
        assert "refresh_token_encrypted" not in set_call


class TestDecryptTokens:
    def test_returns_original_plaintext(self):
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)
        conn = _make_connection(enc, oauth_token="my_oauth", refresh_token="my_refresh")

        oauth, refresh = repo.decrypt_tokens(conn)

        assert oauth == "my_oauth"
        assert refresh == "my_refresh"


class TestStructlogMasking:
    @patch.object(IntegrationConnection, "insert", new_callable=AsyncMock)
    async def test_create_logs_no_raw_tokens(self, mock_insert, caplog):
        """Verify structlog output from create does not contain raw token values."""
        enc = _encryptor()
        repo = IntegrationConnectionRepository(enc)

        await repo.create_connection(
            user_id=USER_ID,
            provider=IntegrationProvider.GMAIL,
            oauth_token="super_secret_oauth_token_123",
            refresh_token="super_secret_refresh_token_456",
            token_expires_at=datetime(2026, 4, 1, tzinfo=UTC),
            scopes=[],
        )

        # structlog output should never contain raw tokens
        log_output = caplog.text
        assert "super_secret_oauth_token_123" not in log_output
        assert "super_secret_refresh_token_456" not in log_output


class TestEnumValues:
    def test_provider_values(self):
        assert IntegrationProvider.GMAIL == "gmail"
        assert IntegrationProvider.OUTLOOK == "outlook"
        assert IntegrationProvider.GOOGLE_CALENDAR == "google_calendar"
        assert IntegrationProvider.MICROSOFT_CALENDAR == "microsoft_calendar"

    def test_status_values(self):
        assert IntegrationStatus.CONNECTED == "connected"
        assert IntegrationStatus.DISCONNECTED == "disconnected"
        assert IntegrationStatus.TOKEN_EXPIRED == "token_expired"
        assert IntegrationStatus.REVOKED == "revoked"


class TestIntegrationConnectionModel:
    def test_document_fields(self):
        enc = _encryptor()
        conn = IntegrationConnection(
            user_id=USER_ID,
            provider=IntegrationProvider.GMAIL,
            oauth_token_encrypted=enc.encrypt("tok"),
            refresh_token_encrypted=enc.encrypt("ref"),
            token_expires_at=datetime(2026, 4, 1, tzinfo=UTC),
            scopes=["scope1"],
            connected_at=datetime(2026, 3, 16, tzinfo=UTC),
        )
        assert conn.user_id == USER_ID
        assert conn.provider == IntegrationProvider.GMAIL
        assert conn.status == IntegrationStatus.CONNECTED
        assert conn.last_synced_at is None
        assert conn.sync_cursor is None
        assert conn.scopes == ["scope1"]

    def test_collection_name(self):
        assert IntegrationConnection.Settings.name == "integration_connections"
