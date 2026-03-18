"""
Tests for evaluate_answer structured scoring and difficulty adjustment (Story 9.2).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.workflows.graphs.interview_coach import (
    evaluate_answer,
    route_next,
)

_COACH_PATH = "src.workflows.graphs.interview_coach._coach"


def _make_eval_json(
    relevance=3, structure=3, specificity=3, confidence=3,
    feedback="Good", improvement="More detail",
):
    return json.dumps({
        "score_relevance": relevance,
        "score_structure": structure,
        "score_specificity": specificity,
        "score_confidence": confidence,
        "feedback": feedback,
        "improvement_suggestion": improvement,
    })


def _make_state(
    difficulty="medium",
    session_scores=None,
    question="Test question",
    answer="Test answer",
):
    return {
        "current_question": question,
        "user_answer": answer,
        "difficulty_level": difficulty,
        "star_stories": "",
        "session_scores": session_scores or [],
    }


def _make_config():
    return {"configurable": {"user_id": "user-123", "thread_id": "t-1"}}


def _high_score_entry():
    return {
        "score_relevance": 5, "score_structure": 5,
        "score_specificity": 5, "score_confidence": 5,
    }


def _low_score_entry():
    return {
        "score_relevance": 1, "score_structure": 1,
        "score_specificity": 2, "score_confidence": 1,
    }


def _mid_score_entry():
    return {
        "score_relevance": 3, "score_structure": 3,
        "score_specificity": 3, "score_confidence": 3,
    }


class TestEvaluateAnswerScoring:
    async def test_extracts_all_four_dimensions(self) -> None:
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {
                "evaluation": _make_eval_json(4, 3, 5, 4),
            }
            result = await evaluate_answer(_make_state(), _make_config())

        entry = result["session_scores"][-1]
        assert entry["score_relevance"] == 4
        assert entry["score_structure"] == 3
        assert entry["score_specificity"] == 5
        assert entry["score_confidence"] == 4

    async def test_extracts_feedback_and_improvement(self) -> None:
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {
                "evaluation": _make_eval_json(
                    feedback="Good STAR usage",
                    improvement="Quantify results",
                ),
            }
            result = await evaluate_answer(_make_state(), _make_config())

        entry = result["session_scores"][-1]
        assert entry["feedback"] == "Good STAR usage"
        assert entry["improvement_suggestion"] == "Quantify results"

    async def test_handles_non_json_evaluation(self) -> None:
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": "Not valid JSON response"}
            result = await evaluate_answer(_make_state(), _make_config())

        entry = result["session_scores"][-1]
        assert entry.get("score_relevance") is None or entry.get("score_relevance", 0) == 0
        assert entry["evaluation"] == "Not valid JSON response"

    async def test_accumulates_scores(self) -> None:
        existing_scores = [{"question_text": "Q1", "score_relevance": 3}]
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": _make_eval_json()}
            result = await evaluate_answer(
                _make_state(session_scores=existing_scores), _make_config()
            )

        assert len(result["session_scores"]) == 2


class TestDifficultyAdjustment:
    async def test_increases_from_medium_to_hard(self) -> None:
        scores = [_high_score_entry() for _ in range(3)]
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": _make_eval_json(5, 5, 5, 5)}
            result = await evaluate_answer(
                _make_state(difficulty="medium", session_scores=scores),
                _make_config(),
            )
        assert result["difficulty_level"] == "hard"

    async def test_increases_from_easy_to_medium(self) -> None:
        scores = [_high_score_entry() for _ in range(3)]
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": _make_eval_json(5, 5, 5, 5)}
            result = await evaluate_answer(
                _make_state(difficulty="easy", session_scores=scores),
                _make_config(),
            )
        assert result["difficulty_level"] == "medium"

    async def test_decreases_from_medium_to_easy(self) -> None:
        scores = [_low_score_entry() for _ in range(3)]
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": _make_eval_json(1, 1, 1, 1)}
            result = await evaluate_answer(
                _make_state(difficulty="medium", session_scores=scores),
                _make_config(),
            )
        assert result["difficulty_level"] == "easy"

    async def test_decreases_from_hard_to_medium(self) -> None:
        scores = [_low_score_entry() for _ in range(3)]
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": _make_eval_json(1, 1, 1, 1)}
            result = await evaluate_answer(
                _make_state(difficulty="hard", session_scores=scores),
                _make_config(),
            )
        assert result["difficulty_level"] == "medium"

    async def test_stays_same_when_average_midrange(self) -> None:
        scores = [_mid_score_entry() for _ in range(3)]
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": _make_eval_json(3, 3, 3, 3)}
            result = await evaluate_answer(
                _make_state(difficulty="medium", session_scores=scores),
                _make_config(),
            )
        assert result["difficulty_level"] == "medium"

    async def test_single_step_transition_not_easy_to_hard(self) -> None:
        """easy should go to medium, NOT directly to hard."""
        scores = [_high_score_entry() for _ in range(3)]
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": _make_eval_json(5, 5, 5, 5)}
            result = await evaluate_answer(
                _make_state(difficulty="easy", session_scores=scores),
                _make_config(),
            )
        assert result["difficulty_level"] == "medium"

    async def test_no_adjustment_with_fewer_than_3_scores(self) -> None:
        scores = [_high_score_entry()]
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": _make_eval_json(5, 5, 5, 5)}
            result = await evaluate_answer(
                _make_state(difficulty="medium", session_scores=scores),
                _make_config(),
            )
        # Only 2 total scores (1 existing + 1 new) — not enough for adjustment
        assert result["difficulty_level"] == "medium"


class TestRouteNext:
    def test_returns_present_question_when_more_remain(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}, {"question_text": "Q2"}]),
            "current_question_index": 0,
        }
        assert route_next(state) == "present_question"

    def test_returns_debrief_at_last_question(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}, {"question_text": "Q2"}]),
            "current_question_index": 1,
        }
        assert route_next(state) == "debrief"

    def test_returns_debrief_with_single_question(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}]),
            "current_question_index": 0,
        }
        assert route_next(state) == "debrief"

    def test_returns_debrief_with_invalid_json(self) -> None:
        state = {"predicted_questions": "not json", "current_question_index": 0}
        assert route_next(state) == "debrief"
