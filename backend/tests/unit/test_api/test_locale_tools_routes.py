"""
Unit tests for locale tools routes.

Covers:
    POST /locale/tools/resume-review   — regional resume guidance
    POST /locale/tools/scam-check      — scam analysis
    POST /locale/tools/visa-check      — visa eligibility
    POST /locale/tools/cultural-prep   — cultural interview prep
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_market_config_repository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_market_config():
    config = MagicMock()
    config.resume_conventions = MagicMock()
    config.resume_conventions.model_dump.return_value = {
        "include_photo": False,
        "paper_size": "letter",
        "expected_pages_max": 2,
    }
    config.cultural = MagicMock()
    config.cultural.model_dump.return_value = {
        "formality_level": "casual",
        "interview_style": "behavioral-heavy",
        "languages": ["English"],
    }
    config.cultural.interview_style = "behavioral-heavy"
    config.cultural.formality_level = "casual"
    config.cultural.languages = ["English"]
    config.hiring_process = MagicMock()
    config.hiring_process.model_dump.return_value = {
        "notice_period_norm_days": 14,
        "buyout_culture": False,
    }
    config.legal = MagicMock()
    config.legal.visa_requirements = [
        {"type": "H-1B", "description": "Specialty occupation visa"},
    ]
    config.legal.non_compete_enforceable = True
    config.legal.worker_protections = "At-will employment"
    return config


# ---------------------------------------------------------------------------
# POST /locale/tools/resume-review
# ---------------------------------------------------------------------------


class TestResumeReview:
    async def test_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = MagicMock()
        repo.get_by_region = AsyncMock(return_value=_make_market_config())

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.post(
                "/locale/tools/resume-review",
                json={"resume_content": "John Doe, Engineer...", "target_market": "US"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["target_market"] == "US"
            assert "resume_conventions" in data
        finally:
            app.dependency_overrides.clear()

    async def test_empty_content_returns_422(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        try:
            response = await client.post(
                "/locale/tools/resume-review",
                json={"resume_content": "   ", "target_market": "US"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_unknown_market_returns_404(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = MagicMock()
        repo.get_by_region = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.post(
                "/locale/tools/resume-review",
                json={"resume_content": "My resume...", "target_market": "ZZ"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /locale/tools/scam-check
# ---------------------------------------------------------------------------


class TestScamCheck:
    async def test_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        try:
            response = await client.post(
                "/locale/tools/scam-check",
                json={
                    "title": "Software Engineer",
                    "description": "Join our team at Acme Corp.",
                    "company_name": "Acme Corporation",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "risk_score" in data
            assert "risk_level" in data
            assert data["risk_level"] == "LOW"
        finally:
            app.dependency_overrides.clear()

    async def test_scam_posting_detected(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        try:
            response = await client.post(
                "/locale/tools/scam-check",
                json={
                    "title": "Act now urgent hiring",
                    "description": "Pay registration fee to apply",
                    "company_email": "jobs@yahoo.com",
                    "contact_method": "whatsapp",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["risk_level"] in ("HIGH", "CRITICAL")
            assert len(data["flags"]) > 0
        finally:
            app.dependency_overrides.clear()

    async def test_empty_posting_returns_422(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        try:
            response = await client.post(
                "/locale/tools/scam-check",
                json={},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /locale/tools/visa-check
# ---------------------------------------------------------------------------


class TestVisaCheck:
    async def test_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = MagicMock()
        repo.get_by_region = AsyncMock(return_value=_make_market_config())

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.post(
                "/locale/tools/visa-check",
                json={"nationality": "IN", "target_market": "US"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["target_market"] == "US"
            assert len(data["visa_requirements"]) > 0
        finally:
            app.dependency_overrides.clear()

    async def test_unknown_market_returns_404(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = MagicMock()
        repo.get_by_region = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.post(
                "/locale/tools/visa-check",
                json={"nationality": "IN", "target_market": "ZZ"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /locale/tools/cultural-prep
# ---------------------------------------------------------------------------


class TestCulturalPrep:
    async def test_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = MagicMock()
        repo.get_by_region = AsyncMock(return_value=_make_market_config())

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.post(
                "/locale/tools/cultural-prep",
                json={"target_market": "US"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["target_market"] == "US"
            assert "cultural_context" in data
            assert "interview_style" in data
        finally:
            app.dependency_overrides.clear()

    async def test_unknown_market_returns_404(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = MagicMock()
        repo.get_by_region = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.post(
                "/locale/tools/cultural-prep",
                json={"target_market": "ZZ"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
