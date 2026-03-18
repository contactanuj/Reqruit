"""Tests for milestone progress tracking and reminder generation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from src.db.documents.onboarding_plan import Milestone, OnboardingPlan
from src.services.milestone_tracker import (
    calculate_progress_pct,
    generate_milestone_reminder,
    generate_overdue_reminder,
    generate_reminders,
    get_overdue_milestones,
    get_upcoming_milestones,
    update_milestone_status,
)


def _make_plan(milestones=None, start_date=None):
    """Helper to create a minimal OnboardingPlan for testing."""
    plan = OnboardingPlan(
        user_id="aaaaaaaaaaaaaaaaaaaaaaaa",
        company_name="Test Corp",
        role_title="Engineer",
        start_date=start_date,
        milestones=milestones or [],
    )
    return plan


class TestCalculateProgressPct:
    def test_empty_milestones(self):
        assert calculate_progress_pct([]) == 0.0

    def test_none_completed(self):
        milestones = [
            Milestone(title="A", target_day=1),
            Milestone(title="B", target_day=30),
        ]
        assert calculate_progress_pct(milestones) == 0.0

    def test_some_completed(self):
        milestones = [
            Milestone(title="A", target_day=1, completed=True),
            Milestone(title="B", target_day=30),
            Milestone(title="C", target_day=60, completed=True),
        ]
        # 2/3 = 66.7%
        assert calculate_progress_pct(milestones) == 66.7

    def test_all_completed(self):
        milestones = [
            Milestone(title="A", target_day=1, completed=True),
            Milestone(title="B", target_day=30, completed=True),
        ]
        assert calculate_progress_pct(milestones) == 100.0


class TestUpdateMilestoneStatus:
    def test_mark_completed(self):
        plan = _make_plan(milestones=[
            Milestone(title="A", target_day=1),
            Milestone(title="B", target_day=30),
            Milestone(title="C", target_day=60),
        ])
        plan = update_milestone_status(plan, 0, completed=True)
        assert plan.milestones[0].completed is True
        assert plan.milestones[0].completed_at is not None
        assert plan.progress_pct == 33.3

    def test_mark_incomplete(self):
        plan = _make_plan(milestones=[
            Milestone(title="A", target_day=1, completed=True, completed_at=datetime.now(UTC)),
        ])
        plan = update_milestone_status(plan, 0, completed=False)
        assert plan.milestones[0].completed is False
        assert plan.milestones[0].completed_at is None
        assert plan.progress_pct == 0.0

    def test_index_out_of_range(self):
        plan = _make_plan(milestones=[Milestone(title="A", target_day=1)])
        try:
            update_milestone_status(plan, 5, completed=True)
            assert False, "Expected IndexError"
        except IndexError:
            pass

    def test_progress_recalculated(self):
        plan = _make_plan(milestones=[
            Milestone(title="A", target_day=1),
            Milestone(title="B", target_day=30),
            Milestone(title="C", target_day=60),
            Milestone(title="D", target_day=90),
        ])
        plan = update_milestone_status(plan, 0, completed=True)
        assert plan.progress_pct == 25.0
        plan = update_milestone_status(plan, 1, completed=True)
        assert plan.progress_pct == 50.0


class TestGetOverdueMilestones:
    def test_no_start_date_returns_empty(self):
        plan = _make_plan(milestones=[Milestone(title="A", target_day=1)])
        assert get_overdue_milestones(plan) == []

    def test_completed_milestones_not_overdue(self):
        start = datetime.now(UTC) - timedelta(days=30)
        plan = _make_plan(
            milestones=[Milestone(title="A", target_day=1, completed=True)],
            start_date=start,
        )
        assert get_overdue_milestones(plan) == []

    def test_detects_overdue_milestone(self):
        start = datetime.now(UTC) - timedelta(days=30)
        plan = _make_plan(
            milestones=[
                Milestone(title="Meet team", target_day=1),  # 29 days overdue
                Milestone(title="Ship code", target_day=60),  # not yet due
            ],
            start_date=start,
        )
        overdue = get_overdue_milestones(plan)
        assert len(overdue) == 1
        assert overdue[0].title == "Meet team"
        assert overdue[0].days_overdue >= 29

    def test_catch_up_suggestion_present(self):
        start = datetime.now(UTC) - timedelta(days=30)
        plan = _make_plan(
            milestones=[Milestone(title="A", target_day=1)],
            start_date=start,
        )
        overdue = get_overdue_milestones(plan)
        assert overdue[0].catch_up_suggestion != ""


class TestGetUpcomingMilestones:
    def test_no_start_date_returns_empty(self):
        plan = _make_plan(milestones=[Milestone(title="A", target_day=1)])
        assert get_upcoming_milestones(plan) == []

    def test_finds_upcoming_milestone(self):
        # Start date such that target_day=5 is 2 days from now
        start = datetime.now(UTC) - timedelta(days=3)
        plan = _make_plan(
            milestones=[Milestone(title="Ship first code change", target_day=5)],
            start_date=start,
        )
        upcoming = get_upcoming_milestones(plan, days_ahead=7)
        assert len(upcoming) == 1
        assert upcoming[0].title == "Ship first code change"
        assert upcoming[0].days_until == 2

    def test_completed_milestones_excluded(self):
        start = datetime.now(UTC) - timedelta(days=3)
        plan = _make_plan(
            milestones=[Milestone(title="A", target_day=5, completed=True)],
            start_date=start,
        )
        assert get_upcoming_milestones(plan, days_ahead=7) == []

    def test_far_future_milestones_excluded(self):
        start = datetime.now(UTC)
        plan = _make_plan(
            milestones=[Milestone(title="A", target_day=60)],
            start_date=start,
        )
        assert get_upcoming_milestones(plan, days_ahead=7) == []


class TestReminders:
    def test_milestone_reminder_text(self):
        text = generate_milestone_reminder("Ship first code change", 7, 3)
        assert "Day 7" in text
        assert "Ship first code change" in text
        assert "3 days" in text
        # Keyword "ship" should trigger contextual question
        assert "first issue" in text

    def test_overdue_reminder_text(self):
        text = generate_overdue_reminder("Meet team", 1, 5)
        assert "Day 1" in text
        assert "was due 5 days ago" in text

    def test_reminder_contextual_question_1on1(self):
        text = generate_milestone_reminder("Set up 1:1 with skip-level", 14, 3)
        assert "calendar invite" in text

    def test_reminder_triggers_at_3_days(self):
        start = datetime.now(UTC) - timedelta(days=4)
        plan = _make_plan(
            milestones=[Milestone(title="Ship code", target_day=7)],
            start_date=start,
        )
        reminders = generate_reminders(plan, reminder_days=3)
        assert len(reminders) == 1
        assert "Ship code" in reminders[0]

    def test_generate_reminders_includes_overdue(self):
        start = datetime.now(UTC) - timedelta(days=30)
        plan = _make_plan(
            milestones=[Milestone(title="Meet team", target_day=1)],
            start_date=start,
        )
        reminders = generate_reminders(plan)
        assert len(reminders) == 1
        assert "was due" in reminders[0]
