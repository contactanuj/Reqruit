"""Tests for POST /trust/ghost-check endpoint."""

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
    repo.get_distinct_reporter_count = AsyncMock(return_value=0)
    repo.has_warning_badge = AsyncMock(return_value=False)
    return repo


class TestGhostCheckEndpoint:
    async def test_200_with_job_url(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/ghost-check",
            json={"job_url": "https://example.com/job/123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "liveness_score" in data
        assert "verdict" in data
        assert "signals" in data
        assert len(data["signals"]) == 5
        assert "recommendation" in data

    async def test_200_with_company_and_title(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/ghost-check",
            json={
                "company_name": "Acme Corp",
                "job_title": "Software Engineer",
                "posted_date": "2026-03-10T00:00:00+00:00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] in ("likely_ghost", "uncertain", "likely_active")

    async def test_422_no_inputs(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/ghost-check",
            json={},
        )

        assert response.status_code == 422

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/trust/ghost-check",
            json={"job_url": "https://example.com/job/123"},
        )
        assert response.status_code in (401, 403)
