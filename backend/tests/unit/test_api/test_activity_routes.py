"""Tests for /activity/* endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user
from src.db.documents.user_activity import ActivityEntry, UserActivity


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


def _make_activity(**kwargs):
    defaults = {
        "user_id": PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
        "date": datetime(2026, 3, 16, tzinfo=UTC),
        "actions": [],
        "streak_count": 0,
        "total_xp": 0,
        "current_league": "bronze",
        "freeze_count": 0,
        "week_start_xp": 0,
    }
    defaults.update(kwargs)
    mock = MagicMock(spec=UserActivity)
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.save = AsyncMock()
    return mock


class TestTrackAction:
    async def test_200_valid_action(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        activity = _make_activity()

        with patch("src.api.routes.activity.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.find_one = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=activity)
            mock_repo.get_today = AsyncMock(return_value=activity)
            mock_repo.find_many = AsyncMock(return_value=[])
            mock_repo.get_or_create_today = AsyncMock(return_value=activity)

            response = await client.post(
                "/activity/track",
                json={"action_type": "job_saved", "metadata": {}},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["action_type"] == "job_saved"
        assert data["xp_earned"] == 5

    async def test_422_invalid_action_type(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        activity = _make_activity()

        with patch("src.api.routes.activity.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_or_create_today = AsyncMock(return_value=activity)
            mock_repo.find_one = AsyncMock(return_value=None)
            mock_repo.find_many = AsyncMock(return_value=[])

            response = await client.post(
                "/activity/track",
                json={"action_type": "invalid_action"},
            )

        assert response.status_code == 422

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/activity/track",
            json={"action_type": "job_saved"},
        )
        assert response.status_code in (401, 403)


class TestGetTodayActivity:
    async def test_200_no_activity(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.activity.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.find_one = AsyncMock(return_value=None)
            mock_repo.get_today = AsyncMock(return_value=None)

            response = await client.get("/activity/today")

        assert response.status_code == 200
        data = response.json()
        assert data["actions"] == []
        assert data["total_xp"] == 0
        assert data["current_league"] == "bronze"

    async def test_200_with_activity(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        entry = ActivityEntry(
            action_type="job_saved",
            xp_earned=5,
            timestamp=datetime.now(UTC),
        )
        activity = _make_activity(
            actions=[entry], total_xp=5, current_league="bronze"
        )

        with patch("src.api.routes.activity.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_today = AsyncMock(return_value=activity)

            response = await client.get("/activity/today")

        assert response.status_code == 200
        data = response.json()
        assert len(data["actions"]) == 1
        assert data["total_xp"] == 5

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/activity/today")
        assert response.status_code in (401, 403)


class TestGetHistory:
    async def test_200_valid_range(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        a1 = _make_activity(
            date=datetime(2026, 3, 15, tzinfo=UTC),
            total_xp=30,
            actions=[],
        )

        with patch("src.api.routes.activity.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[a1])

            response = await client.get(
                "/activity/history",
                params={"from_date": "2026-03-15", "to_date": "2026-03-16"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    async def test_422_exceeds_90_days(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.get(
            "/activity/history",
            params={"from_date": "2025-01-01", "to_date": "2025-12-31"},
        )

        assert response.status_code == 422

    async def test_422_from_after_to(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.get(
            "/activity/history",
            params={"from_date": "2026-03-20", "to_date": "2026-03-10"},
        )

        assert response.status_code == 422

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            "/activity/history",
            params={"from_date": "2026-03-15", "to_date": "2026-03-16"},
        )
        assert response.status_code in (401, 403)


class TestGetStreak:
    async def test_200_no_activity(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.activity.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_today = AsyncMock(return_value=None)

            response = await client.get("/activity/streak")

        assert response.status_code == 200
        data = response.json()
        assert data["streak_count"] == 0
        assert data["freeze_count"] == 0
        assert data["next_milestone"] == 7

    async def test_200_with_streak(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        activity = _make_activity(streak_count=10, freeze_count=2)

        with patch("src.api.routes.activity.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_today = AsyncMock(return_value=activity)

            response = await client.get("/activity/streak")

        assert response.status_code == 200
        data = response.json()
        assert data["streak_count"] == 10
        assert data["freeze_count"] == 2
        assert data["next_milestone"] == 14
        assert 7 in data["milestone_history"]

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/activity/streak")
        assert response.status_code in (401, 403)


class TestGetLeague:
    async def test_200_bronze(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        activity = _make_activity(week_start_xp=50, current_league="bronze")

        with patch("src.api.routes.activity.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_today = AsyncMock(return_value=activity)

            response = await client.get("/activity/league")

        assert response.status_code == 200
        data = response.json()
        assert data["current_league"] == "bronze"
        assert data["weekly_xp"] == 50

    async def test_200_season_boost_flag(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        activity = _make_activity(week_start_xp=100, current_league="silver")

        with (
            patch("src.api.routes.activity.UserActivityRepository") as MockRepo,
            patch("src.services.streak_service.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2026, 2, 15, tzinfo=UTC)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            mock_repo = MockRepo.return_value
            mock_repo.get_today = AsyncMock(return_value=activity)

            response = await client.get("/activity/league", params={"locale": "IN"})

        assert response.status_code == 200
        data = response.json()
        assert data["season_boost_active"] is True

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/activity/league")
        assert response.status_code in (401, 403)
