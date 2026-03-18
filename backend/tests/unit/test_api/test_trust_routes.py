"""Tests for trust verification routes."""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user
from src.services.trust.models import RiskCategory, RiskSignal, TrustScore


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


def _mock_agent_result(**overrides) -> dict:
    base = {
        "company_verification_score": 80.0,
        "recruiter_verification_score": 75.0,
        "posting_freshness_score": 85.0,
        "red_flag_count": 0,
        "overall_trust_score": 80.0,
        "risk_category": "LIKELY_SAFE",
        "risk_signals": [],
    }
    base.update(overrides)
    return base


class TestPostTrustVerify:
    async def test_200_returns_trust_score(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=AsyncMock(return_value=_mock_agent_result()),
        ):
            response = await client.post(
                "/trust/verify",
                json={"company_name": "Acme Corp"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "acme corp"
        assert data["overall_trust_score"] == 80.0
        assert data["risk_category"] == "LIKELY_SAFE"
        assert data["company_verification_score"] == 80.0
        assert data["recruiter_verification_score"] == 75.0

    async def test_200_with_recruiter_email(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=AsyncMock(return_value=_mock_agent_result()),
        ):
            response = await client.post(
                "/trust/verify",
                json={
                    "company_name": "Acme Corp",
                    "recruiter_email": "hr@gmail.com",
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Personal email should add a risk signal
        signal_types = [s["signal_type"] for s in data["risk_signals"]]
        assert "PERSONAL_EMAIL_DOMAIN" in signal_types

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/trust/verify",
            json={"company_name": "Acme Corp"},
        )
        assert response.status_code in (401, 403)

    async def test_422_missing_company_name(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post("/trust/verify", json={})
        assert response.status_code == 422

    async def test_entity_id_includes_email(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=AsyncMock(return_value=_mock_agent_result()),
        ):
            response = await client.post(
                "/trust/verify",
                json={
                    "company_name": "Acme Corp",
                    "recruiter_email": "hr@acme.com",
                },
            )

        data = response.json()
        assert "hr@acme.com" in data["entity_id"]


class TestGetJobTrust:
    async def test_404_when_no_cached_score(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.get("/trust/jobs/nonexistent123")
        assert response.status_code == 404

    async def test_200_when_cached(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        # First, cache a score via the verification service's job cache
        with patch(
            "src.api.routes.trust._verification_service"
        ) as mock_svc:
            score = TrustScore(
                company_verification_score=90.0,
                recruiter_verification_score=85.0,
                overall_trust_score=88.0,
                risk_category=RiskCategory.VERIFIED,
            )
            mock_svc.get_cached_score_for_job.return_value = score

            response = await client.get("/trust/jobs/job456")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job456"
        assert data["overall_trust_score"] == 88.0
        assert data["risk_category"] == "VERIFIED"

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/trust/jobs/job789")
        assert response.status_code in (401, 403)
