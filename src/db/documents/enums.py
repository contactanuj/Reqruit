"""
Enumerations used across MongoDB document models.

These enums define the allowed values for status fields, type fields, and
other categorical data. Using enums (not raw strings) provides:
- Validation at the Pydantic layer — invalid values are rejected before
  reaching the database.
- IDE autocomplete — no more typos like "interviwing" vs "interviewing".
- Single source of truth — change a value here, it changes everywhere.

All enums use Python's StrEnum (Python 3.11+) so they serialize to plain
strings in MongoDB and JSON. This means the database stores readable values
like "applied" instead of integer codes like 2.

Alternative: use plain string literals with Pydantic's Literal type.
    Literal["saved", "applied", "interviewing"] works for 2-3 values, but
    becomes unwieldy for 6+ options and lacks the grouping, documentation,
    and iteration capabilities that an enum provides.
"""

from enum import StrEnum


class ApplicationStatus(StrEnum):
    """
    Tracks an application through the job hunting pipeline.

    Flow: saved -> applied -> interviewing -> offered -> accepted
                                           -> rejected
          (any state) -> withdrawn
    """

    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DocumentType(StrEnum):
    """Types of AI-generated documents stored in the documents collection."""

    COVER_LETTER = "cover_letter"
    TAILORED_RESUME = "tailored_resume"
    OUTREACH_MESSAGE = "outreach_message"


class MessageType(StrEnum):
    """
    Outreach message variants based on the recipient's role.

    Each type uses a different tone and content strategy:
    - recruiter: formal, highlights qualifications and fit
    - engineer: technical, mentions specific technologies and projects
    - manager: strategic, focuses on team impact and leadership
    - generic: balanced approach when the role is unknown
    """

    RECRUITER = "recruiter"
    ENGINEER = "engineer"
    MANAGER = "manager"
    GENERIC = "generic"


class InterviewType(StrEnum):
    """Types of interviews in the hiring pipeline."""

    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    FINAL = "final"


class RemotePreference(StrEnum):
    """User's preference for remote work arrangements."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    NO_PREFERENCE = "no_preference"
