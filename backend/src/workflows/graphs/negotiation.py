"""
Negotiation workflow graph — multi-turn negotiation simulation and script generation.

Graph structure
---------------
::

    START -> simulate_negotiation -> (interrupt for user) -> simulate_negotiation -> ... -> END
    (standalone) generate_scripts node — invocable via API outside the main flow

Node responsibilities:
    simulate_negotiation: Calls NegotiationCoachAgent for recruiter response + coaching.
                         Uses interrupt() to pause for user input between turns.
                         Loops back to itself for subsequent turns until simulation_complete.
    generate_scripts:    Calls ScriptGeneratorAgent to produce counter-offer scripts
                         with decision tree branches. Writes to NegotiationState.scripts.
"""

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from src.agents.negotiation_coach import NegotiationCoachAgent
from src.agents.script_generator import ScriptGeneratorAgent
from src.workflows.states.negotiation import NegotiationState

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Agent singletons
# ---------------------------------------------------------------------------

_coach = NegotiationCoachAgent()
_script_gen = ScriptGeneratorAgent()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


async def simulate_negotiation(
    state: NegotiationState, config: RunnableConfig
) -> Command:
    """Run one turn of negotiation simulation, then pause for user input."""
    logger.info(
        "workflow_node_started",
        node="simulate_negotiation",
        turn=len(state.get("simulation_transcript", [])) + 1,
    )

    # Call the negotiation coach agent
    result = await _coach(state, config)

    recruiter_response = result.get("recruiter_response", "")
    coaching_feedback = result.get("coaching_feedback", "")
    tactic_detected = result.get("tactic_detected", "")
    turn_number = result.get("turn_number", 1)
    simulation_complete = result.get("simulation_complete", False)

    # Append to transcript
    transcript = list(state.get("simulation_transcript", []))

    # Add user response to transcript if this isn't the first turn
    user_response = state.get("user_response", "")
    if user_response:
        transcript.append({
            "role": "user",
            "content": user_response,
            "turn_number": turn_number,
        })

    # Add recruiter response
    transcript.append({
        "role": "recruiter",
        "content": recruiter_response,
        "coaching_feedback": coaching_feedback,
        "tactic_detected": tactic_detected,
        "turn_number": turn_number,
    })

    if simulation_complete:
        return Command(
            update={
                "simulation_transcript": transcript,
                "feedback": coaching_feedback,
                "status": "complete",
                "user_response": "",
            },
            goto=END,
        )

    # Pause for user input
    user_input = interrupt({
        "recruiter_response": recruiter_response,
        "coaching_feedback": coaching_feedback,
        "tactic_detected": tactic_detected,
        "turn_number": turn_number,
    })

    # Resume: user_input contains the user's next response
    return Command(
        update={
            "simulation_transcript": transcript,
            "user_response": user_input.get("user_response", "") if isinstance(user_input, dict) else str(user_input),
            "status": "simulating",
        },
        goto="simulate_negotiation",
    )


async def generate_scripts(
    state: NegotiationState, config: RunnableConfig
) -> dict:
    """Generate counter-offer scripts with decision tree branches."""
    import time

    start = time.monotonic()
    logger.info("workflow_node_started", node="generate_scripts")

    result = await _script_gen(state, config)

    scripts = {
        "opening_statement": result.get("opening_statement", ""),
        "branches": result.get("branches", []),
        "non_salary_tactics": result.get("non_salary_tactics", []),
        "general_tips": result.get("general_tips", []),
    }

    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "workflow_node_completed",
        node="generate_scripts",
        branches_count=len(scripts["branches"]),
        duration_ms=round(duration_ms, 1),
    )

    return {
        "scripts": [scripts],
        "status": "scripting",
    }


async def decision_framework(
    state: NegotiationState, config: RunnableConfig
) -> dict:
    """Compute multi-criteria decision matrix for competing offers."""
    import time

    start = time.monotonic()
    logger.info("workflow_node_started", node="decision_framework")

    # The actual computation is delegated to the decision service
    # which is invoked from the route. This node stores the result.
    # When invoked via the graph, the decision_matrix is already populated
    # by the route handler before resuming the graph.

    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "workflow_node_completed",
        node="decision_framework",
        duration_ms=round(duration_ms, 1),
    )

    return {
        "status": "deciding",
    }


async def human_review(
    state: NegotiationState, config: RunnableConfig
) -> Command:
    """Pause for user review of scripts and decision matrix.

    The user can approve (proceed to END) or request revision
    (loop back to generate_scripts).
    """
    logger.info("workflow_node_started", node="human_review")

    review_decision = interrupt({
        "scripts": state.get("scripts", []),
        "decision_matrix": state.get("decision_matrix", {}),
        "message": "Review your negotiation results",
    })

    action = review_decision.get("action", "approve") if isinstance(review_decision, dict) else "approve"
    feedback = review_decision.get("feedback", "") if isinstance(review_decision, dict) else ""

    if action == "revise":
        logger.info("human_review_revision_requested", feedback=feedback)
        return Command(
            update={"feedback": feedback, "status": "revision_requested"},
            goto="generate_scripts",
        )

    logger.info("human_review_approved")
    return Command(
        update={"status": "approved"},
        goto=END,
    )


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route_simulation(state: NegotiationState) -> str:
    """Route based on simulation status."""
    if state.get("status") == "complete":
        return END
    return "simulate_negotiation"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_negotiation_graph(
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Build and compile the negotiation workflow graph."""
    builder = StateGraph(NegotiationState)

    builder.add_node("simulate_negotiation", simulate_negotiation)
    builder.add_node("generate_scripts", generate_scripts)
    builder.add_node("decision_framework", decision_framework)
    builder.add_node("human_review", human_review)

    builder.add_edge(START, "simulate_negotiation")
    # simulate_negotiation uses Command to route itself (loop or END)
    # generate_scripts and decision_framework are invoked standalone via API
    # human_review uses Command to route to generate_scripts (revise) or END (approve)

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None


def init_negotiation_graph(checkpointer: BaseCheckpointSaver) -> None:
    """Build and cache the graph. Call once at application startup."""
    global _compiled_graph
    _compiled_graph = build_negotiation_graph(checkpointer)
    logger.info("negotiation_graph_initialized")


def get_negotiation_graph() -> CompiledStateGraph:
    """Return the cached compiled graph. Raises RuntimeError if not initialized."""
    if _compiled_graph is None:
        raise RuntimeError(
            "Negotiation graph not initialized. Call init_negotiation_graph() first."
        )
    return _compiled_graph
