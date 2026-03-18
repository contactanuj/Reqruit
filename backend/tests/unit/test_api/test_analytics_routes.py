"""Tests for analytics summary API endpoint."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_success_analytics_service
from src.services.success_analytics import (
    AnalyticsSummaryResponse,
    FieldBreakdown,
    RateBreakdown,
    TimeBreakdown,
)


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_summary(total=10, sufficiency="sufficient", message=None):
    return AnalyticsSummaryResponse(
        total_applications=total,
        data_sufficiency=sufficiency,
        response_rate=RateBreakdown(total=total, count=4, rate=0.4),
        view_rate=RateBreakdown(total=total, count=6, rate=0.6),
        interview_rate=RateBreakdown(total=total, count=2, rate=0.2),
        breakdown_by_submission_method=[
            FieldBreakdown(value="linkedin", count=6, rate=0.6),
            FieldBreakdown(value="email", count=4, rate=0.4),
        ],
        breakdown_by_resume_strategy=[
            FieldBreakdown(value="keyword_focused", count=7, rate=0.7),
        ],
        breakdown_by_day_of_week=[
            TimeBreakdown(bucket="Monday", count=3),
            TimeBreakdown(bucket="Tuesday", count=2),
        ],
        breakdown_by_time_of_day=[
            TimeBreakdown(bucket=9, count=4),
            TimeBreakdown(bucket=14, count=3),
        ],
        message=message,
    )


def _override(app, user, analytics_svc):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_success_analytics_service] = lambda: analytics_svc


class TestAnalyticsSummary:
    async def test_summary_200(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_summary = AsyncMock(return_value=_make_summary())
        _override(client.app, user, svc)

        response = await client.get("/applications/analytics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_applications"] == 10
        assert data["data_sufficiency"] == "sufficient"
        assert data["response_rate"]["rate"] == 0.4
        assert data["view_rate"]["rate"] == 0.6
        assert data["interview_rate"]["rate"] == 0.2
        assert data["message"] is None

    async def test_summary_low_data(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_summary = AsyncMock(
            return_value=_make_summary(
                total=3,
                sufficiency="low",
                message="Fewer than 5 tracked applications. Analytics may not reflect reliable patterns.",
            )
        )
        _override(client.app, user, svc)

        response = await client.get("/applications/analytics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["data_sufficiency"] == "low"
        assert data["message"] is not None
        assert "Fewer than 5" in data["message"]

    async def test_summary_has_breakdowns(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_summary = AsyncMock(return_value=_make_summary())
        _override(client.app, user, svc)

        response = await client.get("/applications/analytics/summary")

        data = response.json()
        assert len(data["breakdown_by_submission_method"]) == 2
        assert data["breakdown_by_submission_method"][0]["value"] == "linkedin"
        assert len(data["breakdown_by_day_of_week"]) == 2
        assert len(data["breakdown_by_time_of_day"]) == 2

    async def test_summary_schema_fields(self, client: AsyncClient) -> None:
        user = _make_user()
        svc = MagicMock()
        svc.get_summary = AsyncMock(return_value=_make_summary())
        _override(client.app, user, svc)

        response = await client.get("/applications/analytics/summary")
        data = response.json()

        expected_keys = {
            "total_applications", "data_sufficiency", "response_rate",
            "view_rate", "interview_rate", "breakdown_by_submission_method",
            "breakdown_by_resume_strategy", "breakdown_by_day_of_week",
            "breakdown_by_time_of_day", "message",
        }
        assert set(data.keys()) == expected_keys


class TestAnalyticsAuthRequired:
    async def test_requires_auth(self, client: AsyncClient) -> None:
        client.app.dependency_overrides.clear()

        response = await client.get("/applications/analytics/summary")

        assert response.status_code in (401, 403)
