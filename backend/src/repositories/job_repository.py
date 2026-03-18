"""
Job repository — data access methods for job listings.

Jobs are created when a user adds a listing to their pipeline.
Ownership is enforced through the Application join table, not directly
on Job — see ApplicationRepository for ownership-scoped queries.
"""

from src.db.documents.job import Job
from src.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Job-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Job)
