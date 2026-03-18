"""Tests for ATS export routes — profile data export for auto-fill."""

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from src.api.dependencies import get_current_user


def _make_user():
    user = MagicMock()
    user.id = "user123"
    user.is_active = True
    return user


class TestExportProfile:
    async def test_returns_export_data(self, client: AsyncClient):
        user = _make_user()
        export_data = {
            "format_version": "1.0",
            "personal_info": {"name": "Alice", "email": "alice@example.com"},
            "work_experience": [],
            "education": [],
            "skills": ["Python"],
            "target_roles": ["Backend Engineer"],
            "preferences": {"remote_preference": "remote"},
        }

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user

        with patch(
            "src.api.routes.ats_export._build_service"
        ) as mock_build:
            mock_service = MagicMock()
            mock_service.export_profile = AsyncMock(return_value=export_data)
            mock_build.return_value = mock_service

            resp = await client.get("/profile/export")

        assert resp.status_code == 200
        data = resp.json()
        assert data["format_version"] == "1.0"
        assert data["personal_info"]["name"] == "Alice"
        assert data["skills"] == ["Python"]
        assert data["target_roles"] == ["Backend Engineer"]

        app.dependency_overrides.clear()

    async def test_returns_empty_for_new_user(self, client: AsyncClient):
        user = _make_user()
        export_data = {
            "format_version": "1.0",
            "personal_info": {},
            "work_experience": [],
            "education": [],
            "skills": [],
            "target_roles": [],
            "preferences": {},
        }

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user

        with patch(
            "src.api.routes.ats_export._build_service"
        ) as mock_build:
            mock_service = MagicMock()
            mock_service.export_profile = AsyncMock(return_value=export_data)
            mock_build.return_value = mock_service

            resp = await client.get("/profile/export")

        assert resp.status_code == 200
        data = resp.json()
        assert data["personal_info"] == {}
        assert data["skills"] == []

        app.dependency_overrides.clear()


class TestExportForPlatform:
    async def test_returns_platform_mapped_data(self, client: AsyncClient):
        user = _make_user()
        export_data = {
            "format_version": "1.0",
            "personal_info": {"name": "Alice", "email": "alice@example.com"},
            "work_experience": [],
            "education": [],
            "skills": ["Python"],
            "target_roles": [],
        }

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user

        with patch(
            "src.api.routes.ats_export._build_service"
        ) as mock_build:
            mock_service = MagicMock()
            mock_service.export_profile = AsyncMock(return_value=export_data)
            mock_build.return_value = mock_service

            resp = await client.get("/profile/export/greenhouse")

        assert resp.status_code == 200
        data = resp.json()
        assert data["platform"] == "greenhouse"
        assert data["personal_info"]["candidate_name"] == "Alice"

        app.dependency_overrides.clear()


class TestListPlatforms:
    async def test_returns_supported_platforms(self, client: AsyncClient):
        resp = await client.get("/ats/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert "greenhouse" in data["platforms"]
        assert "lever" in data["platforms"]
        assert "workday" in data["platforms"]
