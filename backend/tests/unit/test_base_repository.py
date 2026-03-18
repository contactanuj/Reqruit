"""
Tests for the generic BaseRepository.

These tests verify repository behavior using mocked Beanie operations.
No running MongoDB instance is required — all database calls are patched.

Design decisions
----------------
Why mock Beanie operations (not use a real test database):
    Unit tests should be fast, deterministic, and independent of external
    services. Mocking the ODM layer lets us test repository logic (error
    handling, return values, method delegation) without Docker or MongoDB.

    Integration tests with a real database belong in tests/integration/
    and are run manually before releases.

Why test through BaseRepository (not UserRepository):
    BaseRepository contains all the CRUD logic. Testing it directly verifies
    the generic behavior that all concrete repositories inherit. UserRepository
    tests would duplicate these tests plus add auth-specific ones.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from src.core.exceptions import DatabaseError
from src.db.documents.user import User
from src.repositories.base import BaseRepository


@pytest.fixture
def user_repo() -> BaseRepository[User]:
    """Create a BaseRepository instance for User documents."""
    return BaseRepository(User)


@pytest.fixture
def sample_user() -> User:
    """Create a sample User instance for testing."""
    return User(email="test@example.com", hashed_password="hashed_abc123")


# ---------------------------------------------------------------------------
# Create tests
# ---------------------------------------------------------------------------


class TestCreate:
    """Repository.create() should insert documents and handle errors."""

    async def test_create_calls_insert(
        self, user_repo: BaseRepository[User], sample_user: User
    ) -> None:
        """create() should call Beanie's insert() on the document."""
        # Patch insert on the User class — Pydantic v2 does not allow setting
        # arbitrary attributes on model instances (raises ValueError), so we
        # cannot do `sample_user.insert = AsyncMock(...)` directly.
        with patch.object(
            User, "insert", new_callable=AsyncMock, return_value=sample_user
        ) as mock_insert:
            result = await user_repo.create(sample_user)

            mock_insert.assert_awaited_once()
            assert result == sample_user

    async def test_create_raises_database_error_on_failure(
        self, user_repo: BaseRepository[User], sample_user: User
    ) -> None:
        """create() should wrap exceptions in DatabaseError."""
        with (
            patch.object(
                User, "insert", new_callable=AsyncMock,
                side_effect=Exception("duplicate key"),
            ),
            pytest.raises(DatabaseError, match="Failed to create User"),
        ):
            await user_repo.create(sample_user)


# ---------------------------------------------------------------------------
# Read tests
# ---------------------------------------------------------------------------


class TestGetById:
    """Repository.get_by_id() should fetch by ObjectId."""

    async def test_get_by_id_returns_document(
        self, user_repo: BaseRepository[User], sample_user: User
    ) -> None:
        """get_by_id() should return the document when found."""
        doc_id = PydanticObjectId()
        with patch.object(User, "get", new_callable=AsyncMock, return_value=sample_user):
            result = await user_repo.get_by_id(doc_id)
            assert result == sample_user

    async def test_get_by_id_returns_none_when_not_found(
        self, user_repo: BaseRepository[User]
    ) -> None:
        """get_by_id() should return None for non-existent documents."""
        doc_id = PydanticObjectId()
        with patch.object(User, "get", new_callable=AsyncMock, return_value=None):
            result = await user_repo.get_by_id(doc_id)
            assert result is None


class TestFindOne:
    """Repository.find_one() should find by filter dict."""

    async def test_find_one_returns_match(
        self, user_repo: BaseRepository[User], sample_user: User
    ) -> None:
        """find_one() should return the first matching document."""
        with patch.object(
            User, "find_one", new_callable=AsyncMock, return_value=sample_user
        ):
            result = await user_repo.find_one({"email": "test@example.com"})
            assert result == sample_user

    async def test_find_one_returns_none_when_no_match(
        self, user_repo: BaseRepository[User]
    ) -> None:
        """find_one() should return None when no document matches."""
        with patch.object(User, "find_one", new_callable=AsyncMock, return_value=None):
            result = await user_repo.find_one({"email": "nonexistent@example.com"})
            assert result is None


class TestFindMany:
    """Repository.find_many() should support filtering, pagination, and sorting."""

    async def test_find_many_returns_list(
        self, user_repo: BaseRepository[User], sample_user: User
    ) -> None:
        """find_many() should return a list of matching documents."""
        # Build the mock chain: find() -> sort() -> skip() -> limit() -> to_list()
        mock_query = MagicMock()
        mock_query.sort.return_value = mock_query
        mock_query.skip.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.to_list = AsyncMock(return_value=[sample_user])

        with patch.object(User, "find", return_value=mock_query):
            result = await user_repo.find_many(
                filters={"is_active": True},
                skip=0,
                limit=10,
            )
            assert len(result) == 1
            assert result[0] == sample_user

    async def test_find_many_with_sort(
        self, user_repo: BaseRepository[User]
    ) -> None:
        """find_many() should apply sort when provided."""
        mock_query = MagicMock()
        mock_query.sort.return_value = mock_query
        mock_query.skip.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.to_list = AsyncMock(return_value=[])

        with patch.object(User, "find", return_value=mock_query):
            await user_repo.find_many(sort="-created_at")
            mock_query.sort.assert_called_once_with("-created_at")

    async def test_find_many_returns_empty_list(
        self, user_repo: BaseRepository[User]
    ) -> None:
        """find_many() should return empty list when no documents match."""
        mock_query = MagicMock()
        mock_query.skip.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.to_list = AsyncMock(return_value=[])

        with patch.object(User, "find", return_value=mock_query):
            result = await user_repo.find_many()
            assert result == []


# ---------------------------------------------------------------------------
# Update tests
# ---------------------------------------------------------------------------


class TestUpdate:
    """Repository.update() should update specific fields."""

    async def test_update_calls_set(
        self, user_repo: BaseRepository[User], sample_user: User
    ) -> None:
        """update() should call Beanie's .set() with the update data."""
        doc_id = PydanticObjectId()

        with (
            patch.object(User, "get", new_callable=AsyncMock, return_value=sample_user),
            patch.object(User, "set", new_callable=AsyncMock) as mock_set,
        ):
            result = await user_repo.update(doc_id, {"is_active": False})
            mock_set.assert_awaited_once_with({"is_active": False})
            assert result == sample_user

    async def test_update_returns_none_when_not_found(
        self, user_repo: BaseRepository[User]
    ) -> None:
        """update() should return None when the document does not exist."""
        doc_id = PydanticObjectId()
        with patch.object(User, "get", new_callable=AsyncMock, return_value=None):
            result = await user_repo.update(doc_id, {"is_active": False})
            assert result is None

    async def test_update_raises_database_error_on_failure(
        self, user_repo: BaseRepository[User], sample_user: User
    ) -> None:
        """update() should wrap exceptions in DatabaseError."""
        doc_id = PydanticObjectId()

        with (
            patch.object(User, "get", new_callable=AsyncMock, return_value=sample_user),
            patch.object(
                User, "set", new_callable=AsyncMock,
                side_effect=Exception("write error"),
            ),
            pytest.raises(DatabaseError, match="Failed to update User"),
        ):
            await user_repo.update(doc_id, {"is_active": False})


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------


class TestDelete:
    """Repository.delete() should remove documents by ObjectId."""

    async def test_delete_returns_true_when_found(
        self, user_repo: BaseRepository[User], sample_user: User
    ) -> None:
        """delete() should return True after successful deletion."""
        doc_id = PydanticObjectId()

        with (
            patch.object(User, "get", new_callable=AsyncMock, return_value=sample_user),
            patch.object(User, "delete", new_callable=AsyncMock) as mock_delete,
        ):
            result = await user_repo.delete(doc_id)
            assert result is True
            mock_delete.assert_awaited_once()

    async def test_delete_returns_false_when_not_found(
        self, user_repo: BaseRepository[User]
    ) -> None:
        """delete() should return False when the document does not exist."""
        doc_id = PydanticObjectId()
        with patch.object(User, "get", new_callable=AsyncMock, return_value=None):
            result = await user_repo.delete(doc_id)
            assert result is False


# ---------------------------------------------------------------------------
# Count tests
# ---------------------------------------------------------------------------


class TestCount:
    """Repository.count() should count matching documents."""

    async def test_count_returns_number(
        self, user_repo: BaseRepository[User]
    ) -> None:
        """count() should return the number of matching documents."""
        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=42)

        with patch.object(User, "find", return_value=mock_query):
            result = await user_repo.count({"is_active": True})
            assert result == 42

    async def test_count_all_documents(
        self, user_repo: BaseRepository[User]
    ) -> None:
        """count() with no filters should count all documents."""
        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=100)

        with patch.object(User, "find", return_value=mock_query):
            result = await user_repo.count()
            assert result == 100
