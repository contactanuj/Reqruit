"""
Tests for STAR story retrieval in the present_question graph node (Story 9.2).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.workflows.graphs.interview_coach import present_question


def _make_state(questions=None, index=0, difficulty="medium"):
    if questions is None:
        questions = [{"question_text": "Tell me about a leadership challenge"}]
    return {
        "predicted_questions": json.dumps(questions),
        "current_question_index": index,
        "difficulty_level": difficulty,
    }


def _make_config(user_id="user-123", thread_id="t-1"):
    return {"configurable": {"user_id": user_id, "thread_id": thread_id}}


class TestStarStoryRetrieval:
    @patch("src.workflows.graphs.interview_coach.semantic_search")
    @patch("src.workflows.graphs.interview_coach.interrupt")
    async def test_retrieves_star_stories_and_includes_in_interrupt(
        self, mock_interrupt, mock_search
    ) -> None:
        mock_search.return_value = [
            {
                "properties": {
                    "title": "Led migration project",
                    "situation": "Our database was hitting scale limits",
                    "action": "Designed a phased migration plan",
                    "result": "Zero downtime, 40% improvement",
                }
            },
        ]
        mock_interrupt.return_value = {"answer": "My answer"}

        result = await present_question(_make_state(), _make_config())

        mock_search.assert_called_once_with(
            "STARStoryEmbedding",
            "Tell me about a leadership challenge",
            tenant="user-123",
            limit=3,
        )
        assert "Led migration project" in result["star_stories"]

        interrupt_payload = mock_interrupt.call_args[0][0]
        assert "coaching_hints" in interrupt_payload
        assert "Led migration project" in interrupt_payload["coaching_hints"]
        assert interrupt_payload["star_stories_used"] == ["Led migration project"]

    @patch("src.workflows.graphs.interview_coach.semantic_search")
    @patch("src.workflows.graphs.interview_coach.interrupt")
    async def test_handles_empty_retrieval(self, mock_interrupt, mock_search) -> None:
        mock_search.return_value = []
        mock_interrupt.return_value = {"answer": "My answer"}

        result = await present_question(_make_state(), _make_config())

        interrupt_payload = mock_interrupt.call_args[0][0]
        assert "No matching STAR stories" in interrupt_payload["coaching_hints"]
        assert result["star_stories"] == ""

    @patch("src.workflows.graphs.interview_coach.semantic_search")
    @patch("src.workflows.graphs.interview_coach.interrupt")
    async def test_handles_weaviate_failure_gracefully(
        self, mock_interrupt, mock_search
    ) -> None:
        mock_search.side_effect = Exception("Weaviate connection refused")
        mock_interrupt.return_value = {"answer": "My answer"}

        result = await present_question(_make_state(), _make_config())

        assert result["status"] == "coaching"
        interrupt_payload = mock_interrupt.call_args[0][0]
        assert "temporarily unavailable" in interrupt_payload["coaching_hints"]

    @patch("src.workflows.graphs.interview_coach.semantic_search")
    @patch("src.workflows.graphs.interview_coach.interrupt")
    async def test_includes_question_type_in_interrupt(
        self, mock_interrupt, mock_search
    ) -> None:
        mock_search.return_value = []
        mock_interrupt.return_value = {"answer": "My answer"}

        questions = [{"question_text": "Design a URL shortener", "question_type": "system_design"}]
        await present_question(_make_state(questions=questions), _make_config())

        interrupt_payload = mock_interrupt.call_args[0][0]
        assert interrupt_payload["question_type"] == "system_design"

    @patch("src.workflows.graphs.interview_coach.semantic_search")
    @patch("src.workflows.graphs.interview_coach.interrupt")
    async def test_skips_retrieval_without_user_id(
        self, mock_interrupt, mock_search
    ) -> None:
        mock_interrupt.return_value = {"answer": "My answer"}

        await present_question(_make_state(), _make_config(user_id=""))

        mock_search.assert_not_called()

    @patch("src.workflows.graphs.interview_coach.semantic_search")
    @patch("src.workflows.graphs.interview_coach.interrupt")
    async def test_multiple_stories_returned(
        self, mock_interrupt, mock_search
    ) -> None:
        mock_search.return_value = [
            {"properties": {"title": "Story A", "situation": "S1", "action": "A1", "result": "R1"}},
            {"properties": {"title": "Story B", "situation": "S2", "action": "A2", "result": "R2"}},
        ]
        mock_interrupt.return_value = {"answer": "My answer"}

        result = await present_question(_make_state(), _make_config())

        assert "Story A" in result["star_stories"]
        assert "Story B" in result["star_stories"]
        interrupt_payload = mock_interrupt.call_args[0][0]
        assert interrupt_payload["star_stories_used"] == ["Story A", "Story B"]
