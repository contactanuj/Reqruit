"""
Tests for campus placement round transitions and advance_round node (Story 9.5).
"""

import json
from unittest.mock import AsyncMock, patch

from src.workflows.graphs.interview_coach import advance_round, route_next


def _make_config():
    return {"configurable": {"user_id": "user-1", "thread_id": "t-1"}}


class TestRouteNextCampus:
    def test_advances_round_after_last_question_aptitude(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}]),
            "current_question_index": 0,
            "interview_mode": "campus_placement",
            "round_type": "aptitude",
        }
        assert route_next(state) == "advance_round"

    def test_advances_round_after_last_question_gd(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}]),
            "current_question_index": 0,
            "interview_mode": "campus_placement",
            "round_type": "gd",
        }
        assert route_next(state) == "advance_round"

    def test_advances_round_after_last_question_technical(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}]),
            "current_question_index": 0,
            "interview_mode": "campus_placement",
            "round_type": "technical",
        }
        assert route_next(state) == "advance_round"

    def test_debriefs_after_last_round_hr(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}]),
            "current_question_index": 0,
            "interview_mode": "campus_placement",
            "round_type": "hr",
        }
        assert route_next(state) == "debrief"

    def test_continues_questions_within_round(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}, {"question_text": "Q2"}]),
            "current_question_index": 0,
            "interview_mode": "campus_placement",
            "round_type": "aptitude",
        }
        assert route_next(state) == "present_question"

    def test_standard_mode_still_debriefs(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}]),
            "current_question_index": 0,
            "interview_mode": "standard",
            "round_type": "behavioral",
        }
        assert route_next(state) == "debrief"

    def test_missing_mode_defaults_to_debrief(self) -> None:
        state = {
            "predicted_questions": json.dumps([{"question_text": "Q1"}]),
            "current_question_index": 0,
        }
        assert route_next(state) == "debrief"


class TestAdvanceRound:
    async def test_aptitude_to_gd(self) -> None:
        state = {"round_type": "aptitude", "current_round_index": 0}
        result = await advance_round(state, _make_config())
        assert result["round_type"] == "gd"
        assert result["current_question_index"] == 0
        assert result["predicted_questions"] == ""
        assert result["current_round_index"] == 1

    async def test_gd_to_technical(self) -> None:
        state = {"round_type": "gd", "current_round_index": 1}
        result = await advance_round(state, _make_config())
        assert result["round_type"] == "technical"
        assert result["current_round_index"] == 2

    async def test_technical_to_hr(self) -> None:
        state = {"round_type": "technical", "current_round_index": 2}
        result = await advance_round(state, _make_config())
        assert result["round_type"] == "hr"
        assert result["current_round_index"] == 3

    async def test_resets_question_index(self) -> None:
        state = {"round_type": "aptitude", "current_round_index": 0}
        result = await advance_round(state, _make_config())
        assert result["current_question_index"] == 0

    async def test_clears_predicted_questions(self) -> None:
        state = {"round_type": "aptitude", "current_round_index": 0}
        result = await advance_round(state, _make_config())
        assert result["predicted_questions"] == ""
