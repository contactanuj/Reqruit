"""
User document model — authentication and account management.

This is the simplest document in the system. A User represents a registered
account with login credentials. All other collections reference the user's
ObjectId to associate data with a specific person.

Design decisions
----------------
Why email as the unique identifier (not username):
    Email is universally unique, already verified by users, and serves as
    a natural login credential. Username-based systems require an additional
    email field for password resets and notifications anyway.

Why store hashed_password in the same collection (not a separate auth collection):
    For a single-user learning project, the simpler approach is fine.
    In multi-service architectures, separating auth data into its own
    service/collection prevents accidental exposure during user queries.
    We can refactor later if needed.

Why is_active instead of deleting users:
    Soft-delete pattern. Deactivating preserves the user's history
    (applications, documents, STAR stories) for potential reactivation.
    Hard deletion would orphan all referenced documents and require
    cascade-delete logic across 11 other collections.

Why UserLocaleProfile is embedded (not a separate collection):
    Locale profile is always loaded with the user (for middleware injection
    on every agent-triggering request). Making it a separate collection
    would require a join on every request. The data is small (<2KB),
    tightly coupled to the user, and never queried independently.
"""

from datetime import datetime

from beanie import Indexed
from pydantic import BaseModel

from src.db.base_document import TimestampedDocument

# ---------------------------------------------------------------------------
# Locale embedded models
# ---------------------------------------------------------------------------


class LanguageProficiency(BaseModel):
    """A language the user speaks with proficiency level."""

    language: str
    proficiency: str = "PROFESSIONAL"  # NATIVE/FLUENT/PROFESSIONAL/CONVERSATIONAL/BASIC
    script: str = ""


class VisaStatus(BaseModel):
    """User's visa status for a specific country."""

    country: str  # ISO 3166-1 alpha-2
    status: str = "NOT_APPLIED"  # CITIZEN/PR/WORK_VISA/STUDENT_VISA/DEPENDENT/NOT_APPLIED/DENIED


class NoticePeriod(BaseModel):
    """User's current notice period details."""

    contractual_days: int = 0
    served_days: int = 0
    buyout_available: bool = False
    notice_start_date: datetime | None = None
    earliest_joining_date: datetime | None = None


class UserLocaleProfile(BaseModel):
    """
    Embedded locale/market context for a user.

    This data drives locale-aware behavior across all agents and services.
    primary_market determines the default context; target_markets are
    additional markets the user is interested in (e.g., an Indian developer
    targeting US jobs).
    """

    primary_market: str = ""
    target_markets: list[str] = []
    nationality: str = ""
    languages: list[LanguageProficiency] = []
    visa_statuses: list[VisaStatus] = []
    notice_period: NoticePeriod = NoticePeriod()
    career_sector: str = "TECHNOLOGY"
    profile_type: str = "PROFESSIONAL"
    preferred_response_language: str = "en"
    consent_granted_at: datetime | None = None


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class User(TimestampedDocument):
    """
    Registered user account.

    Fields:
        email: Unique login identifier. Indexed for fast lookup during auth.
        hashed_password: bcrypt hash. Never stored or transmitted in plaintext.
        is_active: False = soft-deleted. Inactive users cannot log in.
        locale_profile: Embedded market/locale context. None until user sets it.
    """

    email: Indexed(str, unique=True)
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    usage_tier: str = "free"
    locale_profile: UserLocaleProfile | None = None

    class Settings:
        name = "users"
