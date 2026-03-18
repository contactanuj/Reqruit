"""
Mock interview session document model.

A mock session is created when a user starts a practice interview. The
MockInterviewer agent asks questions from the interview's generated_questions
list, collects user answers, and provides per-question feedback. When the
session is completed, the MockInterviewSummarizer agent generates overall
feedback and a score.

Design decisions
----------------
Why embed QuestionFeedback (not a separate collection):
    Feedback items are tightly coupled to the session — they are never
    queried independently and have no lifecycle outside the parent.

Why current_question_index:
    Tracks progress through the question list so the next question can
    be served without client-side state management.
"""

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument
from src.db.documents.enums import MockSessionStatus


class QuestionFeedback(BaseModel):
    """Per-question feedback from the MockInterviewer agent."""

    question: str = ""
    user_answer: str = ""
    ai_feedback: str = ""
    score: int | None = None


class MockInterviewSession(TimestampedDocument):
    """
    Mock interview practice session.

    Fields:
        user_id: Owner of the session.
        interview_id: The interview this session is for.
        status: Current session status (in_progress, completed, abandoned).
        question_feedbacks: Per-question answer and feedback pairs.
        current_question_index: Index of the next question to ask.
        overall_feedback: Summary feedback from the summarizer agent.
        overall_score: Aggregate score (0-100) from the summarizer.
    """

    user_id: Indexed(PydanticObjectId)
    interview_id: Indexed(PydanticObjectId)
    status: MockSessionStatus = MockSessionStatus.IN_PROGRESS
    question_feedbacks: list[QuestionFeedback] = []
    current_question_index: int = 0
    overall_feedback: str = ""
    overall_score: int | None = None

    class Settings:
        name = "mock_sessions"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("interview_id", ASCENDING)],
                name="user_interview_idx",
            ),
        ]
