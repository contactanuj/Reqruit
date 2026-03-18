"""
Tests for the application assembly workflow graph.

Uses MemorySaver (in-memory checkpointer) so no MongoDB is needed.
Agent LLM calls are mocked — these tests verify graph structure,
node execution, and stub behavior.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from src.workflows.graphs.application_assembly import (
    build_application_assembly_graph,
    close_application_assembly_graph,
    get_application_assembly_graph,
    init_application_assembly_graph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def graph():
    """Build a compiled application assembly graph with in-memory checkpointing."""
    checkpointer = MemorySaver()
    return build_application_assembly_graph(checkpointer)


@pytest.fixture
def mock_agents():
    """Mock all functional agent singletons and external calls so no LLM/DB calls are made."""
    jd_mock = AsyncMock(return_value={"jd_analysis": '{"required_skills": ["Python"]}'})
    fit_mock = AsyncMock(return_value={"fit_assessment": '{"overall": 85, "skills_match": 90}'})
    orchestrator_mock = AsyncMock(return_value={"application_strategy": "tailored resume content"})
    cover_letter_mock = AsyncMock(return_value={"cover_letter": "Dear Hiring Manager..."})
    search_mock = AsyncMock(return_value=[
        {"properties": {"content": "Python developer"}, "score": 0.9},
    ])
    semantic_mock = AsyncMock(return_value=[])
    interrupt_mock = MagicMock(return_value={"action": "approve"})

    # load_locale mock — User.find_one returns None so it defaults to US
    user_mock_cls = MagicMock()
    user_mock_cls.find_one = AsyncMock(return_value=None)
    user_mock_cls.id = "user-1"

    with (
        patch("src.workflows.graphs.application_assembly._jd_decoder", jd_mock),
        patch("src.workflows.graphs.application_assembly._fit_scorer", fit_mock),
        patch("src.workflows.graphs.application_assembly._orchestrator", orchestrator_mock),
        patch("src.workflows.graphs.application_assembly._cover_letter_writer", cover_letter_mock),
        patch("src.workflows.graphs.application_assembly.hybrid_search", search_mock),
        patch("src.workflows.graphs.application_assembly.semantic_search", semantic_mock),
        patch("src.workflows.graphs.application_assembly.interrupt", interrupt_mock),
        patch("src.workflows.graphs.application_assembly.User", user_mock_cls),
    ):
        yield jd_mock, fit_mock


def _initial_state():
    return {
        "messages": [],
        "job_id": "job-123",
        "job_url": "",
        "jd_text": "We need a senior Python developer...",
        "resume_text": "",
        "job_description": "We need a senior Python developer...",
        "decoded_jd": "",
        "fit_analysis": "",
        "skills_summary": "Python expert with 8 years",
        "locale_context": "",
        "selected_resume_blocks": "",
        "application_strategy": "",
        "tailored_resume": "",
        "cover_letter": "",
        "micro_pitch": "",
        "feedback": "",
        "status": "pending",
        "resume_block_fallback": False,
        "star_stories_available": False,
        "locale_defaulted": False,
        "keyword_optimization": "",
        "application_id": "app-123",
        "thread_id": "thread-123",
    }


# ---------------------------------------------------------------------------
# Graph structure tests
# ---------------------------------------------------------------------------


class TestGraphStructure:
    """Verify the graph has the expected nodes and edges."""

    def test_graph_has_expected_nodes(self, graph) -> None:
        node_names = set(graph.get_graph().nodes.keys())
        expected = {
            "__start__", "__end__",
            "decode_jd", "score_fit", "load_locale", "select_resume_blocks",
            "tailor_resume", "generate_cover_letter", "generate_micro_pitch",
            "human_review",
        }
        assert expected.issubset(node_names)

    def test_graph_compiles(self, graph) -> None:
        assert graph is not None


# ---------------------------------------------------------------------------
# Execution tests
# ---------------------------------------------------------------------------


class TestGraphExecution:
    """Verify the graph executes nodes correctly."""

    async def test_decode_jd_node_calls_agent(self, graph, mock_agents) -> None:
        """decode_jd node should call JDDecoder and return decoded_jd."""
        jd_mock, _ = mock_agents
        config = {"configurable": {"thread_id": "test-decode", "user_id": "user-1"}}
        result = await graph.ainvoke(_initial_state(), config=config)

        jd_mock.assert_called_once()
        assert result.get("decoded_jd") == '{"required_skills": ["Python"]}'

    async def test_score_fit_node_calls_agent(self, graph, mock_agents) -> None:
        """score_fit node should call FitScorer and return fit_analysis."""
        _, fit_mock = mock_agents
        config = {"configurable": {"thread_id": "test-fit", "user_id": "user-1"}}
        result = await graph.ainvoke(_initial_state(), config=config)

        fit_mock.assert_called_once()
        assert result.get("fit_analysis") == '{"overall": 85, "skills_match": 90}'

    async def test_all_nodes_execute(self, graph, mock_agents) -> None:
        """All nodes execute and graph completes with approved status."""
        config = {"configurable": {"thread_id": "test-stubs", "user_id": "user-1"}}
        result = await graph.ainvoke(_initial_state(), config=config)

        # human_review (mocked interrupt returns approve) sets status to "approved"
        assert result.get("status") == "approved"

    async def test_full_pipeline_runs_to_completion(self, graph, mock_agents) -> None:
        """All nodes should execute and graph should reach END."""
        jd_mock, fit_mock = mock_agents
        config = {"configurable": {"thread_id": "test-full", "user_id": "user-1"}}
        result = await graph.ainvoke(_initial_state(), config=config)

        # Both functional agents called
        jd_mock.assert_called_once()
        fit_mock.assert_called_once()

        # Final status is "approved" (set by human_review with mocked interrupt)
        assert result["status"] == "approved"


# ---------------------------------------------------------------------------
# Singleton lifecycle tests
# ---------------------------------------------------------------------------


class TestGraphSingleton:
    """Test the init/get/close lifecycle functions."""

    def test_get_before_init_raises(self) -> None:
        import src.workflows.graphs.application_assembly as mod

        original = mod._compiled_graph
        mod._compiled_graph = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                get_application_assembly_graph()
        finally:
            mod._compiled_graph = original

    def test_init_and_get(self) -> None:
        checkpointer = MemorySaver()
        init_application_assembly_graph(checkpointer)
        graph = get_application_assembly_graph()
        assert graph is not None

    def test_close(self) -> None:
        import src.workflows.graphs.application_assembly as mod

        checkpointer = MemorySaver()
        init_application_assembly_graph(checkpointer)
        assert mod._compiled_graph is not None
        close_application_assembly_graph()
        assert mod._compiled_graph is None
