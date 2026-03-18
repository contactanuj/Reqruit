"""
Cover letter workflow graph — the first complete LangGraph workflow.

This graph demonstrates all the key patterns that the remaining 3 workflows
will follow: multi-node processing, typed state, human-in-the-loop (HITL)
review, revision loops, and checkpoint-based persistence.

Graph structure
---------------
::

    START -> analyze_requirements -> retrieve_memories -> write_cover_letter -> human_review
                                                               ^                    |
                                                               |___ (revision) _____|
                                                                                    |
                                                                               (approved) -> END

Node responsibilities:
    analyze_requirements: Calls RequirementsAnalyst to extract key requirements
        from the job description. Sets status="analyzing".
    retrieve_memories: Fetches relevant context from the memory system (past
        cover letters, resume chunks) and stores it in state["memory_context"].
        Runs between analysis and writing so the writer has context available.
    write_cover_letter: Calls CoverLetterWriter to generate (or revise) the
        cover letter. Sets status="writing".
    human_review: Pauses execution with interrupt() so the caller can present
        the draft to the user. Resumes with Command(resume={"action": ...}).
        On "approve" -> sets status="approved", routes to END.
        On "revise" -> stores feedback, sets status="revision_requested",
        routes back to write_cover_letter.

Design decisions
----------------
Why module-level agent singletons (not created per-invocation):
    Agent instances are stateless — they hold only their name, task type, and
    system prompt. Creating them once at module load avoids repeated object
    creation. All per-invocation data flows through the state dict.

Why thin wrapper functions around agents (not passing agents directly):
    The wrapper functions add status updates and (for human_review) HITL logic
    that doesn't belong in the agent class. This keeps BaseAgent subclasses
    focused on LLM interaction while workflow-specific orchestration stays in
    the graph module.

Why interrupt() inside the node (not interrupt_before/interrupt_after):
    The interrupt() function (LangGraph 0.2.57+) lets us prepare a review
    payload *inside* the node, pause, and then handle the user's response in
    the same function. More flexible than interrupt_before (which pauses
    before the node runs) because we can include the cover letter draft in
    the interrupt value.
"""

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from src.agents.base import _extract_user_id
from src.agents.cover_letter import CoverLetterWriter, RequirementsAnalyst
from src.memory.retrieval import retrieve_memories as _retrieve_memories
from src.workflows.states.cover_letter import CoverLetterState

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Agent singletons — stateless, safe to reuse across invocations
# ---------------------------------------------------------------------------

_analyst = RequirementsAnalyst()
_writer = CoverLetterWriter()


# ---------------------------------------------------------------------------
# Node functions — thin wrappers that add status tracking and HITL logic
# ---------------------------------------------------------------------------


async def analyze_requirements(
    state: CoverLetterState, config: RunnableConfig
) -> dict:
    """
    Extract key requirements from the job description.

    Delegates to RequirementsAnalyst, which reads state["job_description"]
    and returns {"requirements_analysis": "..."}.
    """
    logger.info("workflow_node_started", node="analyze_requirements")
    result = await _analyst(state, config)
    result["status"] = "analyzing"
    return result


async def retrieve_memories_node(
    state: CoverLetterState, config: RunnableConfig
) -> dict:
    """
    Fetch relevant context from the memory system for the cover letter writer.

    Searches Weaviate for resume chunks and past cover letters that match
    the job requirements. The results are stored in state["memory_context"]
    so the CoverLetterWriter can include them in its prompt.

    Gracefully degrades — if memory retrieval fails (e.g., no tenant exists
    for a new user, embedding service not ready), returns empty context
    rather than crashing the workflow.
    """
    logger.info("workflow_node_started", node="retrieve_memories")

    user_id = _extract_user_id(config)
    query = state.get("requirements_analysis", "") or state.get("job_description", "")

    try:
        context = await _retrieve_memories(
            agent_name="cover_letter_writer",
            query=query,
            user_id=user_id,
        )
        return {"memory_context": context.formatted}
    except Exception:
        logger.warning(
            "memory_retrieval_skipped",
            node="retrieve_memories",
            exc_info=True,
        )
        return {"memory_context": ""}


async def write_cover_letter(
    state: CoverLetterState, config: RunnableConfig
) -> dict:
    """
    Generate or revise the cover letter.

    Delegates to CoverLetterWriter, which reads requirements_analysis,
    resume_text, and optionally feedback + previous cover_letter from state.
    """
    logger.info("workflow_node_started", node="write_cover_letter")
    result = await _writer(state, config)
    result["status"] = "writing"
    return result


async def human_review(state: CoverLetterState, config: RunnableConfig) -> Command:
    """
    Pause for human review of the cover letter draft.

    Calls interrupt() with the current draft, which suspends the graph
    and returns control to the caller. The caller presents the draft to
    the user and resumes with:

        Command(resume={"action": "approve"})
        Command(resume={"action": "revise", "feedback": "..."})

    On approve: updates status to "approved" and routes to END.
    On revise: stores the feedback, updates status to "revision_requested",
    and routes back to write_cover_letter.
    """
    logger.info(
        "workflow_node_started",
        node="human_review",
        cover_letter_length=len(state.get("cover_letter", "")),
    )

    # Pause execution — the caller gets this value and decides what to do.
    review_decision = interrupt({
        "cover_letter": state.get("cover_letter", ""),
        "requirements_analysis": state.get("requirements_analysis", ""),
        "message": "Please review the cover letter draft.",
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
            goto="write_cover_letter",
        )

    # Default: approve
    logger.info("human_review_approved")
    return Command(
        update={"status": "approved"},
        goto=END,
    )


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------


def _route_after_review(state: CoverLetterState) -> str:
    """
    Route after human_review based on the user's decision.

    This is used as a fallback routing function. In practice, human_review
    returns a Command that explicitly sets the next node, so this function
    serves as documentation and a safety net.
    """
    if state.get("status") == "revision_requested":
        return "write_cover_letter"
    return END


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_cover_letter_graph(
    checkpointer: BaseCheckpointSaver,
) -> StateGraph:
    """
    Build and compile the cover letter workflow graph.

    Args:
        checkpointer: A LangGraph checkpointer (MongoDBSaver in production,
            MemorySaver in tests) that persists graph state between
            invocations. Required for HITL — without it, the graph can't
            resume after an interrupt.

    Returns:
        A compiled StateGraph ready for .ainvoke() or .astream().
    """
    builder = StateGraph(CoverLetterState)

    # Nodes
    builder.add_node("analyze_requirements", analyze_requirements)
    builder.add_node("retrieve_memories", retrieve_memories_node)
    builder.add_node("write_cover_letter", write_cover_letter)
    builder.add_node("human_review", human_review)

    # Edges: START -> analyze -> retrieve_memories -> write -> review
    builder.add_edge(START, "analyze_requirements")
    builder.add_edge("analyze_requirements", "retrieve_memories")
    builder.add_edge("retrieve_memories", "write_cover_letter")
    builder.add_edge("write_cover_letter", "human_review")

    # human_review uses Command to route explicitly, but we still need
    # to declare the possible targets so LangGraph knows the graph structure.
    # An edge from human_review isn't needed because Command handles routing.

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Module-level graph singleton — built once on startup, reused per request.
# CompiledStateGraph is thread-safe and stateless (state lives in the
# checkpointer, not in the graph object itself).
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None


def init_cover_letter_graph(checkpointer: BaseCheckpointSaver) -> None:
    """Build and cache the cover letter graph. Call once at application startup."""
    global _compiled_graph
    _compiled_graph = build_cover_letter_graph(checkpointer)
    logger.info("cover_letter_graph_initialized")


def get_cover_letter_graph() -> CompiledStateGraph:
    """Return the cached compiled graph. Raises RuntimeError if not initialized."""
    if _compiled_graph is None:
        raise RuntimeError(
            "Cover letter graph not initialized. Call init_cover_letter_graph() first."
        )
    return _compiled_graph
