"""Tests for POST /trust/damage-control endpoint."""

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


class TestDamageControlEndpoint:
    async def test_200_returns_recovery_plan(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/damage-control",
            json={
                "scam_type": "financial_fraud",
                "information_shared": ["bank_details", "email"],
                "jurisdiction": "IN",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scam_type"] == "financial_fraud"
        assert data["jurisdiction"] == "IN"
        assert len(data["immediate_actions"]) >= 1
        assert len(data["complaint_filing"]) >= 1
        assert len(data["monitoring_steps"]) >= 1
        assert len(data["platform_flagging"]) >= 1

    async def test_200_us_jurisdiction(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/damage-control",
            json={
                "scam_type": "identity_theft",
                "information_shared": ["ssn"],
                "jurisdiction": "US",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["jurisdiction"] == "US"
        # Should have SSA and IRS steps
        actions = [s["action"] for s in data["complaint_filing"]]
        assert any("Social Security" in a for a in actions)

    async def test_422_invalid_scam_type(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/damage-control",
            json={
                "scam_type": "invalid_type",
                "information_shared": [],
                "jurisdiction": "US",
            },
        )

        assert response.status_code == 422

    async def test_422_invalid_jurisdiction(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/damage-control",
            json={
                "scam_type": "financial_fraud",
                "information_shared": [],
                "jurisdiction": "UK",
            },
        )

        assert response.status_code == 422

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/trust/damage-control",
            json={
                "scam_type": "financial_fraud",
                "information_shared": [],
                "jurisdiction": "US",
            },
        )
        assert response.status_code in (401, 403)
