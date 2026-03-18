"""Tests for admin usage routes: /admin/usage/*, /admin/tiers/*."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_admin_user,
    get_current_user,
    get_usage_service,
)
from src.core.exceptions import NotFoundError
from src.services.usage_service import (
    AdminUsageSummary,
    TierChangeResult,
    UsageAnomaly,
)

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
ADMIN_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


def _make_admin():
    user = MagicMock()
    user.id = ADMIN_ID
    user.email = "admin@example.com"
    user.is_active = True
    user.is_admin = True
    return user


def _make_regular_user():
    user = MagicMock()
    user.id = USER_ID
    user.email = "user@example.com"
    user.is_active = True
    user.is_admin = False
    return user


def _make_summary():
    return AdminUsageSummary(
        total_cost_this_week=10.5,
        per_user_average_usd=5.25,
        model_routing_distribution={"claude-sonnet": 60.0, "claude-haiku": 40.0},
        user_count_by_tier={"FREE": 5, "PRO": 2},
        period_start=datetime(2026, 3, 16, tzinfo=UTC),
        period_end=datetime(2026, 3, 17, tzinfo=UTC),
    )


class TestAdminUsageSummary:
    async def test_200_returns_summary(self, client: AsyncClient) -> None:
        admin = _make_admin()
        mock_service = MagicMock()
        mock_service.get_admin_summary = AsyncMock(return_value=_make_summary())

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_usage_service] = lambda: mock_service

        response = await client.get("/admin/usage/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_cost_this_week"] == 10.5
        assert data["per_user_average_usd"] == 5.25
        assert data["user_count_by_tier"]["FREE"] == 5
        assert data["model_routing_distribution"]["claude-sonnet"] == 60.0

    async def test_403_for_non_admin(self, client: AsyncClient) -> None:
        user = _make_regular_user()
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides.pop(get_current_admin_user, None)

        response = await client.get("/admin/usage/summary")
        assert response.status_code == 403

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_admin_user, None)

        response = await client.get("/admin/usage/summary")
        assert response.status_code in (401, 403)


class TestAdminUsageAnomalies:
    async def test_200_returns_anomalies(self, client: AsyncClient) -> None:
        admin = _make_admin()
        anomalies = [
            UsageAnomaly(
                user_id="aaaaaaaaaaaaaaaaaaaaaaaa",
                current_week_cost=4.0,
                rolling_avg_cost=1.0,
                spike_multiplier=4.0,
                anomaly_type="cost_spike",
            )
        ]
        mock_service = MagicMock()
        mock_service.get_usage_anomalies = AsyncMock(return_value=anomalies)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_usage_service] = lambda: mock_service

        response = await client.get("/admin/usage/anomalies")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["anomaly_type"] == "cost_spike"
        assert data[0]["spike_multiplier"] == 4.0

    async def test_200_empty_anomalies(self, client: AsyncClient) -> None:
        admin = _make_admin()
        mock_service = MagicMock()
        mock_service.get_usage_anomalies = AsyncMock(return_value=[])

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_usage_service] = lambda: mock_service

        response = await client.get("/admin/usage/anomalies")

        assert response.status_code == 200
        assert response.json() == []

    async def test_403_for_non_admin(self, client: AsyncClient) -> None:
        user = _make_regular_user()
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides.pop(get_current_admin_user, None)

        response = await client.get("/admin/usage/anomalies")
        assert response.status_code == 403


class TestUpdateUserTier:
    async def test_200_updates_tier(self, client: AsyncClient) -> None:
        admin = _make_admin()
        result = TierChangeResult(
            user_id=str(USER_ID),
            previous_tier="free",
            new_tier="pro",
            effective_immediately=True,
        )
        mock_service = MagicMock()
        mock_service.update_user_tier = AsyncMock(return_value=result)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_usage_service] = lambda: mock_service

        response = await client.put(
            f"/admin/tiers/{USER_ID}",
            json={"tier": "pro"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["previous_tier"] == "free"
        assert data["new_tier"] == "pro"
        assert data["effective_immediately"] is True

    async def test_422_invalid_tier(self, client: AsyncClient) -> None:
        admin = _make_admin()
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin

        response = await client.put(
            f"/admin/tiers/{USER_ID}",
            json={"tier": "ultra"},
        )
        assert response.status_code == 422

    async def test_404_user_not_found(self, client: AsyncClient) -> None:
        admin = _make_admin()
        mock_service = MagicMock()
        mock_service.update_user_tier = AsyncMock(
            side_effect=NotFoundError("User", str(USER_ID))
        )

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_usage_service] = lambda: mock_service

        response = await client.put(
            f"/admin/tiers/{USER_ID}",
            json={"tier": "pro"},
        )
        assert response.status_code == 404

    async def test_403_for_non_admin(self, client: AsyncClient) -> None:
        user = _make_regular_user()
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides.pop(get_current_admin_user, None)

        response = await client.put(
            f"/admin/tiers/{USER_ID}",
            json={"tier": "pro"},
        )
        assert response.status_code == 403
