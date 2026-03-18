"""Tests for JobShortlistRepository — date-based shortlist queries."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.repositories.job_shortlist_repository import JobShortlistRepository


def _make_shortlist(**overrides):
    defaults = {
        "user_id": "user1",
        "date": datetime(2026, 3, 17, tzinfo=UTC),
        "jobs": [],
        "generation_cost_usd": 0.02,
        "preferences_snapshot": {},
    }
    defaults.update(overrides)
    shortlist = MagicMock()
    for k, v in defaults.items():
        setattr(shortlist, k, v)
    shortlist.id = "shortlist_id"
    return shortlist


class TestGetByUserAndDate:
    async def test_returns_shortlist_for_date(self):
        repo = JobShortlistRepository()
        expected = _make_shortlist()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=expected):
            result = await repo.get_by_user_and_date("user1", datetime(2026, 3, 17, tzinfo=UTC))
        assert result == expected

    async def test_returns_none_when_missing(self):
        repo = JobShortlistRepository()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None):
            result = await repo.get_by_user_and_date("user1", datetime(2026, 3, 17, tzinfo=UTC))
        assert result is None


class TestGetLatestByUser:
    async def test_returns_most_recent(self):
        repo = JobShortlistRepository()
        expected = _make_shortlist()
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=[expected]):
            result = await repo.get_latest_by_user("user1")
        assert result == expected

    async def test_returns_none_when_no_shortlists(self):
        repo = JobShortlistRepository()
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=[]):
            result = await repo.get_latest_by_user("user1")
        assert result is None


class TestGetHistory:
    async def test_returns_recent_shortlists(self):
        repo = JobShortlistRepository()
        shortlists = [_make_shortlist(), _make_shortlist()]
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=shortlists) as mock_find:
            result = await repo.get_history("user1", limit=7)
        assert len(result) == 2
        mock_find.assert_awaited_once_with(
            filters={"user_id": "user1"},
            limit=7,
            sort="-date",
        )

    async def test_returns_empty_list(self):
        repo = JobShortlistRepository()
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=[]):
            result = await repo.get_history("user1")
        assert result == []
