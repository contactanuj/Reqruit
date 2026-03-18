"""
Document repository — data access for AI-generated documents.

Documents are versioned per application + doc_type pair. The create_versioned
method uses optimistic concurrency with retry on DuplicateKeyError to ensure
atomic version assignment. A unique compound index on
(application_id, doc_type, version) enforces uniqueness at the database level.
"""

import structlog
from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from src.core.exceptions import ConflictError
from src.db.documents.document_record import DocumentRecord
from src.db.documents.enums import DocumentType
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class DocumentRepository(BaseRepository[DocumentRecord]):
    """DocumentRecord-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(DocumentRecord)

    async def get_by_thread_id_and_user(
        self, thread_id: str, user_id: PydanticObjectId
    ) -> DocumentRecord | None:
        """Get a document by thread_id scoped to a specific user.

        Used for thread ownership validation — confirms that the thread
        belongs to the requesting user before allowing stream/review access.
        """
        return await self.find_one({"thread_id": thread_id, "user_id": user_id})

    async def get_by_thread_id(
        self, thread_id: str
    ) -> DocumentRecord | None:
        """Get a document by thread_id regardless of user.

        Used to distinguish 403 (thread exists but belongs to another user)
        from 404 (thread does not exist at all).
        """
        return await self.find_one({"thread_id": thread_id})

    async def get_in_progress_for_application(
        self, application_id: PydanticObjectId, doc_type: DocumentType
    ) -> DocumentRecord | None:
        """Find an in-progress document (started but not yet completed/approved).

        A document is "in-progress" when thread_id is assigned (graph started),
        content is still empty (not finalized), and not yet approved.
        """
        return await self.find_one(
            {
                "application_id": application_id,
                "doc_type": doc_type,
                "thread_id": {"$ne": ""},
                "content": "",
                "is_approved": False,
            }
        )

    async def get_for_application(
        self, application_id: PydanticObjectId
    ) -> list[DocumentRecord]:
        """List all documents for an application, newest first."""
        return await self.find_many(
            {"application_id": application_id}, sort="-created_at"
        )

    async def get_latest(
        self, application_id: PydanticObjectId, doc_type: DocumentType
    ) -> DocumentRecord | None:
        """Get the most recent document of a given type for an application."""
        docs = await self.find_many(
            {"application_id": application_id, "doc_type": doc_type},
            limit=1,
            sort="-created_at",
        )
        return docs[0] if docs else None

    async def delete_for_application(
        self, application_id: PydanticObjectId
    ) -> int:
        """Delete all documents linked to an application.

        Used during cascade deletion when a job (and its application) is removed.

        Args:
            application_id: The application whose documents should be deleted.

        Returns:
            Number of documents deleted.
        """
        return await self.delete_many({"application_id": application_id})

    async def _get_next_version(
        self, application_id: PydanticObjectId, doc_type: DocumentType
    ) -> int:
        """Calculate the next version number for a document type on an application.

        Internal helper for create_versioned(). Do NOT call directly — the
        separate read-then-write is racy without the retry loop in
        create_versioned().
        """
        docs = await self.find_many(
            {"application_id": application_id, "doc_type": doc_type},
            sort="-version",
            limit=1,
        )
        return (docs[0].version + 1) if docs else 1

    async def create_versioned(
        self, document: DocumentRecord, max_retries: int = 3
    ) -> DocumentRecord:
        """Insert a DocumentRecord with atomic version assignment.

        Uses optimistic concurrency: compute next version, attempt insert,
        retry with incremented version on DuplicateKeyError. The unique
        compound index on (application_id, doc_type, version) ensures no
        two documents share the same version for a given application+type.

        Args:
            document: The DocumentRecord to insert (version will be set).
            max_retries: Maximum insert attempts before raising ConflictError.

        Returns:
            The inserted document with its assigned version.

        Raises:
            ConflictError: If all retry attempts are exhausted due to
                concurrent version conflicts (DOCUMENT_VERSION_CONFLICT).
        """
        original_version = document.version
        for attempt in range(max_retries):
            version = await self._get_next_version(
                document.application_id, document.doc_type
            )
            document.version = version
            try:
                await document.insert()
                return document
            except DuplicateKeyError as exc:
                if attempt < max_retries - 1:
                    logger.warning(
                        "document_version_conflict_retry",
                        application_id=str(document.application_id),
                        doc_type=document.doc_type,
                        version=version,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                else:
                    document.version = original_version
                    raise ConflictError(
                        detail="Document version conflict — concurrent requests exhausted retries",
                        error_code="DOCUMENT_VERSION_CONFLICT",
                    ) from exc
        # Unreachable, but satisfies type checker
        raise ConflictError(
            detail="Document version conflict",
            error_code="DOCUMENT_VERSION_CONFLICT",
        )
