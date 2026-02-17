"""
Shared embedded sub-models used across multiple document models.

These are Pydantic BaseModel classes (not Beanie Document classes). They are
stored inline within their parent documents, not in separate MongoDB
collections.

Design decisions
----------------
Embedding strategy:
    We embed data that is tightly coupled to its parent, always accessed
    together, and small in size. Embedded models have no independent
    lifecycle — they are created, read, updated, and deleted only through
    their parent document.

    This follows MongoDB's core modeling principle: "data that is accessed
    together should be stored together."

    Alternative: store each sub-model in its own collection with foreign
    key references. This would be the relational (PostgreSQL) approach, but
    in MongoDB it creates unnecessary joins for data that never needs to be
    queried independently.

Why a separate file for shared sub-models:
    Sub-models used by only one document are defined in that document's file
    (e.g., JobRequirements lives in job.py). Sub-models used by multiple
    documents live here to prevent circular imports and make the dependency
    direction clear.

    Currently only SalaryRange is shared (used in Profile and Job). As
    the project grows, other shared value objects can be added here.
"""

from pydantic import BaseModel


class SalaryRange(BaseModel):
    """
    Salary range with currency.

    Used in:
    - Profile.preferences.target_salary (user's desired salary range)
    - Job.salary (compensation range listed in the posting)

    Stored inline within parent documents — never queried independently.
    """

    min_amount: int = 0
    max_amount: int = 0
    currency: str = "USD"
