"""Tests for admin discovery routes — source health dashboard."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from src.api.dependencies import get_current_admin_user


def _make_admin_user():
    user = MagicMock()
    user.id = "admin123"
    user.is_active = True
    user.is_admin = True
    return user


def _make_health(**overrides):
    defaults = {
        "source_name": "indeed_api",
        "status": "healthy",
        "last_check_at": datetime(2026, 3, 17, 5, 0, tzinfo=UTC),
        "last_success_at": datetime(2026, 3, 17, 5, 0, tzinfo=UTC),
        "consecutive_failures": 0,
        "avg_response_ms": 42.5,
        "error_rate_24h": 0.0,
        "disabled": False,
        "last_error": "",
    }
    defaults.update(overrides)
    health = MagicMock()
    for k, v in defaults.items():
        setattr(health, k, v)
    return health


class TestGetSourceHealth:
    async def test_returns_all_sources(self, client: AsyncClient):
        admin = _make_admin_user()
        sources = [
            _make_health(),
            _make_health(source_name="naukri_scraper", status="degraded", consecutive_failures=2),
        ]

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin

        with patch(
            "src.api.routes.admin_discovery.DataSourceHealthRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_all_sources = AsyncMock(return_value=sources)
            mock_repo_cls.return_value = mock_repo

            resp = await client.get("/admin/discovery/sources/health")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["source_name"] == "indeed_api"
        assert data[0]["status"] == "healthy"
        assert data[1]["source_name"] == "naukri_scraper"
        assert data[1]["consecutive_failures"] == 2

        app.dependency_overrides.clear()

    async def test_returns_empty_when_no_sources(self, client: AsyncClient):
        admin = _make_admin_user()

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin

        with patch(
            "src.api.routes.admin_discovery.DataSourceHealthRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_all_sources = AsyncMock(return_value=[])
            mock_repo_cls.return_value = mock_repo

            resp = await client.get("/admin/discovery/sources/health")

        assert resp.status_code == 200
        assert resp.json() == []

        app.dependency_overrides.clear()


class TestToggleSource:
    async def test_disables_source(self, client: AsyncClient):
        admin = _make_admin_user()
        toggled = _make_health(disabled=True)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin

        with patch(
            "src.api.routes.admin_discovery.DataSourceHealthRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.set_disabled = AsyncMock(return_value=toggled)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(
                "/admin/discovery/sources/indeed_api/toggle",
                json={"disabled": True},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["source_name"] == "indeed_api"
        assert data["disabled"] is True

        app.dependency_overrides.clear()

    async def test_returns_404_for_unknown_source(self, client: AsyncClient):
        admin = _make_admin_user()

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin

        with patch(
            "src.api.routes.admin_discovery.DataSourceHealthRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.set_disabled = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await client.post(
                "/admin/discovery/sources/unknown/toggle",
                json={"disabled": True},
            )

        assert resp.status_code == 404

        app.dependency_overrides.clear()


class TestCacheAnalytics:
    async def test_returns_analytics(self, client: AsyncClient):
        admin = _make_admin_user()
        stats = {
            "total_entries": 50,
            "total_hits": 200,
            "total_cost_usd": 0.5,
            "total_tokens": 10000,
            "avg_cost_per_entry_usd": 0.01,
            "estimated_savings_usd": 2.0,
            "hit_rate": 0.8,
        }

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin

        with patch(
            "src.api.routes.admin_discovery.JDCacheRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_analytics = AsyncMock(return_value=stats)
            mock_repo_cls.return_value = mock_repo

            resp = await client.get("/admin/discovery/cache/analytics")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_entries"] == 50
        assert data["total_hits"] == 200
        assert data["estimated_savings_usd"] == 2.0
        assert data["hit_rate"] == 0.8

        app.dependency_overrides.clear()

    async def test_returns_zeros_when_empty(self, client: AsyncClient):
        admin = _make_admin_user()
        stats = {
            "total_entries": 0,
            "total_hits": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "avg_cost_per_entry_usd": 0.0,
            "estimated_savings_usd": 0.0,
            "hit_rate": 0.0,
        }

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = lambda: admin

        with patch(
            "src.api.routes.admin_discovery.JDCacheRepository"
        ) as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_analytics = AsyncMock(return_value=stats)
            mock_repo_cls.return_value = mock_repo

            resp = await client.get("/admin/discovery/cache/analytics")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_entries"] == 0
        assert data["estimated_savings_usd"] == 0.0

        app.dependency_overrides.clear()
