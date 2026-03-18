"""Tests for /wellness/* endpoints."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient
from langchain_core.messages import AIMessage

from src.api.dependencies import get_current_user
from src.db.documents.user_activity import ActivityEntry, UserActivity


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


def _make_activity(**kwargs):
    defaults = {
        "actions": [],
        "total_xp": 0,
        "streak_count": 0,
        "freeze_count": 0,
        "current_league": "bronze",
        "week_start_xp": 0,
    }
    defaults.update(kwargs)
    mock = MagicMock(spec=UserActivity)
    for k, v in defaults.items():
        setattr(mock, k, v)
    mock.save = AsyncMock()
    return mock


def _make_entry(action_type, xp=5):
    return ActivityEntry(
        action_type=action_type,
        xp_earned=xp,
        timestamp=datetime.now(UTC),
    )


class TestWeeklyReview:
    async def test_200_with_sufficient_data(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        entries = [_make_entry("application_submitted", 30) for _ in range(6)]
        activity = _make_activity(actions=entries, total_xp=180)

        agent_response = {
            "summary": "Good week",
            "tactical_adjustments": ["Try startups"],
            "next_week_goals": ["Goal 1", "Goal 2", "Goal 3"],
            "encouragement": "Keep going!",
        }

        with (
            patch("src.api.routes.wellness.UserActivityRepository") as MockRepo,
            patch("src.agents.weekly_review.weekly_review_agent") as mock_agent,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[activity])
            mock_agent.return_value = agent_response

            response = await client.post("/wellness/weekly-review")

        assert response.status_code == 200
        data = response.json()
        assert data["data_driven"] is True
        assert data["metrics"]["applications_count"] == 6
        assert len(data["next_week_goals"]) == 3

    async def test_200_with_insufficient_data(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        entries = [_make_entry("application_submitted", 30) for _ in range(2)]
        activity = _make_activity(actions=entries, total_xp=60)

        agent_response = {
            "summary": "Keep trying",
            "tactical_adjustments": ["Apply more"],
            "next_week_goals": ["Goal 1", "Goal 2", "Goal 3"],
            "encouragement": "Every step counts!",
        }

        with (
            patch("src.api.routes.wellness.UserActivityRepository") as MockRepo,
            patch("src.agents.weekly_review.weekly_review_agent") as mock_agent,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[activity])
            mock_agent.return_value = agent_response

            response = await client.post("/wellness/weekly-review")

        assert response.status_code == 200
        data = response.json()
        assert data["data_driven"] is False
        assert data["comparison_to_last_week"] is None

    async def test_200_with_inflection_warning(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        # Current: 10 apps, 1 response (10% rate)
        curr_entries = (
            [_make_entry("application_submitted", 30) for _ in range(10)]
            + [_make_entry("mock_interview_completed", 50)]
        )
        curr_activity = _make_activity(actions=curr_entries, total_xp=350)

        # Previous: 10 apps, 5 responses (50% rate) — >30% decline
        prev_entries = (
            [_make_entry("application_submitted", 30) for _ in range(10)]
            + [_make_entry("mock_interview_completed", 50) for _ in range(5)]
        )
        prev_activity = _make_activity(actions=prev_entries, total_xp=550)

        agent_response = {
            "summary": "Concerning trends",
            "tactical_adjustments": ["Pivot strategy"],
            "next_week_goals": ["G1", "G2", "G3"],
            "encouragement": "Adapt and overcome!",
        }

        with (
            patch("src.api.routes.wellness.UserActivityRepository") as MockRepo,
            patch("src.agents.weekly_review.weekly_review_agent") as mock_agent,
        ):
            mock_repo = MockRepo.return_value
            # First call returns current week, second returns previous week
            mock_repo.get_history = AsyncMock(side_effect=[[curr_activity], [prev_activity]])
            mock_agent.return_value = agent_response

            response = await client.post("/wellness/weekly-review")

        assert response.status_code == 200
        data = response.json()
        assert data["inflection_warning"] is not None
        assert "response rate" in data["inflection_warning"].lower()

    async def test_200_agent_failure_returns_fallback(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with (
            patch("src.api.routes.wellness.UserActivityRepository") as MockRepo,
            patch("src.agents.weekly_review.weekly_review_agent") as mock_agent,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])
            mock_agent.side_effect = Exception("LLM down")

            response = await client.post("/wellness/weekly-review")

        assert response.status_code == 200
        data = response.json()
        assert data["data_driven"] is False
        assert len(data["next_week_goals"]) == 3

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/wellness/weekly-review")
        assert response.status_code in (401, 403)


class TestMoraleDashboard:
    async def test_200_returns_all_4_indicators(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            response = await client.get("/wellness/morale")

        assert response.status_code == 200
        data = response.json()
        assert "response_rate_trend" in data
        assert "ghosting_frequency" in data
        assert "ghosting_percentage" in data
        assert "interview_conversion_rate" in data
        assert "time_since_last_positive_signal" in data

    async def test_200_includes_burnout_warning_when_triggered(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        now = datetime.now(UTC)
        base = now.replace(hour=10, minute=0, second=0, microsecond=0)
        burst_actions = [
            ActivityEntry(
                action_type="application_submitted",
                xp_earned=30,
                timestamp=base + __import__("datetime").timedelta(minutes=i * 5),
            )
            for i in range(12)
        ]
        today_activity = _make_activity(actions=burst_actions, total_xp=360)
        today_activity.date = now

        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[today_activity])

            response = await client.get("/wellness/morale")

        assert response.status_code == 200
        data = response.json()
        assert data["burnout_warning"] is not None
        assert "signals" in data["burnout_warning"]
        assert "severity" in data["burnout_warning"]

    async def test_200_includes_intervention_when_negative_7_days(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        # Empty data → conv=0 (<10%), days_since_positive=90 (>14d) → 2 negative indicators
        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            response = await client.get("/wellness/morale")

        assert response.status_code == 200
        data = response.json()
        assert data["intervention"] is not None
        assert len(data["intervention"]["triggered_indicators"]) >= 2
        assert data["intervention"]["consecutive_negative_days"] == 7

    async def test_401_morale_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/wellness/morale")
        assert response.status_code in (401, 403)


class TestROIPredict:
    async def test_200_with_jd_text(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            response = await client.post(
                "/wellness/roi-predict",
                json={"jd_text": "Senior Python developer needed"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "probability_of_response" in data
        assert "classification" in data
        assert "contributing_factors" in data
        assert data["classification"] in ("HIGH_ROI", "WORTH_A_SHOT", "SKIP_IT")

    async def test_200_with_job_id(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with (
            patch("src.api.routes.wellness.UserActivityRepository") as MockRepo,
            patch("src.repositories.job_repository.JobRepository") as MockJobRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            mock_job_repo = MockJobRepo.return_value
            mock_job_repo.find_by_id = AsyncMock(return_value=None)

            response = await client.post(
                "/wellness/roi-predict",
                json={"job_id": "aaaaaaaaaaaaaaaaaaaaaaaa"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["contributing_factors"]["user_fit_score"] == 0.5  # default

    async def test_422_with_neither(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post("/wellness/roi-predict", json={})

        assert response.status_code == 422

    async def test_response_includes_all_factors(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            response = await client.post(
                "/wellness/roi-predict",
                json={"jd_text": "Software engineer"},
            )

        data = response.json()
        factors = data["contributing_factors"]
        assert "company_response_rate" in factors
        assert "role_competition_level" in factors
        assert "user_fit_score" in factors
        assert "submission_timing" in factors

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/wellness/roi-predict", json={"jd_text": "test"})
        assert response.status_code in (401, 403)


class TestSchedule:
    async def test_200_with_defaults(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            response = await client.post("/wellness/schedule", json={})

        assert response.status_code == 200
        data = response.json()
        assert len(data["days"]) == 7
        assert "season_boost" in data
        assert "burnout_adjusted" in data
        assert "notes" in data

    async def test_200_with_custom_limits(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            response = await client.post("/wellness/schedule", json={
                "daily_app_limit": 3,
                "available_hours_per_day": 4.0,
                "preferred_rest_days": ["Saturday", "Sunday"],
            })

        assert response.status_code == 200
        data = response.json()
        rest_days = [d for d in data["days"] if d["is_rest_day"]]
        assert len(rest_days) == 2

    async def test_includes_burnout_adjusted_flag(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        # Empty data triggers no burnout (no activity)
        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            response = await client.post("/wellness/schedule", json={})

        data = response.json()
        assert isinstance(data["burnout_adjusted"], bool)

    async def test_includes_season_boost_flag(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.wellness.UserActivityRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_history = AsyncMock(return_value=[])

            response = await client.post("/wellness/schedule", json={})

        data = response.json()
        assert isinstance(data["season_boost"], bool)

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/wellness/schedule", json={})
        assert response.status_code in (401, 403)
