"""
Onboarding workflow graph — plan generation, coaching, and progress tracking.

Graph structure
---------------
::

    START -> generate_plan -> human_review -> END
                                               |
    (independent entry) coaching_session <-> HITL -> END

Node responsibilities:
    generate_plan:    Calls OnboardingPlanAgent, appends locale-specific joining prep.
    human_review:     Uses interrupt() for HITL review of generated plan.
    coaching_session: Calls OnboardingCoachAgent for confidential situation coaching.
                      Supports follow-up via HITL interrupt loop.
"""

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from src.agents.onboarding_coach import onboarding_coach_agent
from src.agents.onboarding_plan import onboarding_plan_agent
from src.services.joining_prep_service import JoiningPrepService
from src.workflows.states.onboarding import OnboardingState

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


async def generate_plan(
    state: OnboardingState, config: RunnableConfig
) -> dict:
    """Call OnboardingPlanAgent to generate the onboarding plan."""
    logger.info(
        "workflow_node_started",
        node="generate_plan",
        company=state.get("company_name", ""),
    )

    result = await onboarding_plan_agent(state, config)

    # Append locale-specific joining prep (deterministic, not LLM)
    locale = state.get("locale", "")
    if locale:
        prep_service = JoiningPrepService()
        joining_prep = prep_service.get_joining_prep(locale)
        result["joining_prep"] = [item.model_dump() for item in joining_prep]
    else:
        result["joining_prep"] = []

    return {
        "plan": result,
        "status": "plan_generated",
    }


async def human_review(
    state: OnboardingState, config: RunnableConfig
) -> Command:
    """Pause for human review of the generated plan."""
    logger.info("workflow_node_started", node="human_review")

    user_input = interrupt({
        "plan": state.get("plan", {}),
        "message": "Please review the onboarding plan. Approve or provide feedback for revision.",
    })

    if isinstance(user_input, dict):
        action = user_input.get("action", "approve")
        feedback = user_input.get("feedback", "")
    elif isinstance(user_input, str):
        action = "approve" if user_input.lower() in ("approve", "yes", "ok") else "revise"
        feedback = user_input if action == "revise" else ""
    else:
        action = "approve"
        feedback = ""

    if action == "revise" and feedback:
        return Command(
            update={"feedback": feedback, "status": "revising"},
            goto="generate_plan",
        )

    return Command(
        update={"status": "approved"},
        goto=END,
    )


async def coaching_session(
    state: OnboardingState, config: RunnableConfig
) -> dict:
    """Call OnboardingCoachAgent for confidential situation coaching."""
    logger.info(
        "workflow_node_started",
        node="coaching_session",
        query_len=len(state.get("coaching_query", "")),
    )

    result = await onboarding_coach_agent(state, config)

    return {
        "coaching_response": result.get("coaching_response", ""),
        "status": "coaching_complete",
    }


async def coaching_followup(
    state: OnboardingState, config: RunnableConfig
) -> Command:
    """HITL interrupt for coaching follow-up questions."""
    logger.info("workflow_node_started", node="coaching_followup")

    user_input = interrupt({
        "coaching_response": state.get("coaching_response", ""),
        "message": "Do you have a follow-up question? Provide it or say 'done'.",
    })

    if isinstance(user_input, dict):
        followup = user_input.get("followup", "")
        done = user_input.get("done", False)
    elif isinstance(user_input, str):
        done = user_input.lower() in ("done", "no", "thanks", "exit")
        followup = "" if done else user_input
    else:
        done = True
        followup = ""

    if not done and followup:
        return Command(
            update={"coaching_query": followup, "status": "coaching_followup"},
            goto="coaching_session",
        )

    return Command(
        update={"status": "coaching_done"},
        goto=END,
    )


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None


def build_onboarding_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build and compile the onboarding workflow graph."""
    builder = StateGraph(OnboardingState)

    builder.add_node("generate_plan", generate_plan)
    builder.add_node("human_review", human_review)
    builder.add_node("coaching_session", coaching_session)
    builder.add_node("coaching_followup", coaching_followup)

    builder.add_edge(START, "generate_plan")
    builder.add_edge("generate_plan", "human_review")
    builder.add_edge("coaching_session", "coaching_followup")

    return builder.compile(checkpointer=checkpointer)


def init_onboarding_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Initialize the module-level onboarding graph singleton."""
    global _compiled_graph
    _compiled_graph = build_onboarding_graph(checkpointer=checkpointer)
    return _compiled_graph


def get_onboarding_graph() -> CompiledStateGraph:
    """Get the compiled onboarding graph, initializing if needed."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_onboarding_graph()
    return _compiled_graph
