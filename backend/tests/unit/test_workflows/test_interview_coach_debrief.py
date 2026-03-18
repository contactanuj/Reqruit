"""
Tests for enhanced debrief node and save_performance node (Story 9.3).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from src.workflows.graphs.interview_coach import (
    _calc_overall_score,
    _parse_assessment,
    debrief,
    save_performance,
)

_COACH_PATH = "src.workflows.graphs.interview_coach._coach"
_REPO_PATH = "src.workflows.graphs.interview_coach.InterviewPerformanceRepository"


def _sample_scores():
    return [
        {
            "question_text": "Tell me about leadership",
            "question_type": "behavioral",
            "score_relevance": 4,
            "score_structure": 3,
            "score_specificity": 4,
            "score_confidence": 3,
            "feedback": "Good example",
            "improvement_suggestion": "More detail",
        },
        {
            "question_text": "How do you handle conflict?",
            "question_type": "behavioral",
            "score_relevance": 3,
            "score_structure": 4,
            "score_specificity": 3,
            "score_confidence": 4,
            "feedback": "Clear structure",
            "improvement_suggestion": "Quantify impact",
        },
    ]


def _debrief_state(session_scores=None):
    return {
        "messages": [],
        "company_name": "TestCorp",
        "role_title": "Software Engineer",
        "session_scores": session_scores if session_scores is not None else _sample_scores(),
        "difficulty_level": "medium",
        "star_stories": "",
        "overall_assessment": "",
        "status": "evaluating",
        "session_id": "sess-123",
    }


def _config(user_id="aaaaaaaaaaaaaaaaaaaaaaaa", thread_id="t-1"):
    return {"configurable": {"user_id": user_id, "thread_id": thread_id}}


class TestDebriefNode:
    async def test_generates_structured_assessment(self) -> None:
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {
                "evaluation": json.dumps({
                    "strengths": ["Clear examples", "Good structure"],
                    "weaknesses": ["Needs more specificity"],
                    "recommendations": ["Practice quantifying results"],
                })
            }
            result = await debrief(_debrief_state(), _config())

        assert result["status"] == "complete"
        assessment = json.loads(result["overall_assessment"])
        assert assessment["strengths"] == ["Clear examples", "Good structure"]
        assert assessment["weaknesses"] == ["Needs more specificity"]
        assert assessment["recommendations"] == ["Practice quantifying results"]

    async def test_calculates_overall_score(self) -> None:
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": "{}"}
            result = await debrief(_debrief_state(), _config())

        assessment = json.loads(result["overall_assessment"])
        # Q1: avg(4,3,4,3)=3.5, Q2: avg(3,4,3,4)=3.5, overall=3.5
        assert assessment["overall_score"] == 3.5

    async def test_handles_empty_scores(self) -> None:
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": "{}"}
            result = await debrief(_debrief_state(session_scores=[]), _config())

        assessment = json.loads(result["overall_assessment"])
        assert assessment["overall_score"] == 0.0
        assert assessment["question_count"] == 0

    async def test_handles_agent_failure_gracefully(self) -> None:
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.side_effect = RuntimeError("LLM failed")
            result = await debrief(_debrief_state(), _config())

        assert result["status"] == "complete"
        assessment = json.loads(result["overall_assessment"])
        assert assessment["summary"] == ""

    async def test_handles_non_json_agent_response(self) -> None:
        with patch(_COACH_PATH, new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = {"evaluation": "Great session overall."}
            result = await debrief(_debrief_state(), _config())

        assessment = json.loads(result["overall_assessment"])
        assert assessment["summary"] == "Great session overall."
        assert assessment["strengths"] == []


class TestSavePerformance:
    async def test_creates_interview_performance(self) -> None:
        state = _debrief_state()
        state["overall_assessment"] = json.dumps({
            "summary": "Good session",
            "strengths": ["Communication"],
            "weaknesses": ["Depth"],
            "overall_score": 3.5,
        })

        with patch(_REPO_PATH) as MockRepo:
            mock_repo = MagicMock()
            mock_repo.create = AsyncMock()
            MockRepo.return_value = mock_repo

            await save_performance(state, _config())

        mock_repo.create.assert_called_once()
        perf = mock_repo.create.call_args[0][0]
        assert perf.company_name == "TestCorp"
        assert perf.role_title == "Software Engineer"
        assert len(perf.question_scores) == 2
        assert perf.overall_score == 3.5
        assert perf.strengths == ["Communication"]
        assert perf.improvement_areas == ["Depth"]

    async def test_maps_question_scores_correctly(self) -> None:
        state = _debrief_state()
        state["overall_assessment"] = "{}"

        with patch(_REPO_PATH) as MockRepo:
            mock_repo = MagicMock()
            mock_repo.create = AsyncMock()
            MockRepo.return_value = mock_repo

            await save_performance(state, _config())

        perf = mock_repo.create.call_args[0][0]
        qs = perf.question_scores[0]
        assert qs.question_text == "Tell me about leadership"
        assert qs.score_relevance == 4
        assert qs.feedback == "Good example"

    async def test_handles_save_failure_gracefully(self) -> None:
        state = _debrief_state()
        state["overall_assessment"] = "{}"

        with patch(_REPO_PATH) as MockRepo:
            mock_repo = MagicMock()
            mock_repo.create = AsyncMock(side_effect=Exception("DB down"))
            MockRepo.return_value = mock_repo

            result = await save_performance(state, _config())

        assert result["status"] == "complete"

    async def test_uses_session_id_from_state(self) -> None:
        state = _debrief_state()
        state["overall_assessment"] = "{}"

        with patch(_REPO_PATH) as MockRepo:
            mock_repo = MagicMock()
            mock_repo.create = AsyncMock()
            MockRepo.return_value = mock_repo

            await save_performance(state, _config())

        perf = mock_repo.create.call_args[0][0]
        assert perf.session_id == "sess-123"


class TestHelpers:
    def test_calc_overall_score(self) -> None:
        scores = _sample_scores()
        assert _calc_overall_score(scores) == 3.5

    def test_calc_overall_score_empty(self) -> None:
        assert _calc_overall_score([]) == 0.0

    def test_calc_overall_score_partial_zeros(self) -> None:
        scores = [{"score_relevance": 4, "score_structure": 0, "score_specificity": 0, "score_confidence": 0}]
        assert _calc_overall_score(scores) == 1.0  # avg(4,0,0,0) = 1.0

    def test_parse_assessment_valid_json(self) -> None:
        text = json.dumps({
            "strengths": ["A"],
            "weaknesses": ["B"],
            "recommendations": ["C"],
        })
        s, w, r = _parse_assessment(text)
        assert s == ["A"]
        assert w == ["B"]
        assert r == ["C"]

    def test_parse_assessment_non_json(self) -> None:
        s, w, r = _parse_assessment("Just a text summary")
        assert s == []
        assert w == []
        assert r == []
