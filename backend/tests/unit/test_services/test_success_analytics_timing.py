"""Tests for timing analysis, strategy comparison, and confidence level."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.db.documents.enums import OutcomeStatus
from src.services.success_analytics import SuccessAnalyticsService, confidence_level


_user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _tracker(
    outcome_status=OutcomeStatus.APPLIED,
    submission_method="linkedin",
    resume_strategy="keyword_focused",
    cover_letter_strategy="",
    submitted_at=None,
):
    t = MagicMock()
    t.outcome_status = outcome_status
    t.submission_method = submission_method
    t.resume_strategy = resume_strategy
    t.cover_letter_strategy = cover_letter_strategy
    t.submitted_at = submitted_at
    return t


def _make_service(trackers):
    repo = MagicMock()
    repo.get_for_user = AsyncMock(return_value=trackers)
    return SuccessAnalyticsService(repo)


# ---------------------------------------------------------------------------
# confidence_level
# ---------------------------------------------------------------------------


class TestConfidenceLevel:
    def test_insufficient(self) -> None:
        assert confidence_level(0) == "insufficient"
        assert confidence_level(4) == "insufficient"

    def test_low(self) -> None:
        assert confidence_level(5) == "low"
        assert confidence_level(14) == "low"

    def test_moderate(self) -> None:
        assert confidence_level(15) == "moderate"
        assert confidence_level(29) == "moderate"

    def test_high(self) -> None:
        assert confidence_level(30) == "high"
        assert confidence_level(100) == "high"


# ---------------------------------------------------------------------------
# get_timing_analysis
# ---------------------------------------------------------------------------


class TestGetTimingAnalysis:
    async def test_groups_by_day_and_time(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, submitted_at=datetime(2026, 3, 9, 9, 0)),    # Monday morning
            _tracker(OutcomeStatus.APPLIED, submitted_at=datetime(2026, 3, 9, 10, 0)),      # Monday morning
            _tracker(OutcomeStatus.RESPONDED, submitted_at=datetime(2026, 3, 10, 14, 0)),   # Tuesday afternoon
        ]
        svc = _make_service(trackers)
        result = await svc.get_timing_analysis(_user_id)

        assert len(result["windows"]) == 2
        # Tuesday afternoon: 1/1 = 1.0, Monday morning: 1/2 = 0.5
        assert result["windows"][0]["response_rate"] == 1.0
        assert result["windows"][0]["day_of_week"] == "Tuesday"
        assert result["windows"][0]["time_bucket"] == "afternoon"

    async def test_empty_returns_insufficient(self) -> None:
        svc = _make_service([])
        result = await svc.get_timing_analysis(_user_id)

        assert result["windows"] == []
        assert result["confidence"] == "insufficient"

    async def test_skips_null_submitted_at(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, submitted_at=datetime(2026, 3, 10, 9, 0)),
            _tracker(OutcomeStatus.APPLIED, submitted_at=None),
        ]
        svc = _make_service(trackers)
        result = await svc.get_timing_analysis(_user_id)

        total_samples = sum(w["sample_size"] for w in result["windows"])
        assert total_samples == 1

    async def test_time_buckets(self) -> None:
        trackers = [
            _tracker(submitted_at=datetime(2026, 3, 10, 3, 0)),   # night
            _tracker(submitted_at=datetime(2026, 3, 10, 8, 0)),   # morning
            _tracker(submitted_at=datetime(2026, 3, 10, 14, 0)),  # afternoon
            _tracker(submitted_at=datetime(2026, 3, 10, 19, 0)),  # evening
        ]
        svc = _make_service(trackers)
        result = await svc.get_timing_analysis(_user_id)

        buckets = {w["time_bucket"] for w in result["windows"]}
        assert buckets == {"night", "morning", "afternoon", "evening"}

    async def test_confidence_per_bucket(self) -> None:
        trackers = [_tracker(submitted_at=datetime(2026, 3, 10, 9, 0))]
        svc = _make_service(trackers)
        result = await svc.get_timing_analysis(_user_id)

        assert result["windows"][0]["confidence"] == "insufficient"


# ---------------------------------------------------------------------------
# get_strategy_comparison
# ---------------------------------------------------------------------------


class TestGetStrategyComparison:
    async def test_ranks_by_response_rate(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, resume_strategy="technical"),
            _tracker(OutcomeStatus.RESPONDED, resume_strategy="technical"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="general"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="general"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_strategy_comparison(_user_id)

        assert result["resume_strategies"][0]["strategy"] == "technical"
        assert result["resume_strategies"][0]["response_rate"] == 1.0
        assert result["resume_strategies"][1]["strategy"] == "general"
        assert result["resume_strategies"][1]["response_rate"] == 0.0

    async def test_empty_returns_insufficient(self) -> None:
        svc = _make_service([])
        result = await svc.get_strategy_comparison(_user_id)

        assert result["resume_strategies"] == []
        assert result["cover_letter_strategies"] == []
        assert result["confidence"] == "insufficient"

    async def test_skips_empty_strategy(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, resume_strategy="technical"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy=""),
        ]
        svc = _make_service(trackers)
        result = await svc.get_strategy_comparison(_user_id)

        assert len(result["resume_strategies"]) == 1
        assert result["resume_strategies"][0]["strategy"] == "technical"

    async def test_cover_letter_strategies(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, cover_letter_strategy="personalized"),
            _tracker(OutcomeStatus.APPLIED, cover_letter_strategy="template"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_strategy_comparison(_user_id)

        assert len(result["cover_letter_strategies"]) == 2
        assert result["cover_letter_strategies"][0]["strategy"] == "personalized"


# ---------------------------------------------------------------------------
# Legacy methods (backward compat)
# ---------------------------------------------------------------------------


class TestGetResponseRate:
    async def test_empty(self) -> None:
        svc = _make_service([])
        result = await svc.get_response_rate(_user_id)

        assert result["total"] == 0
        assert result["response_rate"] == 0.0

    async def test_with_data(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, submission_method="linkedin"),
            _tracker(OutcomeStatus.APPLIED, submission_method="linkedin"),
            _tracker(OutcomeStatus.INTERVIEW_SCHEDULED, submission_method="email"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_response_rate(_user_id)

        assert result["total"] == 3
        assert result["by_method"]["linkedin"]["total"] == 2
        assert result["by_method"]["email"]["total"] == 1


class TestGetBestPerformingStrategies:
    async def test_ranked(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, resume_strategy="technical"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="general"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_best_performing_strategies(_user_id)

        assert result["strategies"][0]["strategy"] == "technical"
        assert result["strategies"][0]["rate"] == 1.0
