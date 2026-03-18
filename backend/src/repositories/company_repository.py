"""
Company repository — data access for company research documents.

Companies are created lazily by the CompanyResearcher agent or when a
user manually adds a contact for a job. The get_by_name method supports
deduplication — we never create two Company documents with the same name.
"""

from src.db.documents.company import Company
from src.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Company-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Company)

    async def get_by_name(self, name: str) -> Company | None:
        """Find a company by exact name match. Used for deduplication."""
        return await self.find_one({"name": name})
