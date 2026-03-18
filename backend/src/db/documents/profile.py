"""
Profile document model — user career data and job hunting preferences.

A Profile is created after registration and filled during the Profile Setup
workflow (Stage 1). It captures the user's skills, experience summary,
target roles, and job hunting preferences that guide all downstream agents.

Design decisions
----------------
Why a separate Profile (not embedded in User):
    The User document handles authentication (email, password, active status).
    The Profile handles career data (skills, preferences, target roles).
    Separating them follows the Single Responsibility Principle:
    - Auth operations never need to load career data.
    - Agent workflows access the profile without exposing credentials.

    Alternative: embed profile fields directly in User. Simpler for small
    apps, but mixing auth and career data makes it harder to reason about
    what each agent can access.

Why PydanticObjectId for user_id (not Link):
    Beanie's Link type enables automatic fetching of referenced documents.
    While convenient, it creates implicit database queries — a Link[User]
    field triggers a separate find() call whenever the profile is loaded.

    PydanticObjectId is explicit: it stores just the ObjectId string. When
    you need the related User, you make a deliberate repository call. This
    makes performance predictable and queries visible in code reviews.

    This is the dominant pattern in production Beanie applications where
    query performance matters.
"""

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel

from src.db.base_document import TimestampedDocument
from src.db.documents.embedded import SalaryRange
from src.db.documents.enums import RemotePreference


class UserPreferences(BaseModel):
    """
    Embedded job hunting preferences.

    These preferences guide the JobMatcher (not yet implemented) and JobSearcher agents. They
    are embedded in Profile because they are always read and written
    together with the profile — never queried independently.
    """

    target_salary: SalaryRange = SalaryRange()
    preferred_locations: list[str] = []
    remote_preference: RemotePreference = RemotePreference.NO_PREFERENCE
    willing_to_relocate: bool = False


class Profile(TimestampedDocument):
    """
    User career profile — skills, goals, and preferences.

    One-to-one relationship with User (enforced by unique index on user_id).

    Fields:
        user_id: References the User document. Unique — one profile per user.
        full_name: Display name for generated documents (cover letters, etc.).
        headline: Professional headline (e.g., "Senior Backend Engineer").
        summary: Career summary paragraph used by agents for context.
        skills: List of technical and soft skills for matching.
        target_roles: Job titles the user is targeting.
        years_of_experience: Total professional experience.
        preferences: Embedded sub-model with salary, location, remote prefs.
    """

    user_id: Indexed(PydanticObjectId, unique=True)
    full_name: str = ""
    headline: str = ""
    summary: str = ""
    skills: list[str] = []
    target_roles: list[str] = []
    years_of_experience: int | None = None
    preferences: UserPreferences = UserPreferences()
    discovery_preferences: dict | None = None

    class Settings:
        name = "profiles"
