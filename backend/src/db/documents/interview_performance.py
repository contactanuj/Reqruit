"""
Interview performance document — tracks mock interview session outcomes.

InterviewPerformance stores per-session scoring data from the adaptive
interview coach. Each session contains multiple QuestionScore entries
(one per question asked), plus an overall assessment. Data is queried
across sessions for longitudinal trend analysis.

Design decisions
----------------
Why a separate collection (not embedded in Interview):
    Performance data has an independent lifecycle — it is queried across
    sessions for trend analysis and improvement tracking. Embedding in
    Interview would require loading all interview data just to compute
    score trends. A separate collection with its own indexes is the
    correct choice for cross-session aggregation.

Why session_id as a UUID string (not ObjectId):
    Sessions are identified before the document is inserted into MongoDB.
    The graph creates a session_id at workflow start and uses it throughout
    the HITL flow. A UUID string generated in application code is more
    portable than a MongoDB ObjectId.
"""

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class QuestionScore(BaseModel):
    """Per-question scoring from the interview coach."""

    question_text: str
    question_type: str = ""  # behavioral, technical, situational, aptitude
    score_relevance: int = 0  # 1-5
    score_structure: int = 0  # 1-5 (STAR adherence)
    score_specificity: int = 0  # 1-5
    score_confidence: int = 0  # 1-5
    feedback: str = ""
    improvement_suggestion: str = ""


class InterviewPerformance(TimestampedDocument):
    """
    Mock interview session performance record.

    Fields:
        user_id: The user who completed the session.
        session_id: UUID string identifying this session (unique per user).
        company_name: Target company for the mock interview.
        role_title: Target role.
        difficulty_level: Session difficulty (easy, medium, hard).
        question_scores: Per-question scoring data.
        overall_score: Average score across all questions.
        strengths: Areas where the user performed well.
        improvement_areas: Areas needing work.
        session_summary: AI-generated session debrief.
    """

    user_id: Indexed(PydanticObjectId)
    session_id: str
    company_name: str = ""
    role_title: str = ""
    difficulty_level: str = "medium"
    question_scores: list[QuestionScore] = []
    overall_score: float = 0.0
    strengths: list[str] = []
    improvement_areas: list[str] = []
    session_summary: str = ""

    class Settings:
        name = "interview_performances"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("session_id", ASCENDING)],
                name="user_session_idx",
                unique=True,
            ),
            IndexModel(
                [("user_id", ASCENDING), ("created_at", DESCENDING)],
                name="user_recent_idx",
            ),
        ]
