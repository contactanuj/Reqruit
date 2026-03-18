"""Tests for UserActivityRepository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from src.db.documents.user_activity import ActivityEntry, UserActivity
from src.repositories.user_activity_repository import UserActivityRepository


USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _make_activity(**kwargs) -> UserActivity:
    defaults = {
        "user_id": USER_ID,
        "date": datetime(2026, 3, 16, tzinfo=UTC),
        "actions": [],
        "streak_count": 0,
        "total_xp": 0,
    }
    defaults.update(kwargs)
    doc = MagicMock(spec=UserActivity)
    for k, v in defaults.items():
        setattr(doc, k, v)
    return doc


class TestGetToday:
    async def test_delegates_to_find_one(self):
        repo = UserActivityRepository()
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.get_today(USER_ID)

        assert result is None
        repo.find_one.assert_called_once()
        call_args = repo.find_one.call_args[0][0]
        assert call_args["user_id"] == USER_ID
        assert "date" in call_args

    async def test_returns_activity_when_found(self):
        repo = UserActivityRepository()
        activity = _make_activity()
        repo.find_one = AsyncMock(return_value=activity)

        result = await repo.get_today(USER_ID)

        assert result is activity


class TestGetOrCreateToday:
    async def test_returns_existing(self):
        repo = UserActivityRepository()
        activity = _make_activity()
        repo.find_one = AsyncMock(return_value=activity)

        result = await repo.get_or_create_today(USER_ID)

        assert result is activity

    async def test_creates_when_not_found(self):
        repo = UserActivityRepository()
        repo.find_one = AsyncMock(return_value=None)
        new_doc = _make_activity()
        repo.create = AsyncMock(return_value=new_doc)

        result = await repo.get_or_create_today(USER_ID)

        assert result is new_doc
        repo.create.assert_called_once()


class TestGetStreak:
    async def test_returns_zero_when_no_records(self):
        repo = UserActivityRepository()
        repo.find_many = AsyncMock(return_value=[])

        streak = await repo.get_streak(USER_ID)

        assert streak == 0

    async def test_returns_streak_from_latest(self):
        repo = UserActivityRepository()
        activity = _make_activity(streak_count=5)
        repo.find_many = AsyncMock(return_value=[activity])

        streak = await repo.get_streak(USER_ID)

        assert streak == 5


class TestGetHistory:
    async def test_returns_records_in_range(self):
        repo = UserActivityRepository()
        a1 = _make_activity(date=datetime(2026, 3, 15, tzinfo=UTC), total_xp=30)
        a2 = _make_activity(date=datetime(2026, 3, 16, tzinfo=UTC), total_xp=50)
        repo.find_many = AsyncMock(return_value=[a2, a1])

        result = await repo.get_history(
            USER_ID,
            datetime(2026, 3, 15, tzinfo=UTC),
            datetime(2026, 3, 16, tzinfo=UTC),
        )

        assert len(result) == 2
        repo.find_many.assert_called_once()
