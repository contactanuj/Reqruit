"""
Tests for the skills analysis workflow graph.

Uses MemorySaver (in-memory checkpointer) so no MongoDB is needed.
Agent LLM calls are mocked — these tests verify graph structure,
node execution order, HITL interrupt/resume, and the revision loop.
"""

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.workflows.graphs.skills_analysis import (
    build_skills_analysis_graph,
    get_skills_analysis_graph,
    init_skills_analysis_graph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def graph():
    """Build a compiled skills analysis graph with in-memory checkpointing."""
    checkpointer = MemorySaver()
    return build_skills_analysis_graph(checkpointer)


@pytest.fixture
def mock_agents():
    """Mock both agent singletons so no LLM calls are made."""
    miner_mock = AsyncMock(
        return_value={"mined_achievements": '[{"title": "Built API", "impact": "3x throughput"}]'}
    )
    analyst_mock = AsyncMock(
        return_value={"skills_analysis": '{"skills": [{"name": "Python"}], "summary": "Strong backend dev"}'}
    )

    with (
        patch("src.workflows.graphs.skills_analysis._miner", miner_mock),
        patch("src.workflows.graphs.skills_analysis._analyst", analyst_mock),
    ):
        yield miner_mock, analyst_mock


# ---------------------------------------------------------------------------
# Graph structure tests
# ---------------------------------------------------------------------------


class TestGraphStructure:
    """Verify the graph has the expected nodes and edges."""

    def test_graph_has_expected_nodes(self, graph) -> None:
        node_names = set(graph.get_graph().nodes.keys())
        expected = {"__start__", "__end__", "mine_achievements", "analyze_skills", "human_review"}
        assert expected.issubset(node_names)

    def test_graph_compiles(self, graph) -> None:
        assert graph is not None


# ---------------------------------------------------------------------------
# Execution tests
# ---------------------------------------------------------------------------


class TestGraphExecution:
    """Verify the graph executes nodes in the correct order and pauses at HITL."""

    async def test_runs_to_human_review_and_pauses(self, graph, mock_agents) -> None:
        """Graph should mine -> analyze -> pause at human_review."""
        miner_mock, analyst_mock = mock_agents

        config = {"configurable": {"thread_id": "test-1", "user_id": "user-1"}}
        initial_state = {
            "messages": [],
            "resume_text": "Senior Python developer at Acme Corp...",
            "work_history": "",
            "existing_achievements": [],
            "mined_achievements": "",
            "skills_analysis": "",
            "feedback": "",
            "status": "pending",
        }

        result = await graph.ainvoke(initial_state, config=config)

        # Both agents should have been called
        miner_mock.assert_called_once()
        analyst_mock.assert_called_once()

        # Graph should pause at human_review with __interrupt__
        state = await graph.aget_state(config)
        assert len(state.tasks) > 0

    async def test_approve_completes_workflow(self, graph, mock_agents) -> None:
        """Approving at human_review should end the workflow."""
        config = {"configurable": {"thread_id": "test-approve", "user_id": "user-1"}}
        initial_state = {
            "messages": [],
            "resume_text": "Python developer",
            "work_history": "",
            "existing_achievements": [],
            "mined_achievements": "",
            "skills_analysis": "",
            "feedback": "",
            "status": "pending",
        }

        await graph.ainvoke(initial_state, config=config)

        # Resume with approval
        result = await graph.ainvoke(
            Command(resume={"action": "approve"}),
            config=config,
        )

        assert result["status"] == "approved"

    async def test_revise_loops_back_to_analyze(self, graph, mock_agents) -> None:
        """Requesting revision should re-run analyze_skills and pause again."""
        miner_mock, analyst_mock = mock_agents

        config = {"configurable": {"thread_id": "test-revise", "user_id": "user-1"}}
        initial_state = {
            "messages": [],
            "resume_text": "Python developer",
            "work_history": "",
            "existing_achievements": [],
            "mined_achievements": "",
            "skills_analysis": "",
            "feedback": "",
            "status": "pending",
        }

        await graph.ainvoke(initial_state, config=config)

        # Resume with revision request
        await graph.ainvoke(
            Command(resume={"action": "revise", "feedback": "Include cloud skills"}),
            config=config,
        )

        # Analyst should be called twice (initial + revision)
        assert analyst_mock.call_count == 2

        # Should pause again at human_review
        state = await graph.aget_state(config)
        assert len(state.tasks) > 0


# ---------------------------------------------------------------------------
# Singleton lifecycle tests
# ---------------------------------------------------------------------------


class TestGraphSingleton:
    """Test the init/get lifecycle functions."""

    def test_get_before_init_raises(self) -> None:
        """get_skills_analysis_graph should raise if not initialized."""
        import src.workflows.graphs.skills_analysis as mod

        original = mod._compiled_graph
        mod._compiled_graph = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                get_skills_analysis_graph()
        finally:
            mod._compiled_graph = original

    def test_init_and_get(self) -> None:
        """init should make get return a graph."""
        checkpointer = MemorySaver()
        init_skills_analysis_graph(checkpointer)
        graph = get_skills_analysis_graph()
        assert graph is not None
