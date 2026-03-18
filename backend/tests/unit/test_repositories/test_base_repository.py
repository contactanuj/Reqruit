"""
Tests for BaseRepository.delete_many() — bulk delete by filter.

Story 2.2: Cascade Delete Job and All Associated Data.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import DatabaseError
from src.repositories.base import BaseRepository


class TestDeleteMany:
    """Tests for BaseRepository.delete_many()."""

    def _make_repo(self) -> BaseRepository:
        """Create a BaseRepository with a mocked model class."""
        mock_model = MagicMock()
        mock_model.__name__ = "MockDocument"
        repo = BaseRepository(mock_model)
        return repo

    async def test_delete_many_returns_deleted_count(self) -> None:
        """Happy path: returns the number of deleted documents."""
        repo = self._make_repo()
        mock_result = MagicMock()
        mock_result.deleted_count = 5
        mock_query = MagicMock()
        mock_query.delete = AsyncMock(return_value=mock_result)
        repo._model.find.return_value = mock_query

        result = await repo.delete_many({"application_id": "abc123"})

        assert result == 5
        repo._model.find.assert_called_once_with({"application_id": "abc123"})
        mock_query.delete.assert_called_once()

    async def test_delete_many_returns_zero_when_no_matches(self) -> None:
        """Returns 0 when no documents match the filter."""
        repo = self._make_repo()
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_query = MagicMock()
        mock_query.delete = AsyncMock(return_value=mock_result)
        repo._model.find.return_value = mock_query

        result = await repo.delete_many({"application_id": "nonexistent"})

        assert result == 0

    async def test_delete_many_returns_zero_when_result_is_none(self) -> None:
        """Returns 0 when Beanie returns None (edge case)."""
        repo = self._make_repo()
        mock_query = MagicMock()
        mock_query.delete = AsyncMock(return_value=None)
        repo._model.find.return_value = mock_query

        result = await repo.delete_many({"status": "orphaned"})

        assert result == 0

    async def test_delete_many_raises_database_error_on_exception(self) -> None:
        """Wraps exceptions in DatabaseError, consistent with other BaseRepository methods."""
        repo = self._make_repo()
        mock_query = MagicMock()
        mock_query.delete = AsyncMock(side_effect=RuntimeError("connection lost"))
        repo._model.find.return_value = mock_query

        with pytest.raises(DatabaseError, match="Failed to delete"):
            await repo.delete_many({"broken": True})
