"""Tests for EmailSignalRepository with idempotent creation."""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId

from src.db.documents.email_signal import EmailSignal
from src.db.documents.integration_connection import IntegrationProvider
from src.repositories.email_signal_repository import EmailSignalRepository

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
PROVIDER = IntegrationProvider.GMAIL


class TestCreateIfNotExists:
    async def test_creates_new_signal(self):
        repo = EmailSignalRepository()
        signal = MagicMock(spec=EmailSignal)
        signal.user_id = USER_ID
        signal.message_id = "msg_123"

        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None),
            patch.object(repo, "create", new_callable=AsyncMock, return_value=signal),
        ):
            result = await repo.create_if_not_exists(signal)

        assert result == signal

    async def test_returns_none_for_duplicate(self):
        repo = EmailSignalRepository()
        signal = MagicMock(spec=EmailSignal)
        signal.user_id = USER_ID
        signal.message_id = "msg_123"

        existing = MagicMock(spec=EmailSignal)
        with patch.object(
            repo, "find_one", new_callable=AsyncMock, return_value=existing
        ):
            result = await repo.create_if_not_exists(signal)

        assert result is None


class TestGetByUser:
    async def test_returns_signals_sorted(self):
        repo = EmailSignalRepository()
        signals = [MagicMock(spec=EmailSignal), MagicMock(spec=EmailSignal)]

        with patch.object(
            repo, "find_many", new_callable=AsyncMock, return_value=signals
        ):
            result = await repo.get_by_user(USER_ID, limit=10, offset=0)

        assert len(result) == 2

    async def test_empty_list_for_no_signals(self):
        repo = EmailSignalRepository()

        with patch.object(
            repo, "find_many", new_callable=AsyncMock, return_value=[]
        ):
            result = await repo.get_by_user(USER_ID)

        assert result == []


class TestGetByUserAndPattern:
    async def test_filters_by_pattern(self):
        repo = EmailSignalRepository()
        signal = MagicMock(spec=EmailSignal)
        signal.matched_pattern = "interview_invitation"

        with patch.object(
            repo, "find_many", new_callable=AsyncMock, return_value=[signal]
        ):
            result = await repo.get_by_user_and_pattern(
                USER_ID, "interview_invitation"
            )

        assert len(result) == 1


class TestDeleteByUserAndProvider:
    async def test_deletes_and_returns_count(self):
        repo = EmailSignalRepository()

        with patch.object(
            repo, "delete_many", new_callable=AsyncMock, return_value=5
        ):
            result = await repo.delete_by_user_and_provider(USER_ID, PROVIDER)

        assert result == 5


class TestUpdateSourceToUserReported:
    async def test_updates_source_field(self):
        repo = EmailSignalRepository()
        mock_result = MagicMock()
        mock_result.modified_count = 3

        with patch.object(EmailSignal, "find") as mock_find:
            mock_find.return_value.update_many = AsyncMock(return_value=mock_result)
            result = await repo.update_source_to_user_reported(USER_ID, PROVIDER)

        assert result == 3

    async def test_returns_zero_when_none_updated(self):
        repo = EmailSignalRepository()

        with patch.object(EmailSignal, "find") as mock_find:
            mock_find.return_value.update_many = AsyncMock(return_value=None)
            result = await repo.update_source_to_user_reported(USER_ID, PROVIDER)

        assert result == 0
