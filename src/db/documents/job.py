"""
Job document model — job listings discovered or manually added by the user.

Jobs are the central entity in the discovery and application workflows.
They can be added via manual entry, URL paste (scraped by JobSearcher agent),
or matched from job boards.

Design decisions
----------------
Why embed requirements and salary (not separate collections):
    JobRequirements and SalaryRange are always accessed together with the
    job listing. They have no independent lifecycle — you never query "all
    salary ranges" without the parent job. Embedding avoids unnecessary
    joins and follows MongoDB's "data that is accessed together should be
    stored together" principle.

Why company_id as a reference (not embedded company data):
    A company can have multiple job listings. Embedding the full company
    data in each job would duplicate research notes, culture notes, and
    tech stack across every listing from the same company. The reference
    pattern avoids this duplication.

    We also store a denormalized company_name for display purposes — avoids
    a join when listing jobs in the UI. This is a common MongoDB pattern:
    denormalize the fields you read frequently, reference the fields you
    update infrequently.

Why a url field:
    Many jobs are discovered via URLs (LinkedIn, company career pages).
    Storing the source URL enables deduplication (same job posted on
    multiple boards) and lets users verify the listing source.

Why compound index on (location, remote):
    Users frequently filter jobs by location and remote preference. A
    compound index on both fields speeds up this common filter combination.
"""

from beanie import PydanticObjectId
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument
from src.db.documents.embedded import SalaryRange


class JobRequirements(BaseModel):
    """
    Embedded job requirements extracted from the listing.

    Stored inline within the Job document. The JobMatcher agent uses these
    fields to compute match scores against the user's profile skills.
    """

    required_skills: list[str] = []
    preferred_skills: list[str] = []
    experience_years: int | None = None


class Job(TimestampedDocument):
    """
    Job listing — discovered by agents or manually added by the user.

    Fields:
        title: Job title as posted.
        company_id: Reference to the Company document. None if company
            hasn't been researched yet.
        company_name: Denormalized company name for display without a join.
        description: Full job description text. Used for RAG and matching.
        requirements: Embedded structured requirements for matching.
        salary: Embedded salary range (if disclosed in the listing).
        location: Job location string (e.g., "San Francisco, CA").
        remote: Whether the role allows remote work.
        url: Source URL of the listing for deduplication and reference.
        source: Where the job was found (e.g., "linkedin", "manual", "indeed").
    """

    title: str
    company_id: PydanticObjectId | None = None
    company_name: str = ""
    description: str = ""
    requirements: JobRequirements = JobRequirements()
    salary: SalaryRange | None = None
    location: str = ""
    remote: bool = False
    url: str = ""
    source: str = ""

    class Settings:
        name = "jobs"
        indexes = [
            IndexModel(
                [("company_id", ASCENDING)],
                name="company_idx",
            ),
            IndexModel(
                [("location", ASCENDING), ("remote", ASCENDING)],
                name="location_remote_idx",
            ),
        ]
