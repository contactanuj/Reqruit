"""Tests for GET /trust/deepfake-guide and POST /trust/deepfake-report endpoints."""

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
    repo.check_duplicate = AsyncMock(return_value=False)
    repo.create = AsyncMock(side_effect=lambda doc: doc)
    repo.has_warning_badge = AsyncMock(return_value=False)
    repo.get_distinct_reporter_count = AsyncMock(return_value=1)
    repo.apply_warning_badge = AsyncMock()
    return repo


class TestDeepfakeGuide:
    async def test_200_returns_checklist(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.get("/trust/deepfake-guide")

        assert response.status_code == 200
        data = response.json()
        assert len(data["categories"]) == 4
        assert "last_updated" in data

    async def test_all_items_have_fields(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.get("/trust/deepfake-guide")
        data = response.json()

        for category in data["categories"]:
            assert "category_name" in category
            for item in category["items"]:
                assert "check" in item
                assert "description" in item
                assert "severity" in item

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/trust/deepfake-guide")
        assert response.status_code in (401, 403)


class TestDeepfakeReport:
    async def test_201_creates_report(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/deepfake-report",
            json={
                "company_name": "Fake Corp",
                "observed_anomalies": ["lip_sync_mismatch", "edge_artifacts"],
                "interview_platform": "zoom",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["entity_type"] == "interview"
        assert data["entity_identifier"] == "Fake Corp"

    async def test_201_uses_interview_id_as_entity(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/deepfake-report",
            json={
                "interview_id": "interview-abc-123",
                "observed_anomalies": ["robotic_speech"],
            },
        )

        assert response.status_code == 201
        assert response.json()["entity_identifier"] == "interview-abc-123"

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/trust/deepfake-report",
            json={
                "observed_anomalies": ["test"],
            },
        )
        assert response.status_code in (401, 403)
