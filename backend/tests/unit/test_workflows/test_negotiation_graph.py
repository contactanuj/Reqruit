"""
Tests for the negotiation workflow graph — state, builder, and singleton pattern.

Uses MemorySaver (in-memory checkpointer) so no MongoDB is needed.
"""

from unittest.mock import patch

from langgraph.checkpoint.memory import MemorySaver

from src.workflows.graphs.negotiation import (
    build_negotiation_graph,
    get_negotiation_graph,
    init_negotiation_graph,
)
from src.workflows.states.negotiation import NegotiationState


class TestNegotiationState:

    def test_state_has_required_keys(self):
        """NegotiationState TypedDict should define all expected keys."""
        annotations = NegotiationState.__annotations__
        expected_keys = {
            "messages", "offer_details", "market_data",
            "competing_offers", "user_priorities",
            "simulation_transcript", "user_response",
            "scripts", "decision_matrix", "feedback", "status",
        }
        assert expected_keys.issubset(set(annotations.keys()))


class TestBuildNegotiationGraph:

    def test_build_returns_compiled_graph(self):
        checkpointer = MemorySaver()
        graph = build_negotiation_graph(checkpointer)
        assert graph is not None

    def test_graph_has_simulate_node(self):
        checkpointer = MemorySaver()
        graph = build_negotiation_graph(checkpointer)
        node_names = list(graph.get_graph().nodes.keys())
        assert "simulate_negotiation" in node_names

    def test_graph_has_generate_scripts_node(self):
        checkpointer = MemorySaver()
        graph = build_negotiation_graph(checkpointer)
        node_names = list(graph.get_graph().nodes.keys())
        assert "generate_scripts" in node_names

    def test_graph_has_decision_framework_node(self):
        checkpointer = MemorySaver()
        graph = build_negotiation_graph(checkpointer)
        node_names = list(graph.get_graph().nodes.keys())
        assert "decision_framework" in node_names

    def test_graph_has_human_review_node(self):
        checkpointer = MemorySaver()
        graph = build_negotiation_graph(checkpointer)
        node_names = list(graph.get_graph().nodes.keys())
        assert "human_review" in node_names


class TestNegotiationGraphSingleton:

    def test_init_and_get(self):
        checkpointer = MemorySaver()
        with patch(
            "src.workflows.graphs.negotiation._compiled_graph", None
        ):
            init_negotiation_graph(checkpointer)
            graph = get_negotiation_graph()
            assert graph is not None

    def test_get_raises_if_not_initialized(self):
        with patch(
            "src.workflows.graphs.negotiation._compiled_graph", None
        ):
            try:
                get_negotiation_graph()
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                assert "not initialized" in str(e)
