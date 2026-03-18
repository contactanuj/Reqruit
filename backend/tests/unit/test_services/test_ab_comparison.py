"""Tests for A/B version comparison in SuccessAnalyticsService."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.db.documents.enums import OutcomeStatus
from src.services.success_analytics import SuccessAnalyticsService


_user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _tracker(
    outcome_status=OutcomeStatus.APPLIED,
    resume_strategy="",
    cover_letter_strategy="",
):
    t = MagicMock()
    t.outcome_status = outcome_status
    t.resume_strategy = resume_strategy
    t.cover_letter_strategy = cover_letter_strategy
    return t


def _make_service(trackers):
    repo = MagicMock()
    repo.get_for_user = AsyncMock(return_value=trackers)
    return SuccessAnalyticsService(repo)


class TestGetAbComparison:
    async def test_two_strategies_ranked(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, resume_strategy="technical"),
            _tracker(OutcomeStatus.RESPONDED, resume_strategy="technical"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="general"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="general"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_ab_comparison(_user_id, "resume_strategy")

        assert result["comparison_possible"] is True
        assert len(result["versions"]) == 2
        assert result["versions"][0]["strategy_name"] == "technical"
        assert result["versions"][0]["response_rate"] == 1.0
        assert result["versions"][1]["strategy_name"] == "general"
        assert result["versions"][1]["response_rate"] == 0.0

    async def test_single_strategy_not_possible(self) -> None:
        trackers = [
            _tracker(resume_strategy="technical"),
            _tracker(resume_strategy="technical"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_ab_comparison(_user_id, "resume_strategy")

        assert result["comparison_possible"] is False
        assert "one" in result["message"].lower() or "vary" in result["message"].lower()

    async def test_no_applications(self) -> None:
        svc = _make_service([])
        result = await svc.get_ab_comparison(_user_id, "resume_strategy")

        assert result["comparison_possible"] is False
        assert result["versions"] == []

    async def test_significance_sufficient(self) -> None:
        trackers = [_tracker(resume_strategy="v1") for _ in range(10)]
        trackers += [_tracker(resume_strategy="v2") for _ in range(3)]
        svc = _make_service(trackers)
        result = await svc.get_ab_comparison(_user_id, "resume_strategy")

        v1 = next(v for v in result["versions"] if v["strategy_name"] == "v1")
        v2 = next(v for v in result["versions"] if v["strategy_name"] == "v2")
        assert v1["significance"] == "sufficient"
        assert v2["significance"] == "inconclusive"

    async def test_view_rate_uses_cumulative(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.VIEWED, resume_strategy="a"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="a"),
            _tracker(OutcomeStatus.OFFER_RECEIVED, resume_strategy="b"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="b"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_ab_comparison(_user_id, "resume_strategy")

        a = next(v for v in result["versions"] if v["strategy_name"] == "a")
        b = next(v for v in result["versions"] if v["strategy_name"] == "b")
        assert a["view_rate"] == 0.5
        assert b["view_rate"] == 0.5

    async def test_interview_rate(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.INTERVIEW_SCHEDULED, resume_strategy="a"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="a"),
            _tracker(OutcomeStatus.OFFER_RECEIVED, resume_strategy="b"),
            _tracker(OutcomeStatus.APPLIED, resume_strategy="b"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_ab_comparison(_user_id, "resume_strategy")

        a = next(v for v in result["versions"] if v["strategy_name"] == "a")
        b = next(v for v in result["versions"] if v["strategy_name"] == "b")
        assert a["interview_rate"] == 0.5
        assert b["interview_rate"] == 0.5

    async def test_cover_letter_strategy(self) -> None:
        trackers = [
            _tracker(OutcomeStatus.RESPONDED, cover_letter_strategy="formal"),
            _tracker(OutcomeStatus.APPLIED, cover_letter_strategy="casual"),
        ]
        svc = _make_service(trackers)
        result = await svc.get_ab_comparison(_user_id, "cover_letter_strategy")

        assert result["comparison_possible"] is True
        assert result["compare_by"] == "cover_letter_strategy"

    async def test_empty_strategy_becomes_unspecified(self) -> None:
        trackers = [
            _tracker(resume_strategy="technical"),
            _tracker(resume_strategy=""),
        ]
        svc = _make_service(trackers)
        result = await svc.get_ab_comparison(_user_id, "resume_strategy")

        assert result["comparison_possible"] is True
        names = {v["strategy_name"] for v in result["versions"]}
        assert "unspecified" in names
