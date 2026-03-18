"""
State definition for the interview coach workflow.

Tracks the adaptive mock interview session: question prediction, individual
question/answer cycles with scoring, and final debrief.
"""

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class InterviewCoachState(TypedDict):
    """
    Full state for the adaptive interview coach workflow.

    Attributes:
        messages: Append-only conversation history.
        company_name: Target company.
        role_title: Target role.
        jd_analysis: Structured JD analysis.
        company_research: Company culture/interview signals.
        locale_context: Market-specific interview norms.
        predicted_questions: JSON array from QuestionPredictor.
        current_question_index: Index into predicted_questions.
        current_question: The question currently being asked.
        user_answer: The candidate's answer to the current question.
        difficulty_level: Current difficulty (easy/medium/hard).
        evaluation: Current question evaluation from coach.
        session_scores: List of QuestionScore dicts accumulated over session.
        star_stories: Relevant STAR stories from Weaviate.
        overall_assessment: Final session summary.
        status: Workflow lifecycle stage.
    """

    messages: Annotated[list, add_messages]
    company_name: str
    role_title: str
    jd_analysis: str
    company_research: str
    locale_context: str
    predicted_questions: str
    current_question_index: int
    current_question: str
    current_question_type: str
    user_answer: str
    difficulty_level: str
    evaluation: str
    session_scores: list
    star_stories: str
    overall_assessment: str
    status: str
    jd_text: str
    session_id: str
    job_id: str
    interview_mode: str
    round_type: str
    company_pattern: str
    current_round_index: int
