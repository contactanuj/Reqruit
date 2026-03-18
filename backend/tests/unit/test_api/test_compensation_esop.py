"""
Tests for the ESOP valuation endpoint.
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


class TestESOPValuationEndpoint:

    async def test_esop_200_with_3_scenarios(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/esop-valuation",
            json={
                "shares": 1000,
                "strike_price": 100.0,
                "current_company_valuation": 10000000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["scenarios"]) == 3
        assert data["scenarios"][0]["scenario_name"] == "Conservative"
        assert data["scenarios"][1]["scenario_name"] == "Moderate"
        assert data["scenarios"][2]["scenario_name"] == "Aggressive"
        assert data["total_shares"] == 1000
        assert data["strike_price"] == 100.0

    async def test_esop_cliff_warning(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/esop-valuation",
            json={
                "shares": 1000,
                "strike_price": 100.0,
                "current_company_valuation": 10000000,
                "cliff_months": 12,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cliff_warning"] == "No value realized before cliff"
        assert data["cliff_date"] is not None

    async def test_esop_no_cliff_warning(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/esop-valuation",
            json={
                "shares": 1000,
                "strike_price": 100.0,
                "current_company_valuation": 10000000,
                "cliff_months": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cliff_warning"] is None

    async def test_esop_vesting_timeline_present(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/esop-valuation",
            json={
                "shares": 4800,
                "strike_price": 100.0,
                "current_company_valuation": 10000000,
                "cliff_months": 12,
                "vesting_frequency": "monthly",
                "vesting_total_months": 48,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["vesting_timeline"]) > 0
        # First tranche is cliff
        assert data["vesting_timeline"][0]["shares"] == 1200

    async def test_esop_with_custom_fmv(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/esop-valuation",
            json={
                "shares": 1000,
                "strike_price": 100.0,
                "current_company_valuation": 10000000,
                "fmv_per_share": 200.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["current_fmv"] == 200.0
        # Perquisite tax should be non-zero since FMV > strike
        assert data["scenarios"][0]["perquisite_tax"] > 0

    async def test_esop_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/compensation/esop-valuation",
            json={
                "shares": 1000,
                "strike_price": 100.0,
                "current_company_valuation": 10000000,
            },
        )
        assert response.status_code in (401, 403)

    async def test_esop_422_missing_required_fields(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/esop-valuation",
            json={"shares": 1000},  # missing strike_price and valuation
        )

        assert response.status_code == 422
