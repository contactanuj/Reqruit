"""
Company document model — company information and research data.

Companies are researched by the CompanyResearcher agent during the Job
Discovery workflow (Stage 2). The research data helps personalize cover
letters, outreach messages, and interview preparation.

Design decisions
----------------
Why a standalone collection (not embedded in Job):
    A company can have multiple job listings. Storing company data once
    and referencing it from each Job avoids duplicating research notes,
    culture notes, and tech stack across listings from the same company.

Why name as the unique key:
    Company names serve as the natural identifier users recognize. The
    unique index prevents duplicate entries when multiple jobs reference
    the same company.

    Alternative: use the company's website domain as the unique key.
    This would handle name variations (e.g., "Google" vs "Google LLC")
    but adds complexity. Company name is sufficient for a personal tool.

Why a freeform research dict:
    The CompanyResearcher agent produces varying research outputs —
    recent news, funding rounds, Glassdoor ratings, tech blog mentions.
    A dict accommodates this variability without rigid schema constraints.
    Specific fields (culture_notes, tech_stack) are promoted to first-class
    fields because they are used directly by other agents.
"""

from beanie import Indexed

from src.db.base_document import TimestampedDocument


class Company(TimestampedDocument):
    """
    Company information gathered by the CompanyResearcher agent.

    Fields:
        name: Company name (unique). Used as the primary identifier.
        domain: Company's website domain (e.g., "google.com").
        website: Full website URL.
        industry: Industry sector (e.g., "Technology", "Finance").
        size: Company size description (e.g., "1000-5000 employees").
        culture_notes: Free-text notes on company culture for personalization.
        tech_stack: Known technologies used by the company.
        research: Freeform dict of additional research (news, funding, etc.).
    """

    name: Indexed(str, unique=True)
    domain: str = ""
    website: str = ""
    industry: str = ""
    size: str = ""
    culture_notes: str = ""
    tech_stack: list[str] = []
    research: dict = {}

    class Settings:
        name = "companies"
