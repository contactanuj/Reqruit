"""
Tests for InterviewPerformanceRepository analytics methods (Story 9.4).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from src.db.documents.interview_performance import InterviewPerformance, QuestionScore
from src.repositories.interview_performance_repository import (
    InterviewPerformanceRepository,
    _category_averages,
    _question_score_avg,
)


def _make_qs(qtype: str, rel: int, struct: int, spec: int, conf: int) -> QuestionScore:
    return QuestionScore(
        question_text=f"Q about {qtype}",
        question_type=qtype,
        score_relevance=rel,
        score_structure=struct,
        score_specificity=spec,
        score_confidence=conf,
    )


def _make_perf(
    session_id: str,
    question_scores: list[QuestionScore],
    overall: float = 3.0,
) -> MagicMock:
    perf = MagicMock(spec=InterviewPerformance)
    perf.session_id = session_id
    perf.overall_score = overall
    perf.created_at = None
    perf.question_scores = question_scores
    perf.strengths = []
    perf.improvement_areas = []
    return perf


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestQuestionScoreAvg:
    def test_all_nonzero(self) -> None:
        qs = _make_qs("behavioral", 4, 3, 5, 4)
        assert _question_score_avg(qs) == 4.0

    def test_some_zero(self) -> None:
        qs = _make_qs("technical", 4, 0, 0, 0)
        assert _question_score_avg(qs) == 4.0

    def test_all_zero(self) -> None:
        qs = _make_qs("unknown", 0, 0, 0, 0)
        assert _question_score_avg(qs) == 0.0


class TestCategoryAverages:
    def test_single_category(self) -> None:
        sessions = [
            _make_perf("s1", [_make_qs("behavioral", 4, 4, 4, 4)]),
            _make_perf("s2", [_make_qs("behavioral", 2, 2, 2, 2)]),
        ]
        result = _category_averages(sessions)
        assert result["behavioral"] == 3.0

    def test_multiple_categories(self) -> None:
        sessions = [
            _make_perf("s1", [
                _make_qs("behavioral", 4, 4, 4, 4),
                _make_qs("technical", 2, 2, 2, 2),
            ]),
        ]
        result = _category_averages(sessions)
        assert result["behavioral"] == 4.0
        assert result["technical"] == 2.0


# ---------------------------------------------------------------------------
# Repository method tests
# ---------------------------------------------------------------------------


class TestGetUserTrends:
    async def test_empty_sessions(self) -> None:
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=[]):
            result = await repo.get_user_trends(PydanticObjectId())
        assert result == {"categories": {}, "overall_trend": []}

    async def test_groups_by_category(self) -> None:
        sessions = [
            _make_perf("s1", [
                _make_qs("behavioral", 4, 4, 4, 4),
                _make_qs("technical", 2, 2, 2, 2),
            ], overall=3.0),
            _make_perf("s2", [
                _make_qs("behavioral", 5, 5, 5, 5),
                _make_qs("technical", 3, 3, 3, 3),
            ], overall=4.0),
        ]
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=sessions):
            result = await repo.get_user_trends(PydanticObjectId())

        assert "behavioral" in result["categories"]
        assert "technical" in result["categories"]
        assert result["categories"]["behavioral"]["average_score"] == 4.5
        assert result["categories"]["technical"]["average_score"] == 2.5
        assert result["categories"]["behavioral"]["data_points"] == 2
        assert len(result["overall_trend"]) == 2

    async def test_unknown_question_type(self) -> None:
        sessions = [_make_perf("s1", [_make_qs("", 3, 3, 3, 3)])]
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=sessions):
            result = await repo.get_user_trends(PydanticObjectId())
        assert "unknown" in result["categories"]


class TestGetImprovementVelocity:
    async def test_not_enough_data(self) -> None:
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=[
            _make_perf("s1", [_make_qs("behavioral", 3, 3, 3, 3)]),
        ]):
            result = await repo.get_improvement_velocity(PydanticObjectId())
        assert result["has_enough_data"] is False
        assert result["velocity"] == {}

    async def test_computes_delta(self) -> None:
        # Sessions returned newest-first; s3 is most recent
        sessions = [
            _make_perf("s3", [_make_qs("behavioral", 5, 5, 5, 5)], 5.0),
            _make_perf("s2", [_make_qs("behavioral", 4, 4, 4, 4)], 4.0),
            _make_perf("s1", [_make_qs("behavioral", 2, 2, 2, 2)], 2.0),
            _make_perf("s0", [_make_qs("behavioral", 1, 1, 1, 1)], 1.0),
        ]
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=sessions):
            result = await repo.get_improvement_velocity(PydanticObjectId())

        assert result["has_enough_data"] is True
        beh = result["velocity"]["behavioral"]
        # Early (s0, s1): avg 1.5, Late (s2, s3): avg 4.5
        assert beh["early_avg"] == 1.5
        assert beh["late_avg"] == 4.5
        assert beh["delta"] == 3.0
        assert beh["improving"] is True

    async def test_declining_category(self) -> None:
        sessions = [
            _make_perf("s2", [_make_qs("technical", 1, 1, 1, 1)]),
            _make_perf("s1", [_make_qs("technical", 4, 4, 4, 4)]),
        ]
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=sessions):
            result = await repo.get_improvement_velocity(PydanticObjectId())

        tech = result["velocity"]["technical"]
        assert tech["improving"] is False
        assert tech["delta"] < 0


class TestGetWeakAreas:
    async def test_not_enough_sessions(self) -> None:
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=[
            _make_perf("s1", [_make_qs("behavioral", 1, 1, 1, 1)]),
            _make_perf("s2", [_make_qs("behavioral", 1, 1, 1, 1)]),
        ]):
            result = await repo.get_weak_areas(PydanticObjectId())
        assert result == []

    async def test_detects_recurring_weakness(self) -> None:
        sessions = [
            _make_perf("s1", [_make_qs("technical", 1, 1, 1, 1), _make_qs("behavioral", 5, 5, 5, 5)]),
            _make_perf("s2", [_make_qs("technical", 2, 2, 2, 2), _make_qs("behavioral", 4, 4, 4, 4)]),
            _make_perf("s3", [_make_qs("technical", 1, 1, 1, 1), _make_qs("behavioral", 5, 5, 5, 5)]),
        ]
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=sessions):
            result = await repo.get_weak_areas(PydanticObjectId())

        assert len(result) == 1
        assert result[0]["category"] == "technical"
        assert result[0]["weak_session_count"] == 3

    async def test_ignores_strong_categories(self) -> None:
        sessions = [
            _make_perf("s1", [_make_qs("behavioral", 5, 5, 5, 5)]),
            _make_perf("s2", [_make_qs("behavioral", 4, 4, 4, 4)]),
            _make_perf("s3", [_make_qs("behavioral", 5, 5, 5, 5)]),
        ]
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=sessions):
            result = await repo.get_weak_areas(PydanticObjectId())
        assert result == []

    async def test_requires_3_weak_sessions(self) -> None:
        """Category weak in only 2 of 4 sessions should not appear."""
        sessions = [
            _make_perf("s1", [_make_qs("technical", 1, 1, 1, 1)]),
            _make_perf("s2", [_make_qs("technical", 5, 5, 5, 5)]),
            _make_perf("s3", [_make_qs("technical", 1, 1, 1, 1)]),
            _make_perf("s4", [_make_qs("technical", 5, 5, 5, 5)]),
        ]
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=sessions):
            result = await repo.get_weak_areas(PydanticObjectId())
        assert result == []

    async def test_sorted_by_average_score(self) -> None:
        sessions = [
            _make_perf("s1", [_make_qs("technical", 1, 1, 1, 1), _make_qs("situational", 2, 2, 2, 2)]),
            _make_perf("s2", [_make_qs("technical", 1, 1, 1, 1), _make_qs("situational", 2, 2, 2, 2)]),
            _make_perf("s3", [_make_qs("technical", 1, 1, 1, 1), _make_qs("situational", 2, 2, 2, 2)]),
        ]
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "get_user_sessions", new_callable=AsyncMock, return_value=sessions):
            result = await repo.get_weak_areas(PydanticObjectId())
        assert len(result) == 2
        assert result[0]["category"] == "technical"  # lower score first
        assert result[1]["category"] == "situational"


class TestCountUserSessions:
    async def test_delegates_to_count(self) -> None:
        repo = InterviewPerformanceRepository()
        with patch.object(repo, "count", new_callable=AsyncMock, return_value=5) as mock_count:
            uid = PydanticObjectId()
            result = await repo.count_user_sessions(uid)
        assert result == 5
        mock_count.assert_called_once_with({"user_id": uid})
