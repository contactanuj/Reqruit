"""Tests for GET /applications/analytics/strategy endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

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


def _make_graph_mock():
    return MagicMock()


def _override(app, user, analytics_svc):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_success_analytics_service] = lambda: analytics_svc
    app.dependency_overrides[get_application_assembly_graph] = lambda: _make_graph_mock()


class TestStrategyInsightsInsufficientData:
    async def test_returns_generic_recommendations(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_response_rate = AsyncMock(
            return_value={"total": 3, "response_rate": 0.0, "by_method": {}}
        )
        _override(client.app, user, svc)

        response = await client.get("/applications/analytics/strategy")

        assert response.status_code == 200
        data = response.json()
        assert data["data_driven"] is False
        assert data["confidence"] == "insufficient"
        assert len(data["recommendations"]) > 0
        assert data["top_resume_strategy"] is None
        assert data["timing_analysis"] == []
        assert data["ai_narrative"] == ""


class TestStrategyInsightsWithData:
    async def test_returns_data_driven_insights(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_response_rate = AsyncMock(
            return_value={"total": 20, "response_rate": 0.35, "by_method": {}}
        )
        svc.get_strategy_comparison = AsyncMock(return_value={
            "resume_strategies": [
                {"strategy": "technical", "response_rate": 0.5, "sample_size": 10}
            ],
            "cover_letter_strategies": [],
            "confidence": "moderate",
        })
        svc.get_timing_analysis = AsyncMock(return_value={
            "windows": [
                {"day_of_week": "Tuesday", "time_bucket": "morning", "sample_size": 5,
                 "response_rate": 0.6, "confidence": "low"}
            ],
            "confidence": "moderate",
        })
        _override(client.app, user, svc)

        with patch("src.api.routes.application_assembly.SuccessPatternAgent") as MockAgent:
            mock_instance = AsyncMock()
            mock_instance.return_value = {"success_insights": "Use technical resumes."}
            MockAgent.return_value = mock_instance

            response = await client.get("/applications/analytics/strategy")

        assert response.status_code == 200
        data = response.json()
        assert data["data_driven"] is True
        assert data["confidence"] == "moderate"
        assert data["top_resume_strategy"]["strategy"] == "technical"
        assert len(data["timing_analysis"]) == 1
        assert data["ai_narrative"] == "Use technical resumes."

    async def test_no_strategies_returns_null(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_response_rate = AsyncMock(
            return_value={"total": 10, "response_rate": 0.2, "by_method": {}}
        )
        svc.get_strategy_comparison = AsyncMock(return_value={
            "resume_strategies": [],
            "cover_letter_strategies": [],
            "confidence": "low",
        })
        svc.get_timing_analysis = AsyncMock(return_value={
            "windows": [], "confidence": "low",
        })
        _override(client.app, user, svc)

        with patch("src.api.routes.application_assembly.SuccessPatternAgent") as MockAgent:
            mock_instance = AsyncMock()
            mock_instance.return_value = {"success_insights": "Not enough strategy data."}
            MockAgent.return_value = mock_instance

            response = await client.get("/applications/analytics/strategy")

        data = response.json()
        assert data["top_resume_strategy"] is None
        assert data["top_cover_letter_strategy"] is None


class TestStrategyInsightsAuth:
    async def test_requires_auth(self, client: AsyncClient) -> None:
        client.app.dependency_overrides.clear()

        response = await client.get("/applications/analytics/strategy")

        assert response.status_code in (401, 403)
