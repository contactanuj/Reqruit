"""Tests for POST /trust/analyze-communication endpoint."""

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


class TestAnalyzeCommunication:
    async def test_200_returns_risk_flags(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/analyze-communication",
            json={
                "communication_channel": "telegram",
                "recruiter_behavior": ["upfront_payment", "pressure_tactics"],
                "hiring_stage": "application",
                "jurisdiction": "IN",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["risk_flags"]) == 2
        assert data["overall_risk_level"] == "HIGH"
        assert len(data["recommended_actions"]) >= 1
        assert data["pii_assessment"] is None

    async def test_200_with_pii_assessment(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/analyze-communication",
            json={
                "communication_channel": "email",
                "recruiter_behavior": ["early_pii_request"],
                "hiring_stage": "application",
                "pii_requested": ["aadhaar", "bank_details"],
                "jurisdiction": "IN",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pii_assessment"] is not None
        assert data["pii_assessment"]["hiring_stage"] == "application"
        assert len(data["pii_assessment"]["alerts"]) == 2

    async def test_200_without_pii_skips_assessment(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/analyze-communication",
            json={
                "communication_channel": "email",
                "recruiter_behavior": ["off_platform_request"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pii_assessment"] is None
        assert data["overall_risk_level"] == "MEDIUM"

    async def test_200_no_risky_behaviors(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/analyze-communication",
            json={
                "communication_channel": "email",
                "recruiter_behavior": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_flags"] == []
        assert data["overall_risk_level"] == "LOW"

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/trust/analyze-communication",
            json={
                "communication_channel": "email",
                "recruiter_behavior": ["upfront_payment"],
            },
        )
        assert response.status_code in (401, 403)
