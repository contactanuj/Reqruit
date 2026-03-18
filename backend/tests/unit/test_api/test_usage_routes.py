"""Tests for usage dashboard API: GET /usage/me, GET /usage/me/breakdown."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user
from src.api.routes.usage import _get_usage_service
from src.services.usage_service import (
    PeriodUsage,
    UsageBreakdown,
    UsageSummary,
)

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _make_user(is_admin=False):
    user = MagicMock()
    user.id = USER_ID
    user.email = "test@example.com"
    user.is_active = True
    user.is_admin = is_admin
    return user


def _make_summary(**overrides):
    defaults = {
        "daily": PeriodUsage(total_tokens=100, total_cost_usd=0.001),
        "weekly": PeriodUsage(total_tokens=500, total_cost_usd=0.005),
        "monthly": PeriodUsage(total_tokens=2000, total_cost_usd=0.02),
        "tier": "free",
        "tier_limit_usd": 1.50,
        "tier_limit_tokens": 500_000,
        "usage_percentage": 0.33,
    }
    defaults.update(overrides)
    return UsageSummary(**defaults)


def _make_breakdown(**overrides):
    defaults = {
        "breakdown_by_feature": {"cover_letter": 0.003, "interview_prep": 0.002},
        "breakdown_by_model": {"claude-sonnet-4-5-20250929": 0.005},
        "period_start": datetime(2026, 3, 16, tzinfo=UTC),
        "period_end": datetime(2026, 3, 17, tzinfo=UTC),
    }
    defaults.update(overrides)
    return UsageBreakdown(**defaults)


class TestGetMyUsage:
    async def test_200_returns_summary(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = MagicMock()
        mock_service.get_usage_summary = AsyncMock(return_value=_make_summary())

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[_get_usage_service] = lambda: mock_service

        response = await client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data["daily"]["total_tokens"] == 100
        assert data["weekly"]["total_cost_usd"] == 0.005
        assert data["monthly"]["total_tokens"] == 2000
        assert data["tier"] == "free"
        assert data["tier_limit_usd"] == 1.50
        assert data["tier_limit_tokens"] == 500_000
        assert data["usage_percentage"] == 0.33

    async def test_200_zeroed_for_new_user(self, client: AsyncClient) -> None:
        user = _make_user()
        summary = _make_summary(
            daily=PeriodUsage(),
            weekly=PeriodUsage(),
            monthly=PeriodUsage(),
            usage_percentage=0.0,
        )
        mock_service = MagicMock()
        mock_service.get_usage_summary = AsyncMock(return_value=summary)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[_get_usage_service] = lambda: mock_service

        response = await client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data["daily"]["total_tokens"] == 0
        assert data["daily"]["total_cost_usd"] == 0.0
        assert data["tier"] == "free"

    async def test_admin_tier_reflected(self, client: AsyncClient) -> None:
        user = _make_user(is_admin=True)
        summary = _make_summary(
            tier="admin",
            tier_limit_usd=999999.0,
            tier_limit_tokens=999_999_999,
        )
        mock_service = MagicMock()
        mock_service.get_usage_summary = AsyncMock(return_value=summary)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[_get_usage_service] = lambda: mock_service

        response = await client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "admin"
        assert data["tier_limit_usd"] == 999999.0

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(_get_usage_service, None)

        response = await client.get("/usage/me")
        assert response.status_code in (401, 403)


class TestGetMyUsageBreakdown:
    async def test_200_returns_breakdown(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = MagicMock()
        mock_service.get_usage_breakdown = AsyncMock(
            return_value=_make_breakdown()
        )

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[_get_usage_service] = lambda: mock_service

        response = await client.get("/usage/me/breakdown")

        assert response.status_code == 200
        data = response.json()
        assert data["breakdown_by_feature"]["cover_letter"] == 0.003
        assert data["breakdown_by_feature"]["interview_prep"] == 0.002
        assert data["breakdown_by_model"]["claude-sonnet-4-5-20250929"] == 0.005
        assert "period_start" in data
        assert "period_end" in data

    async def test_200_empty_breakdown(self, client: AsyncClient) -> None:
        user = _make_user()
        breakdown = _make_breakdown(
            breakdown_by_feature={},
            breakdown_by_model={},
        )
        mock_service = MagicMock()
        mock_service.get_usage_breakdown = AsyncMock(return_value=breakdown)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[_get_usage_service] = lambda: mock_service

        response = await client.get("/usage/me/breakdown")

        assert response.status_code == 200
        data = response.json()
        assert data["breakdown_by_feature"] == {}
        assert data["breakdown_by_model"] == {}

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(_get_usage_service, None)

        response = await client.get("/usage/me/breakdown")
        assert response.status_code in (401, 403)
