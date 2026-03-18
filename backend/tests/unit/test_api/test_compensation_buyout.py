"""
Tests for the buyout calculator endpoint.
"""

from unittest.mock import MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


class TestBuyoutCalculateEndpoint:

    async def test_200_buyout_required(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/buyout-calculate",
            json={
                "monthly_basic": 50000,
                "contractual_notice_days": 90,
                "served_days": 30,
                "offer_joining_date": "2026-02-01",
                "notice_start_date": "2026-01-01",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["remaining_days"] == 60
        assert data["buyout_required"] is True
        assert data["buyout_cost"] > 0
        assert data["gap_days"] is not None

    async def test_200_buyout_not_required(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/buyout-calculate",
            json={
                "monthly_basic": 50000,
                "contractual_notice_days": 90,
                "served_days": 30,
                "offer_joining_date": "2026-06-01",
                "notice_start_date": "2026-01-01",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["buyout_required"] is False
        assert data["gap_days"] is None

    async def test_200_with_joining_bonus(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/buyout-calculate",
            json={
                "monthly_basic": 50000,
                "contractual_notice_days": 90,
                "served_days": 30,
                "offer_joining_date": "2026-02-01",
                "joining_bonus": 200000,
                "notice_start_date": "2026-01-01",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["net_out_of_pocket"] is not None
        assert data["recommendation"] is not None

    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/compensation/buyout-calculate",
            json={
                "monthly_basic": 50000,
                "contractual_notice_days": 90,
                "offer_joining_date": "2026-02-01",
            },
        )
        assert response.status_code in (401, 403)

    async def test_422_missing_required_fields(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/buyout-calculate",
            json={"monthly_basic": 50000},
        )
        assert response.status_code == 422

    async def test_422_served_exceeds_contractual(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/buyout-calculate",
            json={
                "monthly_basic": 50000,
                "contractual_notice_days": 90,
                "served_days": 100,
                "offer_joining_date": "2026-02-01",
            },
        )
        assert response.status_code == 422

    async def test_422_negative_notice_days(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/buyout-calculate",
            json={
                "monthly_basic": 50000,
                "contractual_notice_days": 0,
                "offer_joining_date": "2026-02-01",
            },
        )
        assert response.status_code == 422
