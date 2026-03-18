"""
Interview coach workflow graph — adaptive mock interview sessions.

Graph structure
---------------
::

    START -> predict_questions -> present_question -> evaluate_answer -> route_next
                                       ^                                    |
                                       |_______ (more questions) ___________|
                                                                            |
                                                               (done) -> debrief -> save_performance -> END

Node responsibilities:
    predict_questions: Calls QuestionPredictor to generate 10 predicted questions.
    present_question: Selects the next question and pauses for user's answer via interrupt().
    evaluate_answer: Calls InterviewCoach to evaluate the answer on 4 dimensions.
    route_next: Conditional edge — loops back for more questions or proceeds to debrief.
    debrief: Generates overall session assessment from accumulated scores.
"""

import json

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from beanie import PydanticObjectId

from src.agents.company_patterns import CAMPUS_PLACEMENT_ROUNDS
from src.agents.interview_coach import InterviewCoachAgent
from src.agents.question_predictor import QuestionPredictorAgent
from src.db.documents.interview_performance import InterviewPerformance, QuestionScore
from src.rag.retriever import semantic_search
from src.repositories.interview_performance_repository import InterviewPerformanceRepository
from src.workflows.states.interview_coach import InterviewCoachState

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Agent singletons
# ---------------------------------------------------------------------------

_predictor = QuestionPredictorAgent()
_coach = InterviewCoachAgent()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


async def predict_questions(
    state: InterviewCoachState, config: RunnableConfig
) -> dict:
    """Generate predicted interview questions for the role."""
    logger.info("workflow_node_started", node="predict_questions")
    # Use jd_text as fallback if jd_analysis is empty
    effective_state = dict(state)
    if not effective_state.get("jd_analysis") and effective_state.get("jd_text"):
        effective_state["jd_analysis"] = effective_state["jd_text"]
    result = await _predictor(effective_state, config)
    result["status"] = "predicting"
    result["current_question_index"] = 0
    return result


async def present_question(
    state: InterviewCoachState, config: RunnableConfig
) -> dict:
    """Present the current question and wait for the user's answer."""
    logger.info("workflow_node_started", node="present_question")

    predicted = state.get("predicted_questions", "[]")
    index = state.get("current_question_index", 0)
    question_type = ""

    # Parse questions — handle both JSON array and plain text
    try:
        questions = json.loads(predicted)
        if isinstance(questions, list) and index < len(questions):
            q = questions[index]
            if isinstance(q, dict):
                question_text = q.get("question_text", str(q))
                question_type = q.get("question_type", "")
            else:
                question_text = str(q)
        else:
            question_text = f"Question {index + 1}"
    except (json.JSONDecodeError, TypeError):
        question_text = f"Question {index + 1}: {predicted}"

    # Retrieve relevant STAR stories from Weaviate
    user_id = config["configurable"].get("user_id", "")
    coaching_hints = ""
    star_stories_text = ""
    star_story_titles: list[str] = []

    if user_id and question_text:
        try:
            stories = await semantic_search(
                "STARStoryEmbedding",
                question_text,
                tenant=user_id,
                limit=3,
            )
            if stories:
                star_parts = []
                for s in stories:
                    props = s.get("properties", {})
                    title = props.get("title", "Untitled")
                    star_story_titles.append(title)
                    star_parts.append(
                        f"- **{title}**: {props.get('situation', '')[:100]}..."
                    )
                coaching_hints = (
                    "Relevant stories from your experience:\n"
                    + "\n".join(star_parts)
                )
                star_stories_text = "\n\n".join(
                    f"Story: {s.get('properties', {}).get('title', '')}\n"
                    f"Situation: {s.get('properties', {}).get('situation', '')}\n"
                    f"Action: {s.get('properties', {}).get('action', '')}\n"
                    f"Result: {s.get('properties', {}).get('result', '')}"
                    for s in stories
                )
            else:
                coaching_hints = (
                    "No matching STAR stories found. "
                    "Consider creating stories related to this topic."
                )
        except Exception:
            logger.warning("star_story_retrieval_failed", question=question_text[:50])
            coaching_hints = "STAR story retrieval temporarily unavailable."

    # Pause for user's answer
    user_input = interrupt({
        "current_question": question_text,
        "question_index": index,
        "question_type": question_type,
        "difficulty_level": state.get("difficulty_level", "medium"),
        "coaching_hints": coaching_hints,
        "star_stories_used": star_story_titles,
        "message": "Please answer the interview question.",
    })

    answer = user_input.get("answer", "")

    return {
        "current_question": question_text,
        "current_question_type": question_type,
        "user_answer": answer,
        "star_stories": star_stories_text,
        "status": "coaching",
    }


async def evaluate_answer(
    state: InterviewCoachState, config: RunnableConfig
) -> dict:
    """Evaluate the user's answer and update session scores."""
    logger.info("workflow_node_started", node="evaluate_answer")

    result = await _coach(state, config)

    # Accumulate scores
    scores = list(state.get("session_scores", []))
    evaluation = result.get("evaluation", "")

    score_entry = {
        "question_text": state.get("current_question", ""),
        "question_type": state.get("current_question_type", ""),
        "evaluation": evaluation,
    }

    # Try to parse evaluation for numeric scores
    try:
        eval_data = json.loads(evaluation)
        if isinstance(eval_data, dict):
            score_entry.update({
                "score_relevance": eval_data.get("score_relevance", 0),
                "score_structure": eval_data.get("score_structure", 0),
                "score_specificity": eval_data.get("score_specificity", 0),
                "score_confidence": eval_data.get("score_confidence", 0),
                "feedback": eval_data.get("feedback", ""),
                "improvement_suggestion": eval_data.get("improvement_suggestion", ""),
            })
    except (json.JSONDecodeError, TypeError):
        pass

    scores.append(score_entry)

    # Adjust difficulty based on running average
    old_difficulty = state.get("difficulty_level", "medium")
    difficulty = old_difficulty
    if len(scores) >= 3:
        recent_avgs = []
        for s in scores[-3:]:
            score_vals = [
                s.get("score_relevance", 0),
                s.get("score_structure", 0),
                s.get("score_specificity", 0),
                s.get("score_confidence", 0),
            ]
            avg = sum(score_vals) / len(score_vals) if any(score_vals) else 0
            recent_avgs.append(avg)
        overall_recent = sum(recent_avgs) / len(recent_avgs) if recent_avgs else 0

        if overall_recent > 4.0 and difficulty != "hard":
            difficulty = "hard" if difficulty == "medium" else "medium"
        elif overall_recent < 2.5 and difficulty != "easy":
            difficulty = "easy" if difficulty == "medium" else "medium"

        if difficulty != old_difficulty:
            logger.info(
                "difficulty_adjusted",
                old=old_difficulty,
                new=difficulty,
                avg_score=overall_recent,
            )

    result["session_scores"] = scores
    result["difficulty_level"] = difficulty
    result["status"] = "evaluating"
    return result


def route_next(state: InterviewCoachState) -> str:
    """Route to next question, next campus round, or debrief."""
    predicted = state.get("predicted_questions", "[]")
    index = state.get("current_question_index", 0)

    try:
        questions = json.loads(predicted)
        total = len(questions) if isinstance(questions, list) else 0
    except (json.JSONDecodeError, TypeError):
        total = 0

    if index < total - 1:
        return "present_question"

    # For campus placement, check if there are more rounds
    mode = state.get("interview_mode", "standard")
    if mode == "campus_placement":
        round_type = state.get("round_type", "aptitude")
        if round_type in CAMPUS_PLACEMENT_ROUNDS:
            current_idx = CAMPUS_PLACEMENT_ROUNDS.index(round_type)
            if current_idx < len(CAMPUS_PLACEMENT_ROUNDS) - 1:
                return "advance_round"

    return "debrief"


async def advance_index(
    state: InterviewCoachState, config: RunnableConfig
) -> dict:
    """Increment the question index before presenting the next question."""
    return {"current_question_index": state.get("current_question_index", 0) + 1}


async def advance_round(
    state: InterviewCoachState, config: RunnableConfig
) -> dict:
    """Transition to the next campus placement round."""
    round_type = state.get("round_type", "aptitude")
    current_idx = CAMPUS_PLACEMENT_ROUNDS.index(round_type) if round_type in CAMPUS_PLACEMENT_ROUNDS else 0
    if current_idx >= len(CAMPUS_PLACEMENT_ROUNDS) - 1:
        logger.warning("advance_round_called_on_last_round", round_type=round_type)
        return {"status": "complete"}
    next_round = CAMPUS_PLACEMENT_ROUNDS[current_idx + 1]
    logger.info("campus_round_advanced", old_round=round_type, new_round=next_round)
    return {
        "round_type": next_round,
        "current_question_index": 0,
        "predicted_questions": "",
        "current_round_index": current_idx + 1,
    }


def _calc_overall_score(scores: list[dict]) -> float:
    """Calculate overall score as average of per-question dimension averages."""
    total_scores = []
    for s in scores:
        vals = [
            s.get("score_relevance", 0),
            s.get("score_structure", 0),
            s.get("score_specificity", 0),
            s.get("score_confidence", 0),
        ]
        if any(vals):
            total_scores.append(sum(vals) / len(vals))
    return sum(total_scores) / len(total_scores) if total_scores else 0.0


def _parse_assessment(text: str) -> tuple[list[str], list[str], list[str]]:
    """Parse strengths, weaknesses, recommendations from LLM assessment text."""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return (
                data.get("strengths", []),
                data.get("weaknesses", []),
                data.get("recommendations", []),
            )
    except (json.JSONDecodeError, TypeError):
        pass
    return [], [], []


async def debrief(
    state: InterviewCoachState, config: RunnableConfig
) -> dict:
    """Generate rich session assessment via InterviewCoachAgent in summary mode."""
    logger.info("workflow_node_started", node="debrief")

    scores = state.get("session_scores", [])
    overall = _calc_overall_score(scores)

    # Build summary-oriented state for the coach agent
    summary_state = {
        "current_question": "SESSION_SUMMARY",
        "user_answer": json.dumps(scores),
        "star_stories": state.get("star_stories", ""),
        "difficulty_level": state.get("difficulty_level", "medium"),
        "session_scores": scores,
    }

    try:
        result = await _coach(summary_state, config)
        assessment_raw = result.get("evaluation", "")
    except Exception:
        logger.warning("debrief_agent_call_failed")
        assessment_raw = ""

    strengths, weaknesses, recommendations = _parse_assessment(assessment_raw)

    assessment = json.dumps({
        "summary": assessment_raw,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "overall_score": round(overall, 1),
        "question_count": len(scores),
    })

    logger.info(
        "debrief_generated",
        question_count=len(scores),
        overall_score=round(overall, 1),
    )

    return {
        "overall_assessment": assessment,
        "status": "complete",
    }


async def save_performance(
    state: InterviewCoachState, config: RunnableConfig
) -> dict:
    """Persist InterviewPerformance document from debrief data."""
    logger.info("workflow_node_started", node="save_performance")

    user_id = config["configurable"].get("user_id", "")
    session_id = state.get("session_id", config["configurable"].get("thread_id", ""))

    # Parse assessment
    try:
        assessment = json.loads(state.get("overall_assessment", "{}"))
    except (json.JSONDecodeError, TypeError):
        assessment = {}

    # Map session_scores to QuestionScore entries
    question_scores = [
        QuestionScore(
            question_text=s.get("question_text", ""),
            question_type=s.get("question_type", ""),
            score_relevance=s.get("score_relevance", 0),
            score_structure=s.get("score_structure", 0),
            score_specificity=s.get("score_specificity", 0),
            score_confidence=s.get("score_confidence", 0),
            feedback=s.get("feedback", ""),
            improvement_suggestion=s.get("improvement_suggestion", ""),
        )
        for s in state.get("session_scores", [])
    ]

    try:
        perf = InterviewPerformance(
            user_id=PydanticObjectId(user_id),
            session_id=session_id,
            company_name=state.get("company_name", ""),
            role_title=state.get("role_title", ""),
            difficulty_level=state.get("difficulty_level", "medium"),
            question_scores=question_scores,
            overall_score=assessment.get("overall_score", 0.0),
            strengths=assessment.get("strengths", []),
            improvement_areas=assessment.get("weaknesses", []),
            session_summary=assessment.get("summary", ""),
        )

        repo = InterviewPerformanceRepository()
        await repo.create(perf)
        logger.info("performance_auto_saved", session_id=session_id, user_id=user_id)
    except Exception:
        logger.warning("performance_auto_save_failed", session_id=session_id)

    return {"status": "complete"}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_interview_coach_graph(
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Build and compile the interview coach workflow graph."""
    builder = StateGraph(InterviewCoachState)

    builder.add_node("predict_questions", predict_questions)
    builder.add_node("present_question", present_question)
    builder.add_node("evaluate_answer", evaluate_answer)
    builder.add_node("advance_index", advance_index)
    builder.add_node("advance_round", advance_round)
    builder.add_node("debrief", debrief)
    builder.add_node("save_performance", save_performance)

    builder.add_edge(START, "predict_questions")
    builder.add_edge("predict_questions", "present_question")
    builder.add_edge("present_question", "evaluate_answer")
    builder.add_conditional_edges(
        "evaluate_answer",
        route_next,
        {
            "present_question": "advance_index",
            "advance_round": "advance_round",
            "debrief": "debrief",
        },
    )
    builder.add_edge("advance_index", "present_question")
    builder.add_edge("advance_round", "predict_questions")
    builder.add_edge("debrief", "save_performance")
    builder.add_edge("save_performance", END)

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None


def init_interview_coach_graph(checkpointer: BaseCheckpointSaver) -> None:
    """Build and cache the interview coach graph. Call once at startup."""
    global _compiled_graph
    _compiled_graph = build_interview_coach_graph(checkpointer)
    logger.info("interview_coach_graph_initialized")


def get_interview_coach_graph() -> CompiledStateGraph:
    """Return the cached compiled graph. Raises RuntimeError if not initialized."""
    if _compiled_graph is None:
        raise RuntimeError(
            "Interview coach graph not initialized. "
            "Call init_interview_coach_graph() first."
        )
    return _compiled_graph
