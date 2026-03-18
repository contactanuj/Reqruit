"""Tests for OnboardingPlan document model."""

from datetime import UTC, datetime

from src.db.documents.onboarding_plan import Milestone, OnboardingPlan


class TestMilestone:
    def test_creation(self):
        m = Milestone(title="Meet team", target_day=1, description="Intro meetings")
        assert m.title == "Meet team"
        assert m.target_day == 1
        assert m.completed is False
        assert m.completed_at is None

    def test_completed_milestone(self):
        now = datetime.now(UTC)
        m = Milestone(title="Ship code", target_day=7, completed=True, completed_at=now)
        assert m.completed is True
        assert m.completed_at == now


class TestOnboardingPlanDocument:
    def test_collection_name(self):
        assert OnboardingPlan.Settings.name == "onboarding_plans"

    def test_default_values(self):
        plan = OnboardingPlan(
            user_id="aaaaaaaaaaaaaaaaaaaaaaaa",
            company_name="Acme Corp",
        )
        assert plan.progress_pct == 0.0
        assert plan.milestones == []
        assert plan.coaching_session_count == 0
        assert plan.skill_gaps == []
        assert plan.role_title == ""
        assert plan.jd_text is None

    def test_with_milestones(self):
        milestones = [
            Milestone(title="Meet team", target_day=1),
            Milestone(title="Ship code", target_day=7),
            Milestone(title="Own project", target_day=45),
        ]
        plan = OnboardingPlan(
            user_id="aaaaaaaaaaaaaaaaaaaaaaaa",
            company_name="Acme Corp",
            role_title="Senior Engineer",
            milestones=milestones,
        )
        assert len(plan.milestones) == 3
        assert plan.milestones[0].target_day == 1
        assert plan.milestones[2].target_day == 45


class TestOnboardingPlanInAllModels:
    def test_registered_in_all_models(self):
        from src.db.documents import ALL_DOCUMENT_MODELS
        assert OnboardingPlan in ALL_DOCUMENT_MODELS

    def test_document_count(self):
        from src.db.documents import ALL_DOCUMENT_MODELS
        assert len(ALL_DOCUMENT_MODELS) == 38
        assert len(set(ALL_DOCUMENT_MODELS)) == 38
