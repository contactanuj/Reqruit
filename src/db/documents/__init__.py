"""
Beanie document models — each file defines one MongoDB collection.

Documents are Pydantic models, so the same class serves as:
  1. MongoDB document definition (schema, indexes, collection name)
  2. Validation rules (field types, constraints, defaults)
  3. API-compatible data structures (serializable to JSON)

ALL_DOCUMENT_MODELS is the list registered with init_beanie during startup.
Only concrete document classes go here — not the TimestampedDocument base.
"""

from src.db.documents.application import Application
from src.db.documents.company import Company
from src.db.documents.contact import Contact
from src.db.documents.document_record import DocumentRecord
from src.db.documents.interview import Interview
from src.db.documents.job import Job
from src.db.documents.llm_usage import LLMUsage
from src.db.documents.outreach_message import OutreachMessage
from src.db.documents.profile import Profile
from src.db.documents.resume import Resume
from src.db.documents.star_story import STARStory
from src.db.documents.user import User

# All document classes registered with Beanie during init_beanie().
# Order does not matter — Beanie resolves dependencies internally.
ALL_DOCUMENT_MODELS: list[type] = [
    User,
    Profile,
    Resume,
    Job,
    Company,
    Contact,
    Application,
    DocumentRecord,
    OutreachMessage,
    Interview,
    STARStory,
    LLMUsage,
]

__all__ = [
    "ALL_DOCUMENT_MODELS",
    "Application",
    "Company",
    "Contact",
    "DocumentRecord",
    "Interview",
    "Job",
    "LLMUsage",
    "OutreachMessage",
    "Profile",
    "Resume",
    "STARStory",
    "User",
]
