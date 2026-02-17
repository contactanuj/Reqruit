"""
Tests for the cover letter workflow graph.

Uses MemorySaver (in-memory checkpointer) so no MongoDB is needed.
The agent LLM calls are mocked — these tests verify graph structure,
node execution order, HITL interrupt/resume, and the revision loop.

Design note: We mock at the agent __call__ level (not at the LLM level)
because these tests are about graph behavior, not agent behavior. Agent
tests in test_base.py and test_cover_letter.py cover the LLM interaction.
"""

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.workflows.graphs.cover_letter import build_cover_letter_graph

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def graph():
    """Build a compiled cover letter graph with in-memory checkpointing."""
    checkpointer = MemorySaver()
    return build_cover_letter_graph(checkpointer)


@pytest.fixture
def mock_agents():
    """
    Mock both agent singletons so no LLM calls are made.

    Returns the two mock callables for additional assertions.
    """
    analyst_mock = AsyncMock(
        return_value={"requirements_analysis": "Needs Python, FastAPI, 5+ years"}
    )
    writer_mock = AsyncMock(
        return_value={"cover_letter": "Dear Hiring Manager,\n\nI am excited..."}
    )

    with (
        patch(
            "src.workflows.graphs.cover_letter._analyst",
            analyst_mock,
        ),
        patch(
            "src.workflows.graphs.cover_letter._writer",
            writer_mock,
        ),
    ):
        yield analyst_mock, writer_mock


def _make_config(thread_id: str = "test-thread-1") -> dict:
    """Create a standard LangGraph config with thread_id and user_id."""
    return {
        "configurable": {
            "thread_id": thread_id,
            "user_id": "test-user",
        }
    }


def _make_initial_state() -> dict:
    """Create the initial state for a cover letter workflow."""
    return {
        "messages": [],
        "job_description": "Senior Python Developer at Acme Corp...",
        "resume_text": "10 years of Python experience...",
        "requirements_analysis": "",
        "cover_letter": "",
        "feedback": "",
        "status": "pending",
    }


# ---------------------------------------------------------------------------
# Graph structure
# ---------------------------------------------------------------------------


class TestGraphStructure:
    def test_graph_compiles_with_correct_nodes(self, graph):
        """Verify the graph has the expected nodes."""
        node_names = set(graph.get_graph().nodes.keys())
        # LangGraph adds __start__ and __end__ pseudo-nodes
        assert "analyze_requirements" in node_names
        assert "write_cover_letter" in node_names
        assert "human_review" in node_names


# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------


class TestWorkflowExecution:
    async def test_workflow_pauses_at_human_review(self, graph, mock_agents):
        """The workflow should pause at human_review with an interrupt."""
        config = _make_config()
        state = _make_initial_state()

        # ainvoke will run until it hits the interrupt in human_review
        result = await graph.ainvoke(state, config)

        # Both agents should have been called
        analyst_mock, writer_mock = mock_agents
        analyst_mock.assert_called_once()
        writer_mock.assert_called_once()

        # The state should have the cover letter from the writer
        assert result["cover_letter"] == "Dear Hiring Manager,\n\nI am excited..."
        assert result["requirements_analysis"] == "Needs Python, FastAPI, 5+ years"

    async def test_interrupt_value_contains_cover_letter(self, graph, mock_agents):
        """The interrupt should surface the cover letter draft for review."""
        config = _make_config()
        state = _make_initial_state()

        await graph.ainvoke(state, config)

        # Check the graph state to verify it paused
        graph_state = await graph.aget_state(config)
        assert graph_state.next == ("human_review",)

        # The interrupt value should contain the draft
        tasks = graph_state.tasks
        assert len(tasks) > 0
        interrupts = tasks[0].interrupts
        assert len(interrupts) > 0
        interrupt_value = interrupts[0].value
        assert "cover_letter" in interrupt_value
        assert interrupt_value["cover_letter"] == "Dear Hiring Manager,\n\nI am excited..."

    async def test_approve_completes_workflow(self, graph, mock_agents):
        """Approving the draft should complete the workflow."""
        config = _make_config()
        state = _make_initial_state()

        # First invocation — runs to interrupt
        await graph.ainvoke(state, config)

        # Resume with approval
        result = await graph.ainvoke(
            Command(resume={"action": "approve"}), config
        )

        assert result["status"] == "approved"
        assert result["cover_letter"] == "Dear Hiring Manager,\n\nI am excited..."

    async def test_revision_loops_back_to_writer(self, graph, mock_agents):
        """Requesting a revision should loop back to write_cover_letter."""
        analyst_mock, writer_mock = mock_agents
        config = _make_config()
        state = _make_initial_state()

        # First invocation — runs to interrupt
        await graph.ainvoke(state, config)
        writer_mock.assert_called_once()

        # Update the writer mock for the revision call
        writer_mock.return_value = {
            "cover_letter": "Dear Hiring Manager,\n\nRevised version..."
        }

        # Resume with revision request — should call writer again and pause
        result = await graph.ainvoke(
            Command(resume={"action": "revise", "feedback": "Be more specific"}),
            config,
        )

        # Writer should have been called twice (original + revision)
        assert writer_mock.call_count == 2

        # The state should have the revised cover letter
        assert result["cover_letter"] == "Dear Hiring Manager,\n\nRevised version..."

        # Feedback should be in state
        assert result["feedback"] == "Be more specific"

    async def test_revision_then_approve_completes(self, graph, mock_agents):
        """A revision followed by approval should complete the workflow."""
        analyst_mock, writer_mock = mock_agents
        config = _make_config()
        state = _make_initial_state()

        # First invocation — runs to interrupt
        await graph.ainvoke(state, config)

        # Revision
        writer_mock.return_value = {
            "cover_letter": "Revised letter content"
        }
        await graph.ainvoke(
            Command(resume={"action": "revise", "feedback": "Add more detail"}),
            config,
        )

        # Approve
        result = await graph.ainvoke(
            Command(resume={"action": "approve"}), config
        )

        assert result["status"] == "approved"
        assert result["cover_letter"] == "Revised letter content"
