"""
Application assembly workflow graph — end-to-end job application pipeline.

Graph structure
---------------
::

    START -> decode_jd -> score_fit -> load_locale -> select_resume_blocks
        -> tailor_resume -> generate_cover_letter -> generate_micro_pitch
        -> human_review -> END

Node responsibilities:
    decode_jd: Calls JDDecoder to parse the job description (Story 7.1).
    score_fit: Calls FitScorer to assess candidate-job fit (Story 7.1).
    select_resume_blocks: Weaviate vector search for relevant resume chunks (Story 7.2).
    tailor_resume: ApplicationOrchestratorAgent assembles tailored resume (Story 7.2).
    generate_cover_letter: Stub — Story 7.3.
    generate_micro_pitch: Stub — Story 7.3.
    human_review: Stub — Story 7.4.
"""

import json

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from src.agents.application_orchestrator import ApplicationOrchestratorAgent
from src.agents.cover_letter import CoverLetterWriter
from src.agents.fit_scorer import FitScorer
from src.agents.jd_decoder import JDDecoder
from src.db.documents.user import User
from src.rag.retriever import hybrid_search, semantic_search
from src.repositories.market_config_repository import MarketConfigRepository
from src.services.currency_service import CurrencyService
from src.services.locale_service import LocaleService
from src.workflows.formatters.keyword_optimizer import extract_jd_keywords, optimize_for_naukri
from src.workflows.formatters.locale_formatter import format_resume_instructions, get_formatting_rules
from src.workflows.states.application_assembly import ApplicationAssemblyState

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Agent singletons — stateless, safe to reuse across invocations
# ---------------------------------------------------------------------------

_jd_decoder = JDDecoder()
_fit_scorer = FitScorer()
_orchestrator = ApplicationOrchestratorAgent()
_cover_letter_writer = CoverLetterWriter()
_locale_service = LocaleService(
    market_config_repo=MarketConfigRepository(),
    currency_service=CurrencyService(),
)


# ---------------------------------------------------------------------------
# Functional node functions (Story 7.1)
# ---------------------------------------------------------------------------


async def decode_jd(
    state: ApplicationAssemblyState, config: RunnableConfig
) -> dict:
    """Parse the job description into structured requirements."""
    logger.info("workflow_node_started", node="decode_jd")
    jd_state = {**state, "job_description": state.get("jd_text", "")}
    result = await _jd_decoder(jd_state, config)
    decoded = result.get("jd_analysis", "")
    return {"decoded_jd": decoded, "status": "decoding_jd"}


async def score_fit(
    state: ApplicationAssemblyState, config: RunnableConfig
) -> dict:
    """Assess candidate-job fit based on skills and decoded JD."""
    logger.info("workflow_node_started", node="score_fit")
    result = await _fit_scorer(state, config)
    fit_assessment = result.get("fit_assessment", "")
    return {"fit_analysis": fit_assessment, "status": "scoring_fit"}


# ---------------------------------------------------------------------------
# Locale loading node (Story 7.5)
# ---------------------------------------------------------------------------


async def load_locale(
    state: ApplicationAssemblyState, config: RunnableConfig
) -> dict:
    """Load locale context from user profile and market config.

    Determines the effective market (primary_market or target_market matching JD),
    loads ResumeConventions from MarketConfig, and stores formatting instructions
    in state["locale_context"]. Defaults to US if no locale is set.
    """
    logger.info("workflow_node_started", node="load_locale")
    user_id = config["configurable"]["user_id"]

    user = await User.find_one(User.id == user_id)

    if not user or not user.locale_profile or not user.locale_profile.primary_market:
        logger.info("locale_defaulted_to_us", user_id=user_id)
        rules = get_formatting_rules("US")
        instructions = format_resume_instructions(rules)
        return {
            "locale_context": f"{instructions}\n\nlocale_defaulted: true",
            "locale_defaulted": True,
        }

    locale = user.locale_profile
    effective_market = locale.primary_market

    market_config = await _locale_service.get_market_config(effective_market)
    conventions = market_config.resume_conventions if market_config else None
    rules = get_formatting_rules(effective_market, conventions)
    instructions = format_resume_instructions(rules)

    logger.info(
        "locale_loaded",
        user_id=user_id,
        effective_market=effective_market,
        format_name=rules.format_name,
    )

    return {"locale_context": instructions, "locale_defaulted": False}


# ---------------------------------------------------------------------------
# Functional node functions (Story 7.2)
# ---------------------------------------------------------------------------


async def select_resume_blocks(
    state: ApplicationAssemblyState, config: RunnableConfig
) -> dict:
    """Select resume blocks via Weaviate vector search — NO LLM call.

    Performs hybrid search against the user's ResumeChunk collection using
    JD requirements as the query. Falls back to full resume text if no
    chunks are found (degraded mode, not a failure).
    """
    user_id = config["configurable"]["user_id"]
    decoded_jd = state.get("decoded_jd", "")

    # Parse decoded_jd to extract skills for query
    query_parts = []
    if isinstance(decoded_jd, str):
        try:
            parsed = json.loads(decoded_jd)
            query_parts = parsed.get("required_skills", []) + parsed.get("preferred_skills", [])
        except (json.JSONDecodeError, AttributeError):
            pass

    query_text = ", ".join(query_parts) if query_parts else state.get("jd_text", "")

    logger.info(
        "workflow_node_started",
        node="select_resume_blocks",
        user_id=user_id,
        query_length=len(query_text),
    )

    try:
        results = await hybrid_search(
            collection_name="ResumeChunk",
            query=query_text,
            tenant=str(user_id),
            limit=10,
            alpha=0.7,
        )
    except Exception:
        logger.warning(
            "resume_blocks_search_failed",
            node="select_resume_blocks",
            user_id=user_id,
            exc_info=True,
        )
        results = []

    if not results:
        logger.warning(
            "resume_blocks_empty_fallback",
            node="select_resume_blocks",
            user_id=user_id,
        )
        fallback_text = state.get("resume_text", "")
        return {
            "selected_resume_blocks": json.dumps([{"content": fallback_text, "score": 0.0}]),
            "resume_block_fallback": True,
            "status": "blocks_selected",
        }

    # Serialize results as JSON string (state fields are strings)
    blocks = [
        {"content": r.get("properties", {}).get("content", str(r)), "score": r.get("score", 0.0)}
        for r in results
    ]
    return {
        "selected_resume_blocks": json.dumps(blocks),
        "resume_block_fallback": False,
        "status": "blocks_selected",
    }


async def tailor_resume(
    state: ApplicationAssemblyState, config: RunnableConfig
) -> dict:
    """Assemble selected blocks into a tailored resume via ApplicationOrchestratorAgent."""
    logger.info(
        "workflow_node_started",
        node="tailor_resume",
        user_id=config["configurable"]["user_id"],
    )

    # Build input state matching ApplicationOrchestratorAgent.build_messages() expectations
    agent_state = {
        "jd_analysis": str(state.get("decoded_jd", "")),
        "fit_analysis": str(state.get("fit_analysis", "")),
        "skills_summary": state.get("skills_summary", ""),
        "locale_context": str(state.get("locale_context", "")),
        "relevant_resume_blocks": str(state.get("selected_resume_blocks", "")),
        "messages": state.get("messages", []),
    }

    result = await _orchestrator(agent_state, config)
    tailored = result.get("application_strategy", "")

    update = {
        "tailored_resume": tailored,
        "application_strategy": tailored,
        "status": "resume_tailored",
    }

    # Naukri keyword optimization for IN market
    locale_context = state.get("locale_context", "")
    if "FORMAT FOR IN MARKET" in locale_context:
        decoded_jd = state.get("decoded_jd", "")
        keywords = extract_jd_keywords(decoded_jd)
        report = optimize_for_naukri(keywords, tailored)
        update["keyword_optimization"] = json.dumps({
            "present_keywords": report.present_keywords,
            "missing_keywords": report.missing_keywords,
            "coverage_pct": report.coverage_pct,
            "suggestions": report.suggestions,
        })
        logger.info(
            "keyword_optimization_complete",
            coverage_pct=report.coverage_pct,
            missing_count=len(report.missing_keywords),
        )

    return update


# ---------------------------------------------------------------------------
# Stub node functions — implemented in Stories 7.3-7.4
# ---------------------------------------------------------------------------


async def generate_cover_letter(
    state: ApplicationAssemblyState, config: RunnableConfig
) -> dict:
    """Generate a cover letter using CoverLetterWriter agent."""
    logger.info(
        "workflow_node_started",
        node="generate_cover_letter",
        user_id=config["configurable"]["user_id"],
    )

    # Map graph state keys to CoverLetterWriter.build_messages() expected keys
    agent_state = {
        "resume_text": state.get("tailored_resume") or state.get("resume_text", ""),
        "requirements_analysis": str(state.get("decoded_jd", "")),
        "feedback": state.get("feedback", ""),
        "cover_letter": "",
        "messages": state.get("messages", []),
    }

    result = await _cover_letter_writer(agent_state, config)
    cover_letter = result.get("cover_letter", "")
    return {"cover_letter": cover_letter, "status": "cover_letter_generated"}


async def generate_micro_pitch(
    state: ApplicationAssemblyState, config: RunnableConfig
) -> dict:
    """Generate micro-pitch from STAR stories or resume fallback."""
    user_id = config["configurable"]["user_id"]
    decoded_jd = state.get("decoded_jd", "")

    logger.info("workflow_node_started", node="generate_micro_pitch", user_id=user_id)

    # Parse decoded_jd to extract skills for STAR story query
    query_parts = []
    if isinstance(decoded_jd, str):
        try:
            parsed = json.loads(decoded_jd)
            query_parts = parsed.get("required_skills", [])
        except (json.JSONDecodeError, AttributeError):
            pass

    query_text = ", ".join(query_parts) if query_parts else state.get("jd_text", "")

    # Retrieve STAR stories via semantic search (narrative content, no BM25)
    try:
        star_stories = await semantic_search(
            collection_name="STARStoryEmbedding",
            query=query_text,
            tenant=str(user_id),
            limit=5,
        )
    except Exception:
        logger.warning(
            "star_stories_search_failed",
            node="generate_micro_pitch",
            user_id=user_id,
            exc_info=True,
        )
        star_stories = []

    star_stories_available = len(star_stories) > 0

    if not star_stories_available:
        logger.warning("no_star_stories_fallback", node="generate_micro_pitch", user_id=user_id)

    # Build agent input — include STAR stories when available
    star_text = json.dumps([
        {"content": s.get("properties", {}).get("content", str(s)), "score": s.get("score", 0.0)}
        for s in star_stories
    ]) if star_stories_available else ""

    agent_state = {
        "jd_analysis": str(decoded_jd),
        "fit_analysis": str(state.get("fit_analysis", "")),
        "skills_summary": state.get("skills_summary", ""),
        "locale_context": str(state.get("locale_context", "")),
        "relevant_resume_blocks": str(state.get("selected_resume_blocks", "")),
        "messages": state.get("messages", []),
    }

    # Append STAR stories to resume blocks for the orchestrator
    if star_text:
        agent_state["relevant_resume_blocks"] += f"\n\n## STAR Stories\n{star_text}"

    result = await _orchestrator(agent_state, config)
    pitch_text = result.get("application_strategy", "")

    # Build structured micro_pitch output as JSON string (state fields are strings)
    star_summaries = [
        s.get("properties", {}).get("content", "")[:200]
        for s in star_stories
    ]
    micro_pitch = json.dumps({
        "pitch_text": pitch_text,
        "star_stories_used": star_summaries,
        "star_stories_available": star_stories_available,
    })

    return {
        "micro_pitch": micro_pitch,
        "star_stories_available": star_stories_available,
        "status": "micro_pitch_generated",
    }


async def human_review(
    state: ApplicationAssemblyState, config: RunnableConfig
) -> Command:
    """Pause for human review of the assembled application package.

    Calls interrupt() with the complete package, suspending the graph.
    The caller resumes with Command(resume={"action": "approve|revise|reject", ...}).
    """
    logger.info(
        "workflow_node_started",
        node="human_review",
        has_cover_letter=bool(state.get("cover_letter")),
        has_micro_pitch=bool(state.get("micro_pitch")),
    )

    interrupt_payload = {
        "tailored_resume": state.get("tailored_resume", ""),
        "cover_letter": state.get("cover_letter", ""),
        "micro_pitch": state.get("micro_pitch", ""),
        "fit_analysis": state.get("fit_analysis", ""),
        "application_strategy": state.get("application_strategy", ""),
        "message": "Please review the assembled application materials.",
    }

    # Include keyword optimization warnings for IN market
    keyword_opt = state.get("keyword_optimization", "")
    if keyword_opt:
        interrupt_payload["keyword_optimization"] = keyword_opt

    review_decision = interrupt(interrupt_payload)

    action = review_decision.get("action", "approve")

    if action == "revise":
        feedback = review_decision.get("feedback", "")
        logger.info("human_review_revision_requested", feedback_length=len(feedback))
        return Command(
            update={"feedback": feedback, "status": "revision_requested"},
            goto="tailor_resume",
        )

    if action == "reject":
        logger.info("human_review_rejected")
        return Command(
            update={"status": "rejected"},
            goto=END,
        )

    # Default: approve
    logger.info("human_review_approved")
    return Command(
        update={"status": "approved"},
        goto=END,
    )


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_application_assembly_graph(
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Build and compile the application assembly workflow graph."""
    builder = StateGraph(ApplicationAssemblyState)

    builder.add_node("decode_jd", decode_jd)
    builder.add_node("score_fit", score_fit)
    builder.add_node("load_locale", load_locale)
    builder.add_node("select_resume_blocks", select_resume_blocks)
    builder.add_node("tailor_resume", tailor_resume)
    builder.add_node("generate_cover_letter", generate_cover_letter)
    builder.add_node("generate_micro_pitch", generate_micro_pitch)
    builder.add_node("human_review", human_review)

    builder.add_edge(START, "decode_jd")
    builder.add_edge("decode_jd", "score_fit")
    builder.add_edge("score_fit", "load_locale")
    builder.add_edge("load_locale", "select_resume_blocks")
    builder.add_edge("select_resume_blocks", "tailor_resume")
    builder.add_edge("tailor_resume", "generate_cover_letter")
    builder.add_edge("generate_cover_letter", "generate_micro_pitch")
    builder.add_edge("generate_micro_pitch", "human_review")
    builder.add_edge("human_review", END)

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None


def init_application_assembly_graph(checkpointer: BaseCheckpointSaver) -> None:
    """Build and cache the application assembly graph. Call once at startup."""
    global _compiled_graph
    _compiled_graph = build_application_assembly_graph(checkpointer)
    logger.info("application_assembly_graph_initialized")


def get_application_assembly_graph() -> CompiledStateGraph:
    """Return the cached compiled graph. Raises RuntimeError if not initialized."""
    if _compiled_graph is None:
        raise RuntimeError(
            "Application assembly graph not initialized. "
            "Call init_application_assembly_graph() first."
        )
    return _compiled_graph


def close_application_assembly_graph() -> None:
    """Release the cached graph on shutdown."""
    global _compiled_graph
    _compiled_graph = None
    logger.info("application_assembly_graph_closed")
