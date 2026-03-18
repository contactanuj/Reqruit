"""
Milestone tracker — deterministic progress tracking and reminder generation.

Pure-Python calculations for milestone completion percentage, overdue detection,
upcoming milestones, and contextual reminders.
"""

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from src.db.documents.onboarding_plan import Milestone, OnboardingPlan


class OverdueMilestone(BaseModel):
    """A milestone that is past its target date and not yet completed."""

    title: str
    target_day: int
    days_overdue: int
    catch_up_suggestion: str


class UpcomingMilestone(BaseModel):
    """A milestone approaching its target date."""

    title: str
    target_day: int
    days_until: int


def calculate_progress_pct(milestones: list[Milestone]) -> float:
    """Calculate completion percentage from milestones list."""
    if not milestones:
        return 0.0
    completed = sum(1 for m in milestones if m.completed)
    return round(completed / len(milestones) * 100, 1)


def update_milestone_status(
    plan: OnboardingPlan, milestone_index: int, completed: bool
) -> OnboardingPlan:
    """Mark a milestone as completed/incomplete and recalculate progress."""
    if milestone_index < 0 or milestone_index >= len(plan.milestones):
        raise IndexError(f"Milestone index {milestone_index} out of range")

    milestone = plan.milestones[milestone_index]
    milestone.completed = completed
    milestone.completed_at = datetime.now(UTC) if completed else None
    plan.progress_pct = calculate_progress_pct(plan.milestones)
    return plan


def get_overdue_milestones(plan: OnboardingPlan) -> list[OverdueMilestone]:
    """Find milestones past their target date that are not completed."""
    if not plan.start_date:
        return []

    today = datetime.now(UTC).date()
    overdue = []

    for m in plan.milestones:
        if m.completed:
            continue
        expected_date = (plan.start_date + timedelta(days=m.target_day)).date()
        if today > expected_date:
            days_overdue = (today - expected_date).days
            suggestion = _catch_up_suggestion(m.title, days_overdue)
            overdue.append(OverdueMilestone(
                title=m.title,
                target_day=m.target_day,
                days_overdue=days_overdue,
                catch_up_suggestion=suggestion,
            ))

    return overdue


def get_upcoming_milestones(
    plan: OnboardingPlan, days_ahead: int = 7
) -> list[UpcomingMilestone]:
    """Find milestones within the next N days."""
    if not plan.start_date:
        return []

    today = datetime.now(UTC).date()
    upcoming = []

    for m in plan.milestones:
        if m.completed:
            continue
        expected_date = (plan.start_date + timedelta(days=m.target_day)).date()
        days_until = (expected_date - today).days
        if 0 <= days_until <= days_ahead:
            upcoming.append(UpcomingMilestone(
                title=m.title,
                target_day=m.target_day,
                days_until=days_until,
            ))

    return upcoming


def generate_milestone_reminder(title: str, target_day: int, days_until: int) -> str:
    """Generate a contextual reminder for an upcoming milestone."""
    question = _contextual_question(title)
    return (
        f"Day {target_day} milestone: '{title}' is in {days_until} days. "
        f"{question}"
    )


def generate_overdue_reminder(title: str, target_day: int, days_overdue: int) -> str:
    """Generate a reminder for an overdue milestone."""
    suggestion = _catch_up_suggestion(title, days_overdue)
    return (
        f"Day {target_day} milestone: '{title}' was due {days_overdue} days ago. "
        f"Here's how to catch up: {suggestion}"
    )


def generate_reminders(plan: OnboardingPlan, reminder_days: int = 3) -> list[str]:
    """Generate all active reminders for a plan (upcoming + overdue)."""
    reminders = []

    for m in get_upcoming_milestones(plan, days_ahead=reminder_days):
        reminders.append(generate_milestone_reminder(m.title, m.target_day, m.days_until))

    for m in get_overdue_milestones(plan):
        reminders.append(generate_overdue_reminder(m.title, m.target_day, m.days_overdue))

    return reminders


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_CONTEXTUAL_QUESTIONS: list[tuple[str, str]] = [
    ("ship", "Have you identified a good first issue?"),
    ("code", "Have you identified a good first issue?"),
    ("1:1", "Have you sent the calendar invite?"),
    ("meet", "Have you sent the calendar invite?"),
    ("review", "Have you reviewed the team's recent PRs?"),
    ("setup", "Is your development environment fully configured?"),
    ("mentor", "Have you identified a mentor or buddy?"),
]


def _contextual_question(title: str) -> str:
    """Return a contextual question based on milestone title keywords."""
    title_lower = title.lower()
    for keyword, question in _CONTEXTUAL_QUESTIONS:
        if keyword in title_lower:
            return question
    return "Are you on track?"


def _catch_up_suggestion(title: str, days_overdue: int) -> str:
    """Generate a catch-up suggestion for an overdue milestone."""
    if days_overdue > 14:
        return f"Consider breaking '{title}' into smaller steps and discuss with your manager."
    if days_overdue > 7:
        return f"Prioritize '{title}' this week — block dedicated time on your calendar."
    return f"'{title}' is slightly overdue — schedule time today to make progress."
