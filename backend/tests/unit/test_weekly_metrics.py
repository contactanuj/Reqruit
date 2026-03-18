"""Tests for weekly metrics aggregation and inflection detection."""

from unittest.mock import MagicMock

from src.services.streak_service import (
    INFLECTION_THRESHOLD,
    WeeklyMetrics,
    aggregate_weekly_metrics,
    compute_week_comparison,
    detect_strategy_inflection,
    is_data_sufficient,
)


def _make_entry(action_type: str, xp: int = 5):
    entry = MagicMock()
    entry.action_type = action_type
    entry.xp_earned = xp
    return entry


def _make_activity(actions_list, total_xp=0):
    mock = MagicMock()
    mock.actions = actions_list
    mock.total_xp = total_xp
    return mock


class TestAggregateWeeklyMetrics:
    def test_empty_activities(self):
        result = aggregate_weekly_metrics([])
        assert result.applications_count == 0
        assert result.xp_earned == 0
        assert result.action_breakdown == {}

    def test_counts_applications(self):
        activities = [
            _make_activity([_make_entry("application_submitted"), _make_entry("application_submitted")], total_xp=60),
            _make_activity([_make_entry("job_saved")], total_xp=5),
        ]
        result = aggregate_weekly_metrics(activities)
        assert result.applications_count == 2
        assert result.xp_earned == 65
        assert result.action_breakdown["application_submitted"] == 2
        assert result.action_breakdown["job_saved"] == 1

    def test_counts_interviews(self):
        activities = [_make_activity([_make_entry("interview_prepped")], total_xp=25)]
        result = aggregate_weekly_metrics(activities)
        assert result.interviews_count == 1


class TestComputeWeekComparison:
    def test_positive_change(self):
        current = WeeklyMetrics(applications_count=10, xp_earned=200)
        previous = WeeklyMetrics(applications_count=5, xp_earned=100)
        result = compute_week_comparison(current, previous)
        assert result.applications_change_pct == 100.0
        assert result.xp_change_pct == 100.0

    def test_negative_change(self):
        current = WeeklyMetrics(applications_count=3, xp_earned=50)
        previous = WeeklyMetrics(applications_count=10, xp_earned=200)
        result = compute_week_comparison(current, previous)
        assert result.applications_change_pct == -70.0

    def test_zero_previous(self):
        current = WeeklyMetrics(applications_count=5)
        previous = WeeklyMetrics(applications_count=0)
        result = compute_week_comparison(current, previous)
        assert result.applications_change_pct == 100.0

    def test_both_zero(self):
        current = WeeklyMetrics(applications_count=0)
        previous = WeeklyMetrics(applications_count=0)
        result = compute_week_comparison(current, previous)
        assert result.applications_change_pct == 0.0


class TestDetectStrategyInflection:
    def test_no_inflection_when_stable(self):
        current = WeeklyMetrics(applications_count=10, responses_count=2)
        previous = WeeklyMetrics(applications_count=10, responses_count=2)
        result = detect_strategy_inflection(current, previous)
        assert result is None

    def test_inflection_at_31_pct_decline(self):
        # prev rate: 2/10 = 20%, curr rate: 1/10 = 10%, decline = 50%
        current = WeeklyMetrics(applications_count=10, responses_count=1)
        previous = WeeklyMetrics(applications_count=10, responses_count=2)
        result = detect_strategy_inflection(current, previous)
        assert result is not None
        assert result.decline_pct == 50.0
        assert "response rate dropped" in result.pivot_suggestion.lower()

    def test_no_inflection_below_30_pct(self):
        # prev rate: 4/20 = 20%, curr rate: 3/20 = 15%, decline = 25%
        current = WeeklyMetrics(applications_count=20, responses_count=3)
        previous = WeeklyMetrics(applications_count=20, responses_count=4)
        result = detect_strategy_inflection(current, previous)
        assert result is None

    def test_inflection_at_just_over_30_pct(self):
        # prev rate: 10/10 = 100%, curr rate: 6/10 = 60%, decline = 40%
        current = WeeklyMetrics(applications_count=10, responses_count=6)
        previous = WeeklyMetrics(applications_count=10, responses_count=10)
        result = detect_strategy_inflection(current, previous)
        assert result is not None

    def test_insufficient_current_data(self):
        current = WeeklyMetrics(applications_count=4, responses_count=0)
        previous = WeeklyMetrics(applications_count=10, responses_count=5)
        result = detect_strategy_inflection(current, previous)
        assert result is None

    def test_insufficient_previous_data(self):
        current = WeeklyMetrics(applications_count=10, responses_count=1)
        previous = WeeklyMetrics(applications_count=3, responses_count=2)
        result = detect_strategy_inflection(current, previous)
        assert result is None

    def test_zero_previous_rate(self):
        current = WeeklyMetrics(applications_count=10, responses_count=3)
        previous = WeeklyMetrics(applications_count=10, responses_count=0)
        result = detect_strategy_inflection(current, previous)
        assert result is None


class TestIsDataSufficient:
    def test_4_apps_insufficient(self):
        assert is_data_sufficient(WeeklyMetrics(applications_count=4)) is False

    def test_5_apps_sufficient(self):
        assert is_data_sufficient(WeeklyMetrics(applications_count=5)) is True

    def test_0_apps_insufficient(self):
        assert is_data_sufficient(WeeklyMetrics(applications_count=0)) is False
