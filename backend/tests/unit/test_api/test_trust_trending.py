"""Tests for GET /trust/trending endpoint."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_scam_report_repository


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


def _mock_repo():
    repo = AsyncMock()
    repo.get_trending_aggregation = AsyncMock(return_value=[])
    return repo


class TestGetTrendingScams:
    async def test_200_returns_trending_patterns(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        repo.get_trending_aggregation = AsyncMock(return_value=[
            {
                "_id": "scam-corp",
                "report_count": 5,
                "risk_categories": ["SUSPICIOUS", "SCAM_LIKELY"],
                "entity_types": ["company"],
            },
            {
                "_id": "phish-inc",
                "report_count": 3,
                "risk_categories": ["SUSPICIOUS"],
                "entity_types": ["recruiter"],
            },
        ])
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.get("/trust/trending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["affected_companies"] == ["scam-corp"]
        assert data[0]["report_count"] == 5
        assert data[0]["pattern_type"] == "company"

    async def test_200_with_region_filter(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        repo.get_trending_aggregation = AsyncMock(return_value=[
            {
                "_id": "india-scam",
                "report_count": 4,
                "risk_categories": ["SUSPICIOUS"],
                "entity_types": ["posting"],
            },
        ])
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.get("/trust/trending", params={"region": "IN"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["region"] == "IN"

    async def test_200_empty_list_when_no_data(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.get("/trust/trending")

        assert response.status_code == 200
        assert response.json() == []

    async def test_filters_low_count_entries(self, client: AsyncClient) -> None:
        """Entries with report_count < 2 should be excluded from trending."""
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        repo.get_trending_aggregation = AsyncMock(return_value=[
            {
                "_id": "one-report-entity",
                "report_count": 1,
                "risk_categories": ["SUSPICIOUS"],
                "entity_types": ["company"],
            },
        ])
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.get("/trust/trending")

        assert response.status_code == 200
        assert response.json() == []

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/trust/trending")
        assert response.status_code in (401, 403)
