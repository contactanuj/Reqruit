"""Tests for POST /trust/report and GET /trust/reports endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_scam_report_repository
from src.db.documents.scam_report import ScamReport


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
    repo.get_entity_summary = AsyncMock(return_value={
        "entity_identifier": "test-entity",
        "report_count": 0,
        "risk_categories": [],
        "warning_badge": False,
        "reporters": [],
    })
    return repo


class TestPostTrustReport:
    async def test_201_creates_report(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/report",
            json={
                "entity_type": "company",
                "entity_identifier": "scam-corp",
                "evidence_type": "description",
                "evidence_text": "They asked for money",
                "risk_category": "SUSPICIOUS",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["entity_type"] == "company"
        assert data["entity_identifier"] == "scam-corp"

    async def test_409_duplicate_report(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        repo.check_duplicate = AsyncMock(return_value=True)
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/report",
            json={
                "entity_type": "company",
                "entity_identifier": "scam-corp",
                "evidence_type": "description",
                "evidence_text": "duplicate",
                "risk_category": "SUSPICIOUS",
            },
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "ALREADY_REPORTED"

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/trust/report",
            json={
                "entity_type": "company",
                "entity_identifier": "test",
                "evidence_text": "test",
                "risk_category": "SUSPICIOUS",
            },
        )
        assert response.status_code in (401, 403)

    async def test_422_invalid_entity_type(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/report",
            json={
                "entity_type": "invalid_type",
                "entity_identifier": "test",
                "evidence_text": "test",
                "risk_category": "SUSPICIOUS",
            },
        )
        assert response.status_code == 422

    async def test_422_invalid_evidence_type(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.post(
            "/trust/report",
            json={
                "entity_type": "company",
                "entity_identifier": "test",
                "evidence_type": "video",
                "evidence_text": "test",
                "risk_category": "SUSPICIOUS",
            },
        )
        assert response.status_code == 422


class TestGetTrustReports:
    async def test_returns_summary(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        repo.get_entity_summary = AsyncMock(return_value={
            "entity_identifier": "scam-corp",
            "report_count": 3,
            "risk_categories": ["SUSPICIOUS"],
            "warning_badge": True,
            "reporters": ["abc123", "def456", "ghi789"],
        })
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.get(
            "/trust/reports",
            params={"entity_identifier": "scam-corp"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["report_count"] == 3
        assert data["warning_badge"] is True
        # Verify no raw user IDs exposed (reporters should be hashed strings)
        for r in data["reporters"]:
            assert len(r) <= 12  # truncated hash

    async def test_empty_for_unknown_entity(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)
        repo = _mock_repo()
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.get(
            "/trust/reports",
            params={"entity_identifier": "nonexistent"},
        )

        assert response.status_code == 200
        assert response.json()["report_count"] == 0

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            "/trust/reports",
            params={"entity_identifier": "test"},
        )
        assert response.status_code in (401, 403)
