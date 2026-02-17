"""
Generic base repository implementing the Repository Pattern.

Design decisions
----------------
Why the Repository Pattern (not direct Beanie calls in services):
    The Repository Pattern adds a thin abstraction between business logic
    and data access. This provides:

    1. Testability: services can be tested with mock repositories that
       never touch a real database. Unit tests run in milliseconds.
    2. Consistency: error handling, logging, and common query patterns
       are defined once, not repeated in every service method.
    3. Encapsulation: if we change the ODM (Beanie -> Motor -> SQLAlchemy),
       only the repository layer changes. Services are unaffected.

    Alternative: call Beanie operations directly from services. Works for
    small projects, but as the codebase grows, database concerns leak into
    business logic — error handling, pagination, and query building get
    duplicated across service methods.

Why Python Generics (BaseRepository[T]):
    Generic type parameter T (bound to Document) gives us type safety
    across all repositories. When you create UserRepository(BaseRepository[User]),
    the IDE knows that create() returns a User, find_many() returns list[User],
    etc. No type casting needed.

Why dict filters (not Beanie expression objects):
    Beanie supports both dict filters ({"email": "test@example.com"}) and
    expression objects (User.email == "test@example.com"). Dict filters are
    more generic — the base repository does not need to know about specific
    document fields. Concrete repositories can use Beanie expressions for
    complex queries in their own methods.

Usage
-----
    from src.repositories.base import BaseRepository
    from src.db.documents.user import User

    class UserRepository(BaseRepository[User]):
        def __init__(self):
            super().__init__(User)

        async def get_by_email(self, email: str) -> User | None:
            return await self.find_one({"email": email})
"""

from typing import Any, Generic, TypeVar

import structlog
from beanie import Document, PydanticObjectId

from src.core.exceptions import DatabaseError

logger = structlog.get_logger()

T = TypeVar("T", bound=Document)


class BaseRepository(Generic[T]):
    """
    Generic repository providing standard CRUD operations for Beanie documents.

    Type parameter T is the Beanie Document subclass (e.g., User, Job).
    All methods handle errors and raise domain exceptions (DatabaseError)
    instead of leaking Beanie/PyMongo exceptions to callers.
    """

    def __init__(self, model: type[T]) -> None:
        """
        Initialize with the document model class.

        Args:
            model: The Beanie Document class this repository manages.
        """
        self._model = model

    # -- Create ---------------------------------------------------------------

    async def create(self, document: T) -> T:
        """
        Insert a new document into the collection.

        Beanie's insert() triggers @before_event(Insert) hooks, which set
        the created_at and updated_at timestamps via our TimestampedDocument
        base class.

        Args:
            document: The document instance to insert.

        Returns:
            The inserted document with its generated _id.

        Raises:
            DatabaseError: If the insert operation fails.
        """
        try:
            await document.insert()
            return document
        except Exception as e:
            raise DatabaseError(
                detail=f"Failed to create {self._model.__name__}: {e}"
            ) from e

    # -- Read -----------------------------------------------------------------

    async def get_by_id(self, document_id: PydanticObjectId) -> T | None:
        """
        Fetch a single document by its ObjectId.

        Returns None if the document does not exist (does not raise).
        Callers that need a guaranteed result should check for None and
        raise NotFoundError themselves.
        """
        return await self._model.get(document_id)

    async def find_one(self, filters: dict[str, Any]) -> T | None:
        """
        Find a single document matching the given filters.

        Args:
            filters: MongoDB query dict (e.g., {"email": "user@example.com"}).

        Returns:
            The first matching document, or None if no match.
        """
        return await self._model.find_one(filters)

    async def find_many(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        sort: str | None = None,
    ) -> list[T]:
        """
        Find multiple documents matching the given filters.

        Args:
            filters: MongoDB query dict. None or {} returns all documents.
            skip: Number of documents to skip (for pagination).
            limit: Maximum number of documents to return.
            sort: Field name to sort by. Prefix with "-" for descending
                (e.g., "-created_at").

        Returns:
            List of matching documents (may be empty).
        """
        query = self._model.find(filters or {})
        if sort:
            query = query.sort(sort)
        return await query.skip(skip).limit(limit).to_list()

    # -- Update ---------------------------------------------------------------

    async def update(
        self,
        document_id: PydanticObjectId,
        update_data: dict[str, Any],
    ) -> T | None:
        """
        Update specific fields on a document.

        Uses Beanie's .set() which generates a $set operation — only the
        specified fields are updated, not the entire document. This is
        important for concurrent access: two users updating different
        fields on the same document will not overwrite each other.

        Args:
            document_id: The document's ObjectId.
            update_data: Dict of field names to new values.

        Returns:
            The updated document, or None if the document was not found.

        Raises:
            DatabaseError: If the update operation fails.
        """
        document = await self.get_by_id(document_id)
        if document is None:
            return None
        try:
            await document.set(update_data)
            return document
        except Exception as e:
            raise DatabaseError(
                detail=f"Failed to update {self._model.__name__} {document_id}: {e}"
            ) from e

    # -- Delete ---------------------------------------------------------------

    async def delete(self, document_id: PydanticObjectId) -> bool:
        """
        Delete a document by its ObjectId.

        Returns True if the document was found and deleted, False if it
        did not exist.
        """
        document = await self.get_by_id(document_id)
        if document is None:
            return False
        await document.delete()
        return True

    # -- Count ----------------------------------------------------------------

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count documents matching the given filters.

        Args:
            filters: MongoDB query dict. None or {} counts all documents.

        Returns:
            Number of matching documents.
        """
        return await self._model.find(filters or {}).count()
