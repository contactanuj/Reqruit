"""Tests for GET /applications/analytics/compare endpoint."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_assembly_graph,
    get_current_user,
    get_success_analytics_service,
)


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user, analytics_svc):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_success_analytics_service] = lambda: analytics_svc
    app.dependency_overrides[get_application_assembly_graph] = lambda: MagicMock()


class TestCompareVersions:
    async def test_default_resume_strategy(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_ab_comparison = AsyncMock(return_value={
            "comparison_possible": True,
            "compare_by": "resume_strategy",
            "versions": [
                {"strategy_name": "v1", "sample_size": 15, "response_rate": 0.6,
                 "view_rate": 0.8, "interview_rate": 0.4, "significance": "sufficient"},
            ],
            "message": "",
        })
        _override(client.app, user, svc)

        response = await client.get("/applications/analytics/compare")

        assert response.status_code == 200
        data = response.json()
        assert data["comparison_possible"] is True
        svc.get_ab_comparison.assert_called_once()

    async def test_cover_letter_strategy(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_ab_comparison = AsyncMock(return_value={
            "comparison_possible": True,
            "compare_by": "cover_letter_strategy",
            "versions": [],
            "message": "",
        })
        _override(client.app, user, svc)

        response = await client.get(
            "/applications/analytics/compare?compare_by=cover_letter_strategy"
        )

        assert response.status_code == 200
        assert response.json()["compare_by"] == "cover_letter_strategy"

    async def test_invalid_compare_by_422(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        _override(client.app, user, svc)

        response = await client.get(
            "/applications/analytics/compare?compare_by=invalid_field"
        )

        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_COMPARE_BY"

    async def test_single_strategy_message(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_ab_comparison = AsyncMock(return_value={
            "comparison_possible": False,
            "compare_by": "resume_strategy",
            "versions": [],
            "message": "Only one strategy found. Try varying your approach to enable A/B comparison.",
        })
        _override(client.app, user, svc)

        response = await client.get("/applications/analytics/compare")

        data = response.json()
        assert data["comparison_possible"] is False
        assert "one" in data["message"].lower() or "vary" in data["message"].lower()


class TestCompareAuth:
    async def test_requires_auth(self, client: AsyncClient) -> None:
        client.app.dependency_overrides.clear()

        response = await client.get("/applications/analytics/compare")

        assert response.status_code in (401, 403)
