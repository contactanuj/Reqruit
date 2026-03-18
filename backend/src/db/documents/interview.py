"""
Interview document model — interview records and preparation data.

Interviews are created during the Prepare workflow (Stage 4) when a user
advances to the interview stage. The QuestionGenerator and CompanyBrief
agents populate preparation materials, and the MockInterviewer agent uses
this data for practice sessions.

Design decisions
----------------
Why embed InterviewNotes (not a separate collection):
    Notes are tightly coupled to their interview — they are never queried
    independently and have no lifecycle outside the parent. Embedding
    keeps the data together and avoids a join.

Why questions as a list of strings (not a sub-model):
    Interview questions are simple text strings. Adding structure (category,
    difficulty, source) would be premature optimization — the agents
    generate free-form questions and users just need to see the list.
    We can promote to a sub-model later if structured question data
    becomes valuable.

Why denormalized company_name and role_title:
    When displaying interview details, we need the company name and role
    without joining through Application -> Job -> Company. These fields
    rarely change once an interview is scheduled, so denormalization is
    safe and efficient.
"""

from datetime import datetime

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument
from src.db.documents.enums import InterviewType


class InterviewNotes(BaseModel):
    """
    Embedded interview notes and follow-up items.

    Populated during or after an interview. The follow_up_items list
    tracks action items that came out of the interview (e.g., "send
    portfolio link", "prepare system design for round 2").
    """

    key_points: list[str] = []
    follow_up_items: list[str] = []


class GeneratedQuestion(BaseModel):
    """AI-generated behavioral question with a suggested STAR story angle."""

    question: str = ""
    suggested_angle: str = ""


class Interview(TimestampedDocument):
    """
    Interview record with preparation materials and notes.

    Fields:
        application_id: The application this interview belongs to.
        scheduled_at: When the interview is scheduled. None if not yet set.
        interview_type: Type of interview (phone_screen, technical, etc.).
        company_name: Denormalized for display.
        role_title: Denormalized for display.
        interviewer_name: Name of the interviewer if known.
        notes: Embedded key points and follow-up items.
        questions: List of practice/actual interview questions.
        preparation_notes: Free-text preparation notes from CompanyBrief agent.
    """

    user_id: Indexed(PydanticObjectId)
    application_id: Indexed(PydanticObjectId)
    scheduled_at: datetime | None = None
    interview_type: InterviewType = InterviewType.PHONE_SCREEN
    company_name: str = ""
    role_title: str = ""
    interviewer_name: str = ""
    notes: InterviewNotes = InterviewNotes()
    questions: list[str] = []
    generated_questions: list[GeneratedQuestion] = []
    preparation_notes: str = ""

    class Settings:
        name = "interviews"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("application_id", ASCENDING)],
                name="user_application_idx",
            ),
        ]
