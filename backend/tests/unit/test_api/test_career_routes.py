"""Tests for /career/* endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user
from src.db.documents.onboarding_plan import (
    JoiningPrepItem,
    Milestone,
    OnboardingPlan,
    RelationshipTarget,
)


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


class TestCreateOnboardingPlan:
    async def test_202_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.workflows.graphs.onboarding.get_onboarding_graph") as mock_graph_fn:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={})
            mock_graph_fn.return_value = mock_graph

            response = await client.post("/career/onboarding/plan", json={
                "company_name": "Acme Corp",
                "role_title": "Senior Engineer",
                "start_date": "2026-04-01",
            })

        assert response.status_code == 202
        data = response.json()
        assert "thread_id" in data
        assert "message" in data

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/career/onboarding/plan", json={
            "company_name": "Test",
            "role_title": "Dev",
            "start_date": "2026-04-01",
        })
        assert response.status_code in (401, 403)


class TestGetOnboardingPlan:
    async def test_200_returns_plan(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_plan = MagicMock(spec=OnboardingPlan)
        mock_plan.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        mock_plan.company_name = "Acme Corp"
        mock_plan.role_title = "Senior Engineer"
        mock_plan.milestones = [
            Milestone(title="Meet team", target_day=1, description="Intro meetings"),
        ]
        mock_plan.progress_pct = 0.0
        mock_plan.skill_gaps = []
        mock_plan.relationship_targets = [
            RelationshipTarget(
                role="Direct Manager",
                description="Primary reporting",
                conversation_starters=["What are priorities?"],
                optimal_timing="Week 1",
            ),
        ]
        mock_plan.joining_prep = [
            JoiningPrepItem(
                category="PF Transfer",
                title="PF Transfer Guidance",
                description="Transfer PF",
                checklist=["Link UAN"],
            ),
        ]

        with patch("src.api.routes.career.OnboardingPlanRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_active = AsyncMock(return_value=mock_plan)

            response = await client.get("/career/onboarding/plan")

        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Acme Corp"
        assert len(data["milestones"]) == 1
        assert len(data["relationship_targets"]) == 1
        assert data["relationship_targets"][0]["role"] == "Direct Manager"
        assert len(data["joining_prep"]) == 1
        assert data["joining_prep"][0]["category"] == "PF Transfer"

    async def test_404_when_no_plan(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.career.OnboardingPlanRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_active = AsyncMock(return_value=None)

            response = await client.get("/career/onboarding/plan")

        assert response.status_code == 404

    async def test_plan_response_empty_joining_prep_for_unsupported_locale(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_plan = MagicMock(spec=OnboardingPlan)
        mock_plan.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        mock_plan.company_name = "Acme Corp"
        mock_plan.role_title = "Engineer"
        mock_plan.milestones = []
        mock_plan.progress_pct = 0.0
        mock_plan.skill_gaps = []
        mock_plan.relationship_targets = []
        mock_plan.joining_prep = []

        with patch("src.api.routes.career.OnboardingPlanRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_active = AsyncMock(return_value=mock_plan)

            response = await client.get("/career/onboarding/plan")

        assert response.status_code == 200
        data = response.json()
        assert data["joining_prep"] == []
        assert data["relationship_targets"] == []

    async def test_create_plan_with_locale(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.workflows.graphs.onboarding.get_onboarding_graph") as mock_graph_fn:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={})
            mock_graph_fn.return_value = mock_graph

            response = await client.post("/career/onboarding/plan", json={
                "company_name": "Acme Corp",
                "role_title": "Senior Engineer",
                "start_date": "2026-04-01",
                "locale": "IN",
            })

        assert response.status_code == 202

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/career/onboarding/plan")
        assert response.status_code in (401, 403)


class TestCoachingEndpoint:
    async def test_returns_coaching_response(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_result = {
            "coaching_response": '{"whats_happening":"Normal adjustment","how_to_respond":"Schedule a 1:1","conversation_scripts":["I appreciate..."],"when_to_escalate":"If it continues"}',
        }

        with patch("src.api.routes.career.onboarding_coach_agent", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post("/career/onboarding/coach", json={
                "situation_description": "My manager gives vague feedback and I don't know what to improve",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["whats_happening"] == "Normal adjustment"
        assert len(data["conversation_scripts"]) == 1

    async def test_coaching_increments_session_count(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_plan = MagicMock(spec=OnboardingPlan)
        mock_plan.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        mock_plan.company_name = "Acme Corp"
        mock_plan.role_title = "Engineer"
        mock_plan.milestones = []
        mock_plan.coaching_session_count = 2

        mock_result = {
            "coaching_response": '{"whats_happening":"x","how_to_respond":"y","conversation_scripts":[],"when_to_escalate":"z"}',
        }

        with (
            patch("src.api.routes.career.OnboardingPlanRepository") as MockRepo,
            patch("src.api.routes.career.onboarding_coach_agent", new_callable=AsyncMock, return_value=mock_result),
        ):
            mock_repo = MockRepo.return_value
            # First call: get plan for context + increment
            # Second call: get plan for session count
            mock_plan_after = MagicMock(spec=OnboardingPlan)
            mock_plan_after.coaching_session_count = 3
            mock_repo.get_by_id_and_user = AsyncMock(side_effect=[mock_plan, mock_plan_after])
            mock_repo.update = AsyncMock()

            response = await client.post("/career/onboarding/coach", json={
                "situation_description": "Need help with team dynamics and building rapport",
                "plan_id": "bbbbbbbbbbbbbbbbbbbbbbbb",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["session_count"] == 3

    async def test_situation_too_short_rejected(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post("/career/onboarding/coach", json={
            "situation_description": "Help",
        })
        assert response.status_code == 422

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/career/onboarding/coach", json={
            "situation_description": "My manager gives vague feedback and I need help",
        })
        assert response.status_code in (401, 403)


class TestMilestoneUpdate:
    async def test_patch_milestone_completed(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_plan = MagicMock(spec=OnboardingPlan)
        mock_plan.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        mock_plan.milestones = [
            Milestone(title="Meet team", target_day=1, description="Intro"),
            Milestone(title="Ship code", target_day=7, description="First PR"),
        ]
        mock_plan.progress_pct = 0.0

        with patch("src.api.routes.career.OnboardingPlanRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_plan)
            mock_repo.update = AsyncMock()

            response = await client.patch(
                "/career/onboarding/plan/bbbbbbbbbbbbbbbbbbbbbbbb/milestone/0",
                json={"status": "completed"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["progress_pct"] == 50.0
        assert data["milestone"]["completed"] is True

    async def test_patch_other_users_plan_returns_404(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.career.OnboardingPlanRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

            response = await client.patch(
                "/career/onboarding/plan/bbbbbbbbbbbbbbbbbbbbbbbb/milestone/0",
                json={"status": "completed"},
            )

        assert response.status_code == 404

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.patch(
            "/career/onboarding/plan/bbbbbbbbbbbbbbbbbbbbbbbb/milestone/0",
            json={"status": "completed"},
        )
        assert response.status_code in (401, 403)


class TestGetPlanDetail:
    async def test_returns_detail_with_overdue_and_reminders(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_plan = MagicMock(spec=OnboardingPlan)
        mock_plan.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        mock_plan.company_name = "Acme Corp"
        mock_plan.role_title = "Engineer"
        mock_plan.milestones = [
            Milestone(title="Meet team", target_day=1, description="Intro"),
        ]
        mock_plan.progress_pct = 0.0
        mock_plan.relationship_targets = []
        mock_plan.joining_prep = []
        mock_plan.start_date = None  # No start date => no overdue

        with patch("src.api.routes.career.OnboardingPlanRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_plan)

            response = await client.get(
                "/career/onboarding/plan/bbbbbbbbbbbbbbbbbbbbbbbb"
            )

        assert response.status_code == 200
        data = response.json()
        assert "overdue_milestones" in data
        assert "upcoming_milestones" in data
        assert "reminders" in data

    async def test_404_for_nonexistent_plan(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.career.OnboardingPlanRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

            response = await client.get(
                "/career/onboarding/plan/bbbbbbbbbbbbbbbbbbbbbbbb"
            )

        assert response.status_code == 404
