"""Tests for nudge API routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_nudge_repository
from src.db.documents.nudge import NudgeStatus, NudgeType

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
NUDGE_ID = PydanticObjectId("cccccccccccccccccccccccc")
APP_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


def _make_user():
    user = MagicMock()
    user.id = USER_ID
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_nudge_doc(**overrides):
    defaults = {
        "id": NUDGE_ID,
        "user_id": USER_ID,
        "application_id": APP_ID,
        "nudge_type": NudgeType.FOLLOW_UP_REMINDER,
        "status": NudgeStatus.PENDING,
        "title": "Time to follow up on Acme",
        "message": "It's been 7 days since you applied.",
        "suggested_actions": ["Send follow-up email"],
        "trigger_date": datetime(2026, 3, 10, tzinfo=UTC),
    }
    defaults.update(overrides)
    nudge = MagicMock()
    for k, v in defaults.items():
        setattr(nudge, k, v)
    return nudge


class TestListNudges:
    async def test_returns_pending_nudges(self, client: AsyncClient):
        user = _make_user()
        nudge = _make_nudge_doc()
        mock_repo = MagicMock()
        mock_repo.get_pending_by_user = AsyncMock(return_value=[nudge])

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.get("/nudges")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Time to follow up on Acme"
        assert data[0]["nudge_type"] == NudgeType.FOLLOW_UP_REMINDER

        app.dependency_overrides.clear()

    async def test_returns_empty_list(self, client: AsyncClient):
        user = _make_user()
        mock_repo = MagicMock()
        mock_repo.get_pending_by_user = AsyncMock(return_value=[])

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.get("/nudges")
        assert resp.status_code == 200
        assert resp.json() == []

        app.dependency_overrides.clear()


class TestNudgeCount:
    async def test_returns_count(self, client: AsyncClient):
        user = _make_user()
        mock_repo = MagicMock()
        mock_repo.count_pending_by_user = AsyncMock(return_value=3)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.get("/nudges/count")
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

        app.dependency_overrides.clear()


class TestMarkSeen:
    async def test_marks_nudge_as_seen(self, client: AsyncClient):
        user = _make_user()
        nudge = _make_nudge_doc(status=NudgeStatus.SEEN)
        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=nudge)
        mock_repo.mark_seen = AsyncMock(return_value=nudge)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.patch(f"/nudges/{NUDGE_ID}/seen")
        assert resp.status_code == 200
        assert resp.json()["status"] == NudgeStatus.SEEN

        app.dependency_overrides.clear()

    async def test_not_found(self, client: AsyncClient):
        user = _make_user()
        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=None)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.patch(f"/nudges/{NUDGE_ID}/seen")
        assert resp.status_code == 404

        app.dependency_overrides.clear()


class TestDismissNudge:
    async def test_dismisses_nudge(self, client: AsyncClient):
        user = _make_user()
        nudge = _make_nudge_doc(status=NudgeStatus.DISMISSED)
        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=nudge)
        mock_repo.mark_dismissed = AsyncMock(return_value=nudge)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.patch(f"/nudges/{NUDGE_ID}/dismiss")
        assert resp.status_code == 200
        assert resp.json()["status"] == NudgeStatus.DISMISSED

        app.dependency_overrides.clear()

    async def test_not_found(self, client: AsyncClient):
        user = _make_user()
        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=None)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.patch(f"/nudges/{NUDGE_ID}/dismiss")
        assert resp.status_code == 404

        app.dependency_overrides.clear()


class TestActedOnNudge:
    async def test_marks_acted_on(self, client: AsyncClient):
        user = _make_user()
        nudge = _make_nudge_doc(status=NudgeStatus.ACTED_ON)
        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=nudge)
        mock_repo.mark_acted_on = AsyncMock(return_value=nudge)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.patch(f"/nudges/{NUDGE_ID}/acted-on")
        assert resp.status_code == 200
        assert resp.json()["status"] == NudgeStatus.ACTED_ON

        app.dependency_overrides.clear()

    async def test_not_found(self, client: AsyncClient):
        user = _make_user()
        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=None)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_nudge_repository] = lambda: mock_repo

        resp = await client.patch(f"/nudges/{NUDGE_ID}/acted-on")
        assert resp.status_code == 404

        app.dependency_overrides.clear()
