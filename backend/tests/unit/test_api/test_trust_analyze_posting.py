"""Tests for POST /trust/analyze-posting endpoint."""

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


class TestAnalyzePostingEndpoint:
    async def test_200_clean_jd(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/analyze-posting",
            json={
                "job_title": "SDE-2",
                "company_name": "Acme Corp",
                "jd_text": "Looking for experienced Python developer with 5+ years.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "freshness" in data
        assert "red_flags" in data
        assert "india_specific_flags" in data
        assert "recommended_actions" in data
        assert "overall_risk_level" in data
        assert data["overall_risk_level"] == "NONE"

    async def test_200_with_india_locale(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/analyze-posting",
            json={
                "job_title": "Associate",
                "company_name": "Agency",
                "jd_text": "Pay placement fee of Rs. 5000 before joining.",
                "locale": "IN",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["india_specific_flags"]) >= 1
        assert data["india_specific_flags"][0]["category"] == "PLACEMENT_FEE_ILLEGAL"

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/trust/analyze-posting",
            json={
                "job_title": "Dev",
                "company_name": "Corp",
                "jd_text": "Some JD.",
            },
        )
        assert response.status_code in (401, 403)

    async def test_422_missing_required_fields(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/analyze-posting",
            json={"job_title": "Dev"},
        )
        assert response.status_code == 422

    async def test_freshness_in_response(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/trust/analyze-posting",
            json={
                "job_title": "Dev",
                "company_name": "Corp",
                "jd_text": "Standard role.",
                "posted_date": "2025-01-01T00:00:00+00:00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["freshness"]["staleness_flag"] is True
        assert data["freshness"]["days_since_posted"] > 30
