"""Tests for daily shortlist generation task and scoring logic."""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


class TestScoreJobs:
    def test_role_match_scores_high(self):
        from src.tasks.discovery_tasks import _score_jobs

        listing = MagicMock()
        listing.title = "Senior Backend Engineer"
        listing.location = "Remote"
        listing.salary_range = "100k-150k"
        listing.source = "indeed"
        listing.source_url = "https://indeed.com/1"
        listing.company = "Acme"

        prefs = {"roles": ["backend"], "locations": ["Remote"], "remote_only": True}
        result = _score_jobs([listing], prefs)

        assert len(result) == 1
        assert result[0]["score"] >= 0.7
        assert any("Role match" in r for r in result[0]["reasons"])

    def test_remote_match(self):
        from src.tasks.discovery_tasks import _score_jobs

        listing = MagicMock()
        listing.title = "Data Analyst"
        listing.location = "Remote - USA"
        listing.salary_range = ""

        prefs = {"roles": [], "locations": [], "remote_only": True}
        result = _score_jobs([listing], prefs)
        assert any("Remote" in r for r in result[0]["reasons"])

    def test_location_match(self):
        from src.tasks.discovery_tasks import _score_jobs

        listing = MagicMock()
        listing.title = "Engineer"
        listing.location = "Bangalore, India"
        listing.salary_range = ""

        prefs = {"roles": [], "locations": ["bangalore"], "remote_only": False}
        result = _score_jobs([listing], prefs)
        assert any("Location" in r for r in result[0]["reasons"])

    def test_salary_disclosed_bonus(self):
        from src.tasks.discovery_tasks import _score_jobs

        listing = MagicMock()
        listing.title = "Developer"
        listing.location = "NYC"
        listing.salary_range = "80k-100k"

        prefs = {"roles": [], "locations": [], "remote_only": False}
        result = _score_jobs([listing], prefs)
        assert any("Salary" in r for r in result[0]["reasons"])

    def test_general_match_fallback(self):
        from src.tasks.discovery_tasks import _score_jobs

        listing = MagicMock()
        listing.title = "Manager"
        listing.location = "London"
        listing.salary_range = ""

        prefs = {"roles": ["backend"], "locations": ["NYC"], "remote_only": False}
        result = _score_jobs([listing], prefs)
        assert result[0]["score"] == 0.1
        assert "General match" in result[0]["reasons"]

    def test_sorted_by_score_descending(self):
        from src.tasks.discovery_tasks import _score_jobs

        high = MagicMock(title="Backend Engineer", location="Remote", salary_range="100k")
        low = MagicMock(title="Manager", location="London", salary_range="")

        prefs = {"roles": ["backend"], "locations": [], "remote_only": True}
        result = _score_jobs([low, high], prefs)
        assert result[0]["score"] >= result[1]["score"]

    def test_score_capped_at_one(self):
        from src.tasks.discovery_tasks import _score_jobs

        listing = MagicMock()
        listing.title = "Backend Engineer"
        listing.location = "Remote"
        listing.salary_range = "100k-200k"

        prefs = {"roles": ["backend"], "locations": ["remote"], "remote_only": True}
        result = _score_jobs([listing], prefs)
        assert result[0]["score"] <= 1.0


class TestGenerateAllShortlists:
    async def test_generates_for_users_with_preferences(self):
        profile = MagicMock()
        profile.user_id = USER_ID
        profile.discovery_preferences = {"roles": ["backend"], "locations": ["Remote"]}

        mock_profile_repo = MagicMock()
        mock_profile_repo.find_many = AsyncMock(return_value=[profile])

        mock_shortlist_repo = MagicMock()
        mock_shortlist_repo.get_by_user_and_date = AsyncMock(return_value=None)
        mock_shortlist_repo.create = AsyncMock()

        mock_health_repo = MagicMock()
        healthy_source = MagicMock()
        healthy_source.source_name = "indeed_api"
        mock_health_repo.get_healthy_sources = AsyncMock(return_value=[healthy_source])

        listing = MagicMock()
        listing.title = "Backend Dev"
        listing.location = "Remote"
        listing.salary_range = ""
        listing.source = "indeed_api"
        listing.source_url = "https://indeed.com/1"
        listing.company = "Acme"

        mock_client = MagicMock()
        mock_client.search_jobs = AsyncMock(return_value=[listing])

        mock_registry = {"indeed_api": MagicMock(return_value=mock_client)}

        with (
            patch("src.repositories.profile_repository.ProfileRepository", return_value=mock_profile_repo),
            patch("src.repositories.job_shortlist_repository.JobShortlistRepository", return_value=mock_shortlist_repo),
            patch("src.repositories.data_source_health_repository.DataSourceHealthRepository", return_value=mock_health_repo),
            patch("src.integrations.job_source_clients.JOB_SOURCE_REGISTRY", mock_registry),
        ):
            from src.tasks.discovery_tasks import _generate_all_shortlists
            result = await _generate_all_shortlists()

        assert result["generated"] == 1
        assert result["errors"] == 0

    async def test_skips_existing_shortlists(self):
        profile = MagicMock()
        profile.user_id = USER_ID
        profile.discovery_preferences = {"roles": ["backend"]}

        mock_profile_repo = MagicMock()
        mock_profile_repo.find_many = AsyncMock(return_value=[profile])

        mock_shortlist_repo = MagicMock()
        mock_shortlist_repo.get_by_user_and_date = AsyncMock(return_value=MagicMock())

        mock_health_repo = MagicMock()
        mock_health_repo.get_healthy_sources = AsyncMock(return_value=[])

        with (
            patch("src.repositories.profile_repository.ProfileRepository", return_value=mock_profile_repo),
            patch("src.repositories.job_shortlist_repository.JobShortlistRepository", return_value=mock_shortlist_repo),
            patch("src.repositories.data_source_health_repository.DataSourceHealthRepository", return_value=mock_health_repo),
            patch("src.integrations.job_source_clients.JOB_SOURCE_REGISTRY", {}),
        ):
            from src.tasks.discovery_tasks import _generate_all_shortlists
            result = await _generate_all_shortlists()

        assert result["generated"] == 0

    async def test_skips_profiles_without_preferences(self):
        profile = MagicMock()
        profile.user_id = USER_ID
        profile.discovery_preferences = None

        mock_profile_repo = MagicMock()
        mock_profile_repo.find_many = AsyncMock(return_value=[profile])

        mock_shortlist_repo = MagicMock()
        mock_health_repo = MagicMock()
        mock_health_repo.get_healthy_sources = AsyncMock(return_value=[])

        with (
            patch("src.repositories.profile_repository.ProfileRepository", return_value=mock_profile_repo),
            patch("src.repositories.job_shortlist_repository.JobShortlistRepository", return_value=mock_shortlist_repo),
            patch("src.repositories.data_source_health_repository.DataSourceHealthRepository", return_value=mock_health_repo),
            patch("src.integrations.job_source_clients.JOB_SOURCE_REGISTRY", {}),
        ):
            from src.tasks.discovery_tasks import _generate_all_shortlists
            result = await _generate_all_shortlists()

        assert result["generated"] == 0

    async def test_handles_source_query_failure(self):
        profile = MagicMock()
        profile.user_id = USER_ID
        profile.discovery_preferences = {"roles": ["backend"], "locations": []}

        mock_profile_repo = MagicMock()
        mock_profile_repo.find_many = AsyncMock(return_value=[profile])

        mock_shortlist_repo = MagicMock()
        mock_shortlist_repo.get_by_user_and_date = AsyncMock(return_value=None)
        mock_shortlist_repo.create = AsyncMock()

        mock_health_repo = MagicMock()
        healthy = MagicMock(source_name="indeed_api")
        mock_health_repo.get_healthy_sources = AsyncMock(return_value=[healthy])

        mock_client = MagicMock()
        mock_client.search_jobs = AsyncMock(side_effect=Exception("timeout"))
        mock_registry = {"indeed_api": MagicMock(return_value=mock_client)}

        with (
            patch("src.repositories.profile_repository.ProfileRepository", return_value=mock_profile_repo),
            patch("src.repositories.job_shortlist_repository.JobShortlistRepository", return_value=mock_shortlist_repo),
            patch("src.repositories.data_source_health_repository.DataSourceHealthRepository", return_value=mock_health_repo),
            patch("src.integrations.job_source_clients.JOB_SOURCE_REGISTRY", mock_registry),
        ):
            from src.tasks.discovery_tasks import _generate_all_shortlists
            result = await _generate_all_shortlists()

        # Still generates (empty shortlist) even if source fails
        assert result["generated"] == 1


class TestCeleryTaskRegistration:
    def test_generate_task_registered(self):
        from src.tasks.discovery_tasks import generate_daily_shortlists
        assert generate_daily_shortlists.name == "tasks.batch.generate_daily_shortlists"

    def test_beat_schedule_includes_generation(self):
        from src.tasks.celery_app import celery_app
        schedule = celery_app.conf.beat_schedule
        assert "generate-daily-shortlists" in schedule
        assert schedule["generate-daily-shortlists"]["schedule"] == 86400.0
