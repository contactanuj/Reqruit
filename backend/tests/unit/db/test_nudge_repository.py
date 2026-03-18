"""Tests for NudgeRepository — idempotent creation and lifecycle methods."""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId

from src.db.documents.nudge import NudgeStatus, NudgeType
from src.repositories.nudge_repository import NudgeRepository

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
APP_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
NUDGE_ID = PydanticObjectId("cccccccccccccccccccccccc")


def _make_nudge(**overrides):
    defaults = {
        "user_id": USER_ID,
        "application_id": APP_ID,
        "nudge_type": NudgeType.FOLLOW_UP_REMINDER,
        "status": NudgeStatus.PENDING,
        "title": "Follow up on Acme",
        "message": "It's been 7 days.",
        "suggested_actions": ["Send follow-up email"],
    }
    defaults.update(overrides)
    nudge = MagicMock()
    for k, v in defaults.items():
        setattr(nudge, k, v)
    return nudge


class TestCreateIfNotExists:
    async def test_creates_when_no_duplicate(self):
        repo = NudgeRepository()
        nudge = _make_nudge()
        with (
            patch.object(repo, "find_one", new_callable=AsyncMock, return_value=None),
            patch.object(repo, "create", new_callable=AsyncMock, return_value=nudge),
        ):
            result = await repo.create_if_not_exists(nudge)
        assert result == nudge

    async def test_returns_none_when_duplicate_exists(self):
        repo = NudgeRepository()
        nudge = _make_nudge()
        existing = _make_nudge()
        with patch.object(repo, "find_one", new_callable=AsyncMock, return_value=existing):
            result = await repo.create_if_not_exists(nudge)
        assert result is None


class TestGetPendingByUser:
    async def test_returns_pending_nudges(self):
        repo = NudgeRepository()
        nudges = [_make_nudge(), _make_nudge()]
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=nudges):
            result = await repo.get_pending_by_user(USER_ID)
        assert len(result) == 2

    async def test_uses_correct_filters(self):
        repo = NudgeRepository()
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=[]) as mock_find:
            await repo.get_pending_by_user(USER_ID, limit=10)
        mock_find.assert_awaited_once_with(
            filters={"user_id": USER_ID, "status": NudgeStatus.PENDING},
            limit=10,
            sort="-trigger_date",
        )


class TestGetByUserAndApplication:
    async def test_returns_nudges_for_application(self):
        repo = NudgeRepository()
        nudges = [_make_nudge()]
        with patch.object(repo, "find_many", new_callable=AsyncMock, return_value=nudges):
            result = await repo.get_by_user_and_application(USER_ID, APP_ID)
        assert len(result) == 1


class TestMarkSeen:
    async def test_updates_status_and_seen_at(self):
        repo = NudgeRepository()
        updated = _make_nudge(status=NudgeStatus.SEEN)
        with patch.object(repo, "update", new_callable=AsyncMock, return_value=updated) as mock_update:
            result = await repo.mark_seen(NUDGE_ID)
        assert result == updated
        call_args = mock_update.call_args
        assert call_args[0][0] == NUDGE_ID
        assert call_args[0][1]["status"] == NudgeStatus.SEEN
        assert "seen_at" in call_args[0][1]


class TestMarkDismissed:
    async def test_updates_status_and_dismissed_at(self):
        repo = NudgeRepository()
        updated = _make_nudge(status=NudgeStatus.DISMISSED)
        with patch.object(repo, "update", new_callable=AsyncMock, return_value=updated) as mock_update:
            result = await repo.mark_dismissed(NUDGE_ID)
        assert result == updated
        call_args = mock_update.call_args
        assert call_args[0][1]["status"] == NudgeStatus.DISMISSED
        assert "dismissed_at" in call_args[0][1]


class TestMarkActedOn:
    async def test_updates_status(self):
        repo = NudgeRepository()
        updated = _make_nudge(status=NudgeStatus.ACTED_ON)
        with patch.object(repo, "update", new_callable=AsyncMock, return_value=updated) as mock_update:
            result = await repo.mark_acted_on(NUDGE_ID)
        assert result == updated
        mock_update.assert_awaited_once_with(NUDGE_ID, {"status": NudgeStatus.ACTED_ON})


class TestCountPendingByUser:
    async def test_returns_count(self):
        repo = NudgeRepository()
        with patch.object(repo, "count", new_callable=AsyncMock, return_value=5):
            result = await repo.count_pending_by_user(USER_ID)
        assert result == 5


class TestDeleteByApplication:
    async def test_deletes_all_for_application(self):
        repo = NudgeRepository()
        with patch.object(repo, "delete_many", new_callable=AsyncMock, return_value=3) as mock_delete:
            result = await repo.delete_by_application(APP_ID)
        assert result == 3
        mock_delete.assert_awaited_once_with({"application_id": APP_ID})
