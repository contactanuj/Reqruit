"""
Unit tests for RefreshTokenRepository.

Tests the CAS revocation, family revocation, and token creation methods.
All Beanie operations are mocked — no database connection needed.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId

from src.repositories.refresh_token_repository import RefreshTokenRepository


class TestGetByJti:
    async def test_returns_token_when_exists(self):
        repo = RefreshTokenRepository()
        mock_token = MagicMock()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=mock_token):
            result = await repo.get_by_jti("some-jti")
            assert result is mock_token

    async def test_returns_none_when_not_found(self):
        repo = RefreshTokenRepository()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None):
            result = await repo.get_by_jti("nonexistent-jti")
            assert result is None

    async def test_queries_by_token_jti(self):
        repo = RefreshTokenRepository()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None) as mock_find:
            await repo.get_by_jti("target-jti")
            mock_find.assert_called_once_with({"token_jti": "target-jti"})


class TestRevokeByJti:
    async def test_returns_true_on_first_revocation(self):
        """CAS success: token was not yet revoked, this call revoked it."""
        repo = RefreshTokenRepository()
        mock_collection = MagicMock()
        mock_collection.find_one_and_update = AsyncMock(return_value=MagicMock())
        with patch(
            "src.repositories.refresh_token_repository.RefreshToken.get_pymongo_collection",
            return_value=mock_collection,
        ):
            result = await repo.revoke_by_jti("jti-1")
            assert result is True

    async def test_returns_false_when_already_revoked(self):
        """CAS failure: token was already revoked by another call."""
        repo = RefreshTokenRepository()
        mock_collection = MagicMock()
        mock_collection.find_one_and_update = AsyncMock(return_value=None)
        with patch(
            "src.repositories.refresh_token_repository.RefreshToken.get_pymongo_collection",
            return_value=mock_collection,
        ):
            result = await repo.revoke_by_jti("jti-1")
            assert result is False

    async def test_uses_atomic_cas_filter(self):
        """Verify the atomic CAS query uses the correct filter."""
        repo = RefreshTokenRepository()
        mock_collection = MagicMock()
        mock_collection.find_one_and_update = AsyncMock(return_value=None)
        with patch(
            "src.repositories.refresh_token_repository.RefreshToken.get_pymongo_collection",
            return_value=mock_collection,
        ):
            await repo.revoke_by_jti("jti-abc")
            mock_collection.find_one_and_update.assert_called_once_with(
                {"token_jti": "jti-abc", "is_revoked": False},
                {"$set": {"is_revoked": True}},
            )


class TestRevokeFamily:
    async def test_revokes_all_tokens_in_family(self):
        repo = RefreshTokenRepository()
        mock_result = MagicMock()
        mock_result.modified_count = 3
        mock_find = MagicMock()
        mock_find.update_many = AsyncMock(return_value=mock_result)
        with patch(
            "src.repositories.refresh_token_repository.RefreshToken.find",
            return_value=mock_find,
        ):
            count = await repo.revoke_family("family-xyz")
            assert count == 3

    async def test_returns_zero_when_no_active_tokens(self):
        repo = RefreshTokenRepository()
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_find = MagicMock()
        mock_find.update_many = AsyncMock(return_value=mock_result)
        with patch(
            "src.repositories.refresh_token_repository.RefreshToken.find",
            return_value=mock_find,
        ):
            count = await repo.revoke_family("family-xyz")
            assert count == 0


class TestCreateToken:
    async def test_creates_and_returns_token(self):
        repo = RefreshTokenRepository()
        user_id = PydanticObjectId()
        expires_at = datetime.now(UTC) + timedelta(days=7)
        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock()
            result = await repo.create_token(
                user_id=user_id,
                jti="jti-new",
                family_id="family-new",
                expires_at=expires_at,
            )
            assert result is not None
            mock_create.assert_called_once()
            created_doc = mock_create.call_args[0][0]
            assert created_doc.user_id == user_id
            assert created_doc.token_jti == "jti-new"
            assert created_doc.family_id == "family-new"
            assert created_doc.expires_at == expires_at
            assert created_doc.is_revoked is False
