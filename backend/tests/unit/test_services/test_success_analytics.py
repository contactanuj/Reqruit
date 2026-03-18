"""Tests for SuccessAnalyticsService — rate computations and breakdowns."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.db.documents.enums import OutcomeStatus
from src.services.success_analytics import SuccessAnalyticsService


_user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _tracker(
    outcome_status=OutcomeStatus.APPLIED,
    submission_method="linkedin",
    resume_strategy="keyword_focused",
    submitted_at=None,
):
    t = MagicMock()
    t.outcome_status = outcome_status
    t.submission_method = submission_method
    t.resume_strategy = resume_strategy
    t.submitted_at = submitted_at or datetime(2026, 3, 10, 9, 0)
    return t


def _make_service(trackers):
    repo = MagicMock()
    repo.get_for_user = AsyncMock(return_value=trackers)
    return SuccessAnalyticsService(repo)


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestGetSummary:
    async def test_sufficient_data(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.VIEWED, submitted_at=datetime(2026, 3, 10, 9, 0)),
            _tracker(OutcomeStatus.RESPONDED, submitted_at=datetime(2026, 3, 11, 14, 0)),
            _tracker(OutcomeStatus.INTERVIEW_SCHEDULED, submitted_at=datetime(2026, 3, 12, 10, 0)),
            _tracker(OutcomeStatus.REJECTED, submitted_at=datetime(2026, 3, 13, 16, 0)),
            _tracker(OutcomeStatus.GHOSTED, submitted_at=datetime(2026, 3, 14, 11, 0)),
        ]
        svc = _make_service(trackers)
        result = await svc.get_summary(_user_id)

        assert result.total_applications == 5
        assert result.data_sufficiency == "sufficient"
        assert result.message is None

    async def test_low_data(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.APPLIED),
            _tracker(OutcomeStatus.VIEWED),
        ]
        svc = _make_service(trackers)
        result = await svc.get_summary(_user_id)

        assert result.total_applications == 2
        assert result.data_sufficiency == "low"
        assert result.message is not None
        assert "Fewer than 5" in result.message

    async def test_empty(self) -> None:
        svc = _make_service([])
        result = await svc.get_summary(_user_id)

        assert result.total_applications == 0
        assert result.data_sufficiency == "low"
        assert result.response_rate.rate == 0.0
        assert result.view_rate.rate == 0.0
        assert result.interview_rate.rate == 0.0


# ---------------------------------------------------------------------------
# _compute_rates
# ---------------------------------------------------------------------------


class TestComputeRates:
    def test_cumulative_rates(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.VIEWED),
            _tracker(OutcomeStatus.RESPONDED),
            _tracker(OutcomeStatus.INTERVIEW_SCHEDULED),
            _tracker(OutcomeStatus.REJECTED),
            _tracker(OutcomeStatus.GHOSTED),
        ]
        svc = _make_service([])
        rates = svc._compute_rates(trackers)

        # viewed: VIEWED + RESPONDED + INTERVIEW = 3/5
        assert rates["view_rate"].count == 3
        assert rates["view_rate"].rate == 0.6
        # responded: RESPONDED + INTERVIEW = 2/5
        assert rates["response_rate"].count == 2
        assert rates["response_rate"].rate == 0.4
        # interview: INTERVIEW = 1/5
        assert rates["interview_rate"].count == 1
        assert rates["interview_rate"].rate == 0.2

    def test_empty_trackers(self) -> None:
        svc = _make_service([])
        rates = svc._compute_rates([])

        assert rates["view_rate"].rate == 0.0
        assert rates["response_rate"].rate == 0.0
        assert rates["interview_rate"].rate == 0.0

    def test_all_applied(self) -> None:
        trackers = [_tracker(OutcomeStatus.APPLIED) for _ in range(5)]
        svc = _make_service([])
        rates = svc._compute_rates(trackers)

        assert rates["view_rate"].count == 0
        assert rates["response_rate"].count == 0

    def test_offer_counts_as_all_milestones(self) -> None:
        trackers = [_tracker(OutcomeStatus.OFFER_RECEIVED)]
        svc = _make_service([])
        rates = svc._compute_rates(trackers)

        assert rates["view_rate"].count == 1
        assert rates["response_rate"].count == 1
        assert rates["interview_rate"].count == 1


# ---------------------------------------------------------------------------
# _breakdown_by_field
# ---------------------------------------------------------------------------


class TestBreakdownByField:
    def test_groups_by_submission_method(self) -> None:
        trackers = [
            _tracker(submission_method="linkedin"),
            _tracker(submission_method="linkedin"),
            _tracker(submission_method="email"),
        ]
        svc = _make_service([])
        result = svc._breakdown_by_field(trackers, "submission_method")

        methods = {b.value: b.count for b in result}
        assert methods["linkedin"] == 2
        assert methods["email"] == 1

    def test_groups_by_resume_strategy(self) -> None:
        trackers = [
            _tracker(resume_strategy="keyword_focused"),
            _tracker(resume_strategy="referral"),
            _tracker(resume_strategy="keyword_focused"),
        ]
        svc = _make_service([])
        result = svc._breakdown_by_field(trackers, "resume_strategy")

        strategies = {b.value: b.count for b in result}
        assert strategies["keyword_focused"] == 2
        assert strategies["referral"] == 1

    def test_empty_field_becomes_unknown(self) -> None:
        trackers = [_tracker(submission_method="")]
        svc = _make_service([])
        result = svc._breakdown_by_field(trackers, "submission_method")

        assert result[0].value == "unknown"

    def test_empty_trackers(self) -> None:
        svc = _make_service([])
        assert svc._breakdown_by_field([], "submission_method") == []

    def test_rates_sum_to_one(self) -> None:
        trackers = [
            _tracker(submission_method="linkedin"),
            _tracker(submission_method="email"),
            _tracker(submission_method="naukri"),
        ]
        svc = _make_service([])
        result = svc._breakdown_by_field(trackers, "submission_method")

        total_rate = sum(b.rate for b in result)
        assert abs(total_rate - 1.0) < 0.01


# ---------------------------------------------------------------------------
# _breakdown_by_day_of_week
# ---------------------------------------------------------------------------


class TestBreakdownByDayOfWeek:
    def test_groups_by_day(self) -> None:
        trackers = [
            _tracker(submitted_at=datetime(2026, 3, 9, 9, 0)),   # Monday
            _tracker(submitted_at=datetime(2026, 3, 10, 10, 0)),  # Tuesday
            _tracker(submitted_at=datetime(2026, 3, 9, 14, 0)),   # Monday
        ]
        svc = _make_service([])
        result = svc._breakdown_by_day_of_week(trackers)

        days = {b.bucket: b.count for b in result}
        assert days["Monday"] == 2
        assert days["Tuesday"] == 1

    def test_skips_none_submitted_at(self) -> None:
        trackers = [
            _tracker(submitted_at=datetime(2026, 3, 10, 9, 0)),
            _tracker(submitted_at=None),
        ]
        # Override the default submitted_at for the second tracker
        trackers[1].submitted_at = None
        svc = _make_service([])
        result = svc._breakdown_by_day_of_week(trackers)

        total = sum(b.count for b in result)
        assert total == 1


# ---------------------------------------------------------------------------
# _breakdown_by_time_of_day
# ---------------------------------------------------------------------------


class TestBreakdownByTimeOfDay:
    def test_groups_by_hour(self) -> None:
        trackers = [
            _tracker(submitted_at=datetime(2026, 3, 10, 9, 0)),
            _tracker(submitted_at=datetime(2026, 3, 11, 9, 30)),
            _tracker(submitted_at=datetime(2026, 3, 12, 14, 0)),
        ]
        svc = _make_service([])
        result = svc._breakdown_by_time_of_day(trackers)

        hours = {b.bucket: b.count for b in result}
        assert hours[9] == 2
        assert hours[14] == 1

    def test_skips_none_submitted_at(self) -> None:
        trackers = [_tracker(submitted_at=None)]
        trackers[0].submitted_at = None
        svc = _make_service([])
        result = svc._breakdown_by_time_of_day(trackers)

        assert result == []


# ---------------------------------------------------------------------------
# _assess_data_sufficiency
# ---------------------------------------------------------------------------


class TestAssessDataSufficiency:
    def test_sufficient(self) -> None:
        svc = _make_service([])
        assert svc._assess_data_sufficiency(5) == "sufficient"
        assert svc._assess_data_sufficiency(100) == "sufficient"

    def test_low(self) -> None:
        svc = _make_service([])
        assert svc._assess_data_sufficiency(0) == "low"
        assert svc._assess_data_sufficiency(4) == "low"
