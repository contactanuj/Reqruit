"""Tests for discovery API routes — preferences and shortlists."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_discovery_service
from src.db.documents.job_shortlist import DiscoveryPreferences


def _make_user():
    user = MagicMock()
    user.id = "user123"
    user.is_active = True
    return user


def _make_job_mock(**overrides):
    defaults = {
        "job_id": None,
        "source": "indeed_api",
        "source_url": "https://indeed.com/job/123",
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "Remote",
        "fit_score": 0.85,
        "roi_prediction": "high",
        "trust_score": 0.9,
        "salary_range": "100k-150k",
        "match_reasons": ["skills match", "location match"],
    }
    defaults.update(overrides)
    job = MagicMock()
    for k, v in defaults.items():
        setattr(job, k, v)
    return job


class TestUpdatePreferences:
    async def test_saves_and_returns_preferences(self, client: AsyncClient):
        user = _make_user()
        prefs = DiscoveryPreferences(
            roles=["backend"],
            locations=["Remote"],
            salary_min=100000,
            salary_max=150000,
        )
        mock_service = MagicMock()
        mock_service.update_preferences = AsyncMock(return_value=prefs)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_discovery_service] = lambda: mock_service

        resp = await client.put("/discovery/preferences", json={
            "roles": ["backend"],
            "locations": ["Remote"],
            "salary_min": 100000,
            "salary_max": 150000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["roles"] == ["backend"]
        assert data["salary_min"] == 100000

        app.dependency_overrides.clear()

    async def test_raises_when_no_profile(self, client: AsyncClient):
        user = _make_user()
        mock_service = MagicMock()
        mock_service.update_preferences = AsyncMock(
            side_effect=ValueError("Profile not found")
        )

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_discovery_service] = lambda: mock_service

        resp = await client.put("/discovery/preferences", json={"roles": ["backend"]})
        assert resp.status_code == 404

        app.dependency_overrides.clear()


class TestGetPreferences:
    async def test_returns_preferences(self, client: AsyncClient):
        user = _make_user()
        prefs = DiscoveryPreferences(
            roles=["frontend"],
            locations=["NYC"],
            remote_only=True,
        )
        mock_service = MagicMock()
        mock_service.get_preferences = AsyncMock(return_value=prefs)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_discovery_service] = lambda: mock_service

        resp = await client.get("/discovery/preferences")
        assert resp.status_code == 200
        data = resp.json()
        assert data["roles"] == ["frontend"]
        assert data["remote_only"] is True

        app.dependency_overrides.clear()

    async def test_returns_null_when_not_set(self, client: AsyncClient):
        user = _make_user()
        mock_service = MagicMock()
        mock_service.get_preferences = AsyncMock(return_value=None)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_discovery_service] = lambda: mock_service

        resp = await client.get("/discovery/preferences")
        assert resp.status_code == 200
        assert resp.json() is None

        app.dependency_overrides.clear()


class TestGetShortlist:
    async def test_returns_latest_shortlist(self, client: AsyncClient):
        user = _make_user()
        job = _make_job_mock()

        shortlist = MagicMock()
        shortlist.date = datetime(2026, 3, 17, tzinfo=UTC)
        shortlist.jobs = [job]
        shortlist.generation_cost_usd = 0.02

        mock_service = MagicMock()
        mock_service.get_latest_shortlist = AsyncMock(return_value=shortlist)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_discovery_service] = lambda: mock_service

        resp = await client.get("/discovery/shortlist")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["title"] == "Backend Engineer"
        assert data["jobs"][0]["fit_score"] == 0.85

        app.dependency_overrides.clear()

    async def test_returns_null_when_no_shortlist(self, client: AsyncClient):
        user = _make_user()
        mock_service = MagicMock()
        mock_service.get_latest_shortlist = AsyncMock(return_value=None)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_discovery_service] = lambda: mock_service

        resp = await client.get("/discovery/shortlist")
        assert resp.status_code == 200
        assert resp.json() is None

        app.dependency_overrides.clear()


class TestGetHistory:
    async def test_returns_shortlist_history(self, client: AsyncClient):
        user = _make_user()
        job = _make_job_mock(title="Data Engineer", source="naukri", company="Corp",
                             location="Bangalore", fit_score=0.7, roi_prediction="medium",
                             trust_score=None, salary_range="", match_reasons=[],
                             source_url="")

        shortlist = MagicMock()
        shortlist.date = datetime(2026, 3, 16, tzinfo=UTC)
        shortlist.jobs = [job]
        shortlist.generation_cost_usd = 0.01

        mock_service = MagicMock()
        mock_service.get_shortlist_history = AsyncMock(return_value=[shortlist])

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_discovery_service] = lambda: mock_service

        resp = await client.get("/discovery/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert len(data[0]["jobs"]) == 1

        app.dependency_overrides.clear()

    async def test_returns_empty_history(self, client: AsyncClient):
        user = _make_user()
        mock_service = MagicMock()
        mock_service.get_shortlist_history = AsyncMock(return_value=[])

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_discovery_service] = lambda: mock_service

        resp = await client.get("/discovery/history")
        assert resp.status_code == 200
        assert resp.json() == []

        app.dependency_overrides.clear()
