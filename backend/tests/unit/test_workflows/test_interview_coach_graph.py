"""
Tests for the interview coach workflow graph.

Uses MemorySaver (in-memory checkpointer) so no MongoDB is needed.
Agent LLM calls are mocked — these tests verify graph structure,
HITL interrupt/resume, question loop, and difficulty adjustment.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.workflows.graphs.interview_coach import (
    build_interview_coach_graph,
    get_interview_coach_graph,
    init_interview_coach_graph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_QUESTIONS = json.dumps([
    {"question_text": "Tell me about yourself.", "question_type": "behavioral", "difficulty": "easy"},
    {"question_text": "Design a cache system.", "question_type": "technical", "difficulty": "hard"},
    {"question_text": "Describe a conflict.", "question_type": "situational", "difficulty": "medium"},
])

MOCK_EVALUATION = json.dumps({
    "score_relevance": 4,
    "score_structure": 3,
    "score_specificity": 4,
    "score_confidence": 3,
    "feedback": "Good answer with clear structure.",
    "improvement_suggestion": "Add more quantified results.",
    "next_difficulty": "medium",
})


@pytest.fixture
def graph():
    """Build a compiled interview coach graph with in-memory checkpointing."""
    checkpointer = MemorySaver()
    return build_interview_coach_graph(checkpointer)


@pytest.fixture
def mock_agents():
    """Mock both agent singletons so no LLM calls are made."""
    predictor_mock = AsyncMock(
        return_value={"predicted_questions": MOCK_QUESTIONS}
    )
    coach_mock = AsyncMock(
        return_value={"evaluation": MOCK_EVALUATION}
    )

    with (
        patch("src.workflows.graphs.interview_coach._predictor", predictor_mock),
        patch("src.workflows.graphs.interview_coach._coach", coach_mock),
    ):
        yield predictor_mock, coach_mock


def _initial_state():
    return {
        "messages": [],
        "company_name": "Acme Corp",
        "role_title": "Senior Engineer",
        "jd_analysis": "Requires Python, system design",
        "company_research": "",
        "locale_context": "",
        "predicted_questions": "",
        "current_question_index": 0,
        "current_question": "",
        "user_answer": "",
        "difficulty_level": "medium",
        "evaluation": "",
        "session_scores": [],
        "star_stories": "",
        "overall_assessment": "",
        "status": "pending",
        "interview_mode": "standard",
        "round_type": "behavioral",
        "company_pattern": "",
        "current_round_index": 0,
    }


# ---------------------------------------------------------------------------
# Graph structure tests
# ---------------------------------------------------------------------------


class TestGraphStructure:
    """Verify the graph has the expected nodes."""

    def test_graph_has_expected_nodes(self, graph) -> None:
        node_names = set(graph.get_graph().nodes.keys())
        expected = {
            "__start__", "__end__",
            "predict_questions", "present_question",
            "evaluate_answer", "advance_index", "debrief",
        }
        assert expected.issubset(node_names)

    def test_graph_compiles(self, graph) -> None:
        assert graph is not None


# ---------------------------------------------------------------------------
# Execution tests
# ---------------------------------------------------------------------------


class TestGraphExecution:
    """Verify the graph executes correctly with HITL and question loop."""

    async def test_runs_to_first_question_and_pauses(self, graph, mock_agents) -> None:
        """Graph should predict questions then pause at present_question."""
        predictor_mock, _ = mock_agents

        config = {"configurable": {"thread_id": "test-1", "user_id": "user-1"}}
        await graph.ainvoke(_initial_state(), config=config)

        predictor_mock.assert_called_once()

        # Should pause at present_question interrupt
        state = await graph.aget_state(config)
        assert len(state.tasks) > 0

    async def test_answer_evaluates_and_loops(self, graph, mock_agents) -> None:
        """Answering a question should evaluate and pause for the next question."""
        _, coach_mock = mock_agents

        config = {"configurable": {"thread_id": "test-loop", "user_id": "user-1"}}
        await graph.ainvoke(_initial_state(), config=config)

        # Answer first question
        await graph.ainvoke(
            Command(resume={"answer": "I am a senior Python developer with 8 years experience."}),
            config=config,
        )

        coach_mock.assert_called_once()

        # Should pause again for the next question
        state = await graph.aget_state(config)
        assert len(state.tasks) > 0

    async def test_all_questions_lead_to_debrief(self, graph, mock_agents) -> None:
        """After answering all questions, the graph should reach debrief and complete."""
        _, coach_mock = mock_agents

        config = {"configurable": {"thread_id": "test-debrief", "user_id": "user-1"}}
        await graph.ainvoke(_initial_state(), config=config)

        # Answer all 3 questions
        for i in range(3):
            result = await graph.ainvoke(
                Command(resume={"answer": f"Answer to question {i + 1}"}),
                config=config,
            )

        # 3 evaluations + 1 debrief summary call
        assert coach_mock.call_count == 4
        assert result["status"] == "complete"
        assessment = json.loads(result.get("overall_assessment", "{}"))
        assert "overall_score" in assessment

    async def test_session_scores_accumulate(self, graph, mock_agents) -> None:
        """Session scores should accumulate with each answered question."""
        config = {"configurable": {"thread_id": "test-scores", "user_id": "user-1"}}
        await graph.ainvoke(_initial_state(), config=config)

        # Answer first question
        await graph.ainvoke(
            Command(resume={"answer": "My answer"}),
            config=config,
        )

        state_snapshot = await graph.aget_state(config)
        values = state_snapshot.values
        assert len(values.get("session_scores", [])) == 1


# ---------------------------------------------------------------------------
# Singleton lifecycle tests
# ---------------------------------------------------------------------------


class TestGraphSingleton:
    """Test the init/get lifecycle functions."""

    def test_get_before_init_raises(self) -> None:
        import src.workflows.graphs.interview_coach as mod

        original = mod._compiled_graph
        mod._compiled_graph = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                get_interview_coach_graph()
        finally:
            mod._compiled_graph = original

    def test_init_and_get(self) -> None:
        checkpointer = MemorySaver()
        init_interview_coach_graph(checkpointer)
        graph = get_interview_coach_graph()
        assert graph is not None
