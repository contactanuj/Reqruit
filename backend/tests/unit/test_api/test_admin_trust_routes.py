"""Tests for admin trust routes: GET /admin/trust/review-queue and PATCH /admin/trust/reports/{id}."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_admin_user, get_current_user, get_scam_report_repository
from src.db.documents.scam_report import ScamReport


def _make_admin():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "admin@example.com"
    user.is_active = True
    user.is_admin = True
    return user


def _make_regular_user():
    user = MagicMock()
    user.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    user.email = "user@example.com"
    user.is_active = True
    user.is_admin = False
    return user


def _mock_repo():
    repo = AsyncMock()
    repo.get_unverified_queue = AsyncMock(return_value=[])
    repo.verify_report = AsyncMock(return_value=None)
    repo.apply_warning_badge = AsyncMock()
    return repo


def _make_report(**overrides):
    defaults = {
        "id": PydanticObjectId("cccccccccccccccccccccccc"),
        "reporter_user_id": PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
        "entity_type": "company",
        "entity_identifier": "scam-corp",
        "evidence_type": "description",
        "evidence_text": "Asked for upfront payment",
        "risk_category": "SUSPICIOUS",
        "verified": False,
        "admin_notes": "",
        "warning_badge_applied": False,
    }
    defaults.update(overrides)
    report = MagicMock(spec=ScamReport)
    for k, v in defaults.items():
        setattr(report, k, v)
    return report


class TestGetReviewQueue:
    async def test_200_returns_unverified_reports(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = _mock_repo()
        report = _make_report()
        repo.get_unverified_queue = AsyncMock(return_value=[report])
        client.app.dependency_overrides[get_current_admin_user] = lambda: admin
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.get("/admin/trust/review-queue")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["entity_identifier"] == "scam-corp"
        assert data[0]["verified"] is False

    async def test_200_empty_queue(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = _mock_repo()
        client.app.dependency_overrides[get_current_admin_user] = lambda: admin
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.get("/admin/trust/review-queue")

        assert response.status_code == 200
        assert response.json() == []

    async def test_403_for_non_admin(self, client: AsyncClient) -> None:
        user = _make_regular_user()
        client.app.dependency_overrides[get_current_user] = lambda: user
        # Don't override get_current_admin_user — let the real dependency run
        client.app.dependency_overrides.pop(get_current_admin_user, None)

        response = await client.get("/admin/trust/review-queue")

        assert response.status_code == 403

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        client.app.dependency_overrides.pop(get_current_admin_user, None)
        client.app.dependency_overrides.pop(get_current_user, None)

        response = await client.get("/admin/trust/review-queue")

        assert response.status_code in (401, 403)


class TestPatchVerifyReport:
    async def test_200_verifies_report(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = _mock_repo()
        verified_report = _make_report(verified=True, admin_notes="Confirmed scam")
        repo.verify_report = AsyncMock(return_value=verified_report)
        client.app.dependency_overrides[get_current_admin_user] = lambda: admin
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.patch(
            "/admin/trust/reports/cccccccccccccccccccccccc",
            json={"verified": True, "admin_notes": "Confirmed scam"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
        assert data["admin_notes"] == "Confirmed scam"

    async def test_applies_warning_badge_on_verify(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = _mock_repo()
        verified_report = _make_report(verified=True, admin_notes="Verified")
        repo.verify_report = AsyncMock(return_value=verified_report)
        client.app.dependency_overrides[get_current_admin_user] = lambda: admin
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        await client.patch(
            "/admin/trust/reports/cccccccccccccccccccccccc",
            json={"verified": True, "admin_notes": "Verified"},
        )

        repo.apply_warning_badge.assert_called_once_with("scam-corp")

    async def test_404_for_invalid_report_id(self, client: AsyncClient) -> None:
        admin = _make_admin()
        repo = _mock_repo()
        repo.verify_report = AsyncMock(return_value=None)
        client.app.dependency_overrides[get_current_admin_user] = lambda: admin
        client.app.dependency_overrides[get_scam_report_repository] = lambda: repo

        response = await client.patch(
            "/admin/trust/reports/dddddddddddddddddddddddd",
            json={"verified": True, "admin_notes": "test"},
        )

        assert response.status_code == 404

    async def test_403_for_non_admin(self, client: AsyncClient) -> None:
        user = _make_regular_user()
        client.app.dependency_overrides[get_current_user] = lambda: user
        client.app.dependency_overrides.pop(get_current_admin_user, None)

        response = await client.patch(
            "/admin/trust/reports/cccccccccccccccccccccccc",
            json={"verified": True, "admin_notes": "test"},
        )

        assert response.status_code == 403

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        client.app.dependency_overrides.pop(get_current_admin_user, None)
        client.app.dependency_overrides.pop(get_current_user, None)

        response = await client.patch(
            "/admin/trust/reports/cccccccccccccccccccccccc",
            json={"verified": True, "admin_notes": "test"},
        )

        assert response.status_code in (401, 403)
