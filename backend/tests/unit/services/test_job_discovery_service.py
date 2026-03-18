"""Tests for JobDiscoveryService — preference management and shortlist retrieval."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.documents.job_shortlist import DiscoveryPreferences
from src.services.job_discovery_service import JobDiscoveryService


def _make_service(profile_repo=None, shortlist_repo=None):
    return JobDiscoveryService(
        profile_repo=profile_repo or MagicMock(),
        shortlist_repo=shortlist_repo or MagicMock(),
    )


def _make_profile(**overrides):
    profile = MagicMock()
    profile.id = "profile_id"
    profile.user_id = "user1"
    profile.discovery_preferences = overrides.get("discovery_preferences")
    return profile


class TestUpdatePreferences:
    async def test_saves_preferences(self):
        profile = _make_profile()
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=profile)
        profile_repo.update = AsyncMock(return_value=profile)

        service = _make_service(profile_repo=profile_repo)
        prefs = DiscoveryPreferences(
            roles=["backend"],
            locations=["Remote"],
            salary_min=100000,
            salary_max=150000,
        )
        result = await service.update_preferences("user1", prefs)

        assert result.roles == ["backend"]
        assert result.salary_min == 100000
        profile_repo.update.assert_awaited_once()

    async def test_raises_when_no_profile(self):
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=None)

        service = _make_service(profile_repo=profile_repo)
        prefs = DiscoveryPreferences(roles=["backend"])

        with pytest.raises(ValueError, match="Profile not found"):
            await service.update_preferences("user1", prefs)


class TestGetPreferences:
    async def test_returns_preferences_from_dict(self):
        profile = _make_profile(
            discovery_preferences={
                "roles": ["frontend"],
                "locations": ["NYC"],
                "salary_min": 80000,
                "salary_max": 120000,
                "company_sizes": [],
                "remote_only": True,
            }
        )
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=profile)

        service = _make_service(profile_repo=profile_repo)
        result = await service.get_preferences("user1")

        assert result is not None
        assert result.roles == ["frontend"]
        assert result.remote_only is True

    async def test_returns_none_when_no_profile(self):
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=None)

        service = _make_service(profile_repo=profile_repo)
        result = await service.get_preferences("user1")
        assert result is None

    async def test_returns_none_when_no_preferences_set(self):
        profile = _make_profile(discovery_preferences=None)
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=profile)

        service = _make_service(profile_repo=profile_repo)
        result = await service.get_preferences("user1")
        assert result is None

    async def test_returns_preferences_object_directly(self):
        prefs_obj = DiscoveryPreferences(roles=["data"], remote_only=True)
        profile = _make_profile()
        profile.discovery_preferences = prefs_obj
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=profile)

        service = _make_service(profile_repo=profile_repo)
        result = await service.get_preferences("user1")
        assert result is not None
        assert result.roles == ["data"]


class TestGetLatestShortlist:
    async def test_delegates_to_repo(self):
        shortlist = MagicMock()
        shortlist_repo = MagicMock()
        shortlist_repo.get_latest_by_user = AsyncMock(return_value=shortlist)

        service = _make_service(shortlist_repo=shortlist_repo)
        result = await service.get_latest_shortlist("user1")
        assert result == shortlist

    async def test_returns_none_when_empty(self):
        shortlist_repo = MagicMock()
        shortlist_repo.get_latest_by_user = AsyncMock(return_value=None)

        service = _make_service(shortlist_repo=shortlist_repo)
        result = await service.get_latest_shortlist("user1")
        assert result is None


class TestGetShortlistHistory:
    async def test_returns_history(self):
        shortlists = [MagicMock(), MagicMock()]
        shortlist_repo = MagicMock()
        shortlist_repo.get_history = AsyncMock(return_value=shortlists)

        service = _make_service(shortlist_repo=shortlist_repo)
        result = await service.get_shortlist_history("user1", limit=5)
        assert len(result) == 2
        shortlist_repo.get_history.assert_awaited_once_with("user1", limit=5)
