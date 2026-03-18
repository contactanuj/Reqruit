"""
Skills analysis workflow graph — mines achievements and analyzes skills.

Graph structure
---------------
::

    START -> mine_achievements -> analyze_skills -> human_review
                                       ^                |
                                       |__ (revision) __|
                                                        |
                                                   (approved) -> END

Node responsibilities:
    mine_achievements: Calls AchievementMiner to extract quantified achievements
        from resume text and work history. Sets status="mining".
    analyze_skills: Calls SkillsAnalyst to map skills from achievements and
        resume. Sets status="analyzing".
    human_review: Pauses for user to verify extracted skills and achievements.
        On approve -> status="approved", routes to END.
        On revise -> stores feedback, status="revision_requested",
        routes back to analyze_skills.
"""

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from src.agents.achievement_miner import AchievementMiner
from src.agents.skills_analyst import SkillsAnalyst
from src.workflows.states.skills_analysis import SkillsAnalysisState

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Agent singletons — stateless, safe to reuse across invocations
# ---------------------------------------------------------------------------

_miner = AchievementMiner()
_analyst = SkillsAnalyst()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


async def mine_achievements(
    state: SkillsAnalysisState, config: RunnableConfig
) -> dict:
    """Extract achievements from resume and work history."""
    logger.info("workflow_node_started", node="mine_achievements")
    result = await _miner(state, config)
    result["status"] = "mining"
    return result


async def analyze_skills(
    state: SkillsAnalysisState, config: RunnableConfig
) -> dict:
    """Map and assess skills from achievements and resume."""
    logger.info("workflow_node_started", node="analyze_skills")
    result = await _analyst(state, config)
    result["status"] = "analyzing"
    return result


async def human_review(
    state: SkillsAnalysisState, config: RunnableConfig
) -> Command:
    """
    Pause for human review of extracted skills and achievements.

    Resume with:
        Command(resume={"action": "approve"})
        Command(resume={"action": "revise", "feedback": "..."})
    """
    logger.info(
        "workflow_node_started",
        node="human_review",
        has_skills=bool(state.get("skills_analysis")),
    )

    review_decision = interrupt({
        "mined_achievements": state.get("mined_achievements", ""),
        "skills_analysis": state.get("skills_analysis", ""),
        "message": "Please review the extracted skills and achievements.",
    })

    action = review_decision.get("action", "approve")

    if action == "revise":
        feedback = review_decision.get("feedback", "")
        logger.info("human_review_revision_requested", feedback_length=len(feedback))
        return Command(
            update={
                "feedback": feedback,
                "status": "revision_requested",
            },
            goto="analyze_skills",
        )

    logger.info("human_review_approved")
    return Command(
        update={"status": "approved"},
        goto=END,
    )


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_skills_analysis_graph(
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """
    Build and compile the skills analysis workflow graph.

    Args:
        checkpointer: LangGraph checkpointer for HITL persistence.

    Returns:
        A compiled StateGraph ready for .ainvoke() or .astream().
    """
    builder = StateGraph(SkillsAnalysisState)

    builder.add_node("mine_achievements", mine_achievements)
    builder.add_node("analyze_skills", analyze_skills)
    builder.add_node("human_review", human_review)

    builder.add_edge(START, "mine_achievements")
    builder.add_edge("mine_achievements", "analyze_skills")
    builder.add_edge("analyze_skills", "human_review")

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None


def init_skills_analysis_graph(checkpointer: BaseCheckpointSaver) -> None:
    """Build and cache the skills analysis graph. Call once at startup."""
    global _compiled_graph
    _compiled_graph = build_skills_analysis_graph(checkpointer)
    logger.info("skills_analysis_graph_initialized")


def get_skills_analysis_graph() -> CompiledStateGraph:
    """Return the cached compiled graph. Raises RuntimeError if not initialized."""
    if _compiled_graph is None:
        raise RuntimeError(
            "Skills analysis graph not initialized. Call init_skills_analysis_graph() first."
        )
    return _compiled_graph
