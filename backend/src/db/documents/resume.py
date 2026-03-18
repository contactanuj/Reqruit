"""
Resume document model — uploaded and parsed resume data.

Users can upload multiple resume versions. One is marked as the "master"
resume — the complete version that agents use as the source of truth for
skills, experience, and education.

Design decisions
----------------
Why store raw_text alongside parsed_data:
    The raw text is the unstructured content extracted from PDF/DOCX. The
    parsed data is a structured breakdown (work experience, education,
    skills) created by the ResumeParser agent.

    We keep both because:
    - raw_text is used for RAG chunking and embedding generation
    - parsed_data is used by agents that need structured field access
    - Re-parsing is expensive (requires an LLM call), so caching the
      result in parsed_data avoids redundant API calls

Why is_master flag:
    Users may have multiple resume versions (general, technical, management).
    The master resume is the most complete version. Agents default to using
    the master unless a specific version is more appropriate for the target
    job.

    Alternative: always use the most recent resume. Simpler, but users
    often upload targeted versions that are less complete than their master.

Why compound index on (user_id, is_master):
    The most common query is "get the master resume for this user." A
    compound index serves this query in a single index scan, avoiding
    a collection scan followed by a filter.
"""

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class ContactInfo(BaseModel):
    """Embedded contact information extracted from resume."""

    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""


class WorkExperience(BaseModel):
    """Single work experience entry extracted from resume."""

    company: str = ""
    title: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    highlights: list[str] = []


class Education(BaseModel):
    """Single education entry extracted from resume."""

    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""


class ParsedResumeData(BaseModel):
    """
    Structured resume data extracted by the ResumeParser agent.

    This is an embedded sub-model (BaseModel, not Document) stored inline
    within the Resume document. It is never queried independently — always
    accessed through its parent Resume.
    """

    contact_info: ContactInfo = ContactInfo()
    work_experience: list[WorkExperience] = []
    education: list[Education] = []
    skills: list[str] = []
    certifications: list[str] = []
    languages: list[str] = []


class Resume(TimestampedDocument):
    """
    Uploaded resume with raw text and parsed structured data.

    Fields:
        user_id: Owner of this resume.
        title: User-provided label (e.g., "General Resume", "Tech Lead Version").
        raw_text: Full text extracted from PDF/DOCX. Used for RAG chunking.
        parsed_data: Structured breakdown by ResumeParser agent. None until parsed.
        file_name: Original uploaded file name.
        version: Auto-incremented version number per user.
        is_master: True for the primary/complete resume.
    """

    user_id: Indexed(PydanticObjectId)
    title: str = ""
    raw_text: str = ""
    parsed_data: ParsedResumeData | None = None
    file_name: str = ""
    version: int = 1
    is_master: bool = False
    parse_status: str = "pending"  # "pending" | "processing" | "completed" | "failed"

    class Settings:
        name = "resumes"
        indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("is_master", ASCENDING)],
                name="user_master_idx",
            ),
        ]
