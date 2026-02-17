"""
Contact document model — points of contact at target companies.

Contacts are people at companies the user may want to reach out to.
They are discovered by the POCFinder agent during Job Discovery (Stage 2)
and used by the OutreachComposer agent during the Application workflow
(Stage 3).

Design decisions
----------------
Why a separate collection (not embedded in Company):
    A company can have many contacts, and contacts have their own lifecycle
    (tracked via contacted flag, contact date). Embedding them would make
    the Company document grow unboundedly. A separate collection lets us
    query contacts independently (e.g., "all uncontacted contacts") and
    paginate results.

    Rule of thumb: embed when the list is bounded and small (like tech_stack).
    Reference when the list can grow without limit (like contacts).

Why contacted flag instead of a separate interactions collection:
    For a single-user tool, a boolean + timestamp is sufficient to track
    outreach status. A full interactions/conversations model would be
    warranted in a multi-user CRM, but adds complexity we do not need yet.
"""

from datetime import datetime

from beanie import Indexed, PydanticObjectId

from src.db.base_document import TimestampedDocument


class Contact(TimestampedDocument):
    """
    Point of contact at a company.

    Fields:
        company_id: Reference to the parent Company document.
        name: Full name of the contact.
        role: Functional role (e.g., "Engineering Manager", "Recruiter").
        title: Exact job title from their profile.
        email: Contact email if known.
        linkedin_url: LinkedIn profile URL for outreach.
        notes: Free-text notes about the contact or past interactions.
        contacted: Whether the user has reached out to this person.
        contacted_at: When the outreach happened. None if not yet contacted.
    """

    company_id: Indexed(PydanticObjectId)
    name: str
    role: str = ""
    title: str = ""
    email: str = ""
    linkedin_url: str = ""
    notes: str = ""
    contacted: bool = False
    contacted_at: datetime | None = None

    class Settings:
        name = "contacts"
