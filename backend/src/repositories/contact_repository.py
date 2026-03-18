"""
Contact repository — data access for company contacts.

Contacts are associated with companies (via company_id). The get_for_company
method is the primary query — contacts are always browsed in the context
of a specific company.
"""

from beanie import PydanticObjectId

from src.db.documents.contact import Contact
from src.repositories.base import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    """Contact-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Contact)

    async def get_for_company(
        self, company_id: PydanticObjectId, skip: int = 0, limit: int = 50
    ) -> list[Contact]:
        """List contacts for a specific company."""
        return await self.find_many({"company_id": company_id}, skip=skip, limit=limit)
