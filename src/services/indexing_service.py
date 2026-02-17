"""
Indexing service — the write path of the RAG pipeline.

Orchestrates the flow: fetch document from MongoDB → chunk → embed → store
in Weaviate. Each document type has a dedicated index method that understands
the source schema and the target Weaviate collection properties.

Design decisions
----------------
Why constructor-injected repositories (not global imports):
    The service depends on 8 repositories (4 MongoDB + 4 Weaviate). Passing
    them via the constructor makes the service fully testable — unit tests
    inject mocks without patching module-level state.

    This follows the same principle as FastAPI's dependency injection, but
    at the service layer instead of the request layer. Each `index_*` method
    uses the injected repos directly.

Why delete-before-reindex (not upsert):
    When a resume is edited and re-indexed, old chunks must be removed.
    Weaviate does not have a native "upsert by property" operation for
    multi-object updates. The simplest correct approach is:
    1. Find all existing objects for this source document (by resume_id, etc.)
    2. Delete each one
    3. Insert fresh chunks

    This is idempotent — re-indexing the same document twice produces the
    same result. It also handles structural changes (e.g., a resume that
    gains a new section) correctly because old chunks with different
    section boundaries are fully replaced.

Why separate index methods per document type (not a generic `index()`):
    Each document type has different source fields (Resume.raw_text vs
    STARStory.situation+task+action+result), different chunking strategies
    (section-based vs single-embedding), and different Weaviate property
    schemas. A generic method would need so many conditionals that it would
    be harder to read and maintain than dedicated methods.

Why cover letter indexing takes company/role as parameters:
    The DocumentRecord model does not store company or role directly — those
    come from the associated Job document via the Application. Rather than
    adding a dependency on Application/Job repositories, we accept them as
    parameters. The calling workflow (which already has this context) passes
    them in.

Usage
-----
    from src.services.indexing_service import IndexingService

    service = IndexingService(
        resume_repo=BaseRepository(Resume),
        job_repo=BaseRepository(Job),
        star_story_repo=BaseRepository(STARStory),
        document_repo=BaseRepository(DocumentRecord),
        resume_chunk_weaviate=WeaviateRepository("ResumeChunk"),
        job_embedding_weaviate=WeaviateRepository("JobEmbedding"),
        cover_letter_weaviate=WeaviateRepository("CoverLetterEmbedding"),
        star_story_weaviate=WeaviateRepository("STARStoryEmbedding"),
    )

    count = await service.index_resume("resume-id", "user-1")
    # -> 5 chunks indexed
"""

import structlog
from beanie import PydanticObjectId

from src.db.documents.document_record import DocumentRecord
from src.db.documents.job import Job
from src.db.documents.resume import Resume
from src.db.documents.star_story import STARStory
from src.rag.chunker import Chunk, chunk_job_description, chunk_resume
from src.rag.embeddings import embed_texts
from src.repositories.base import BaseRepository
from src.repositories.weaviate_base import WeaviateRepository

logger = structlog.get_logger()

# Maximum length for summary fields stored in Weaviate. Full content is
# in MongoDB — Weaviate only needs enough text for BM25 keyword matching.
_SUMMARY_MAX_CHARS = 500


class IndexingService:
    """
    Orchestrates document indexing from MongoDB into Weaviate.

    Each `index_*` method follows the same pattern:
    1. Fetch the source document from MongoDB
    2. Delete any existing embeddings for that document (idempotent re-index)
    3. Ensure the user's Weaviate tenant exists
    4. Chunk the document content (or use it as-is for single-embedding types)
    5. Generate embeddings via BGE-small-en-v1.5
    6. Store the embeddings in the target Weaviate collection
    """

    def __init__(
        self,
        resume_repo: BaseRepository[Resume],
        job_repo: BaseRepository[Job],
        star_story_repo: BaseRepository[STARStory],
        document_repo: BaseRepository[DocumentRecord],
        resume_chunk_weaviate: WeaviateRepository,
        job_embedding_weaviate: WeaviateRepository,
        cover_letter_weaviate: WeaviateRepository,
        star_story_weaviate: WeaviateRepository,
    ) -> None:
        self._resume_repo = resume_repo
        self._job_repo = job_repo
        self._star_story_repo = star_story_repo
        self._document_repo = document_repo
        self._resume_chunk_weaviate = resume_chunk_weaviate
        self._job_embedding_weaviate = job_embedding_weaviate
        self._cover_letter_weaviate = cover_letter_weaviate
        self._star_story_weaviate = star_story_weaviate

    # -- Public index methods -------------------------------------------------

    async def index_resume(self, resume_id: str, user_id: str) -> int:
        """
        Index a resume's text content into the ResumeChunk collection.

        Fetches the resume from MongoDB, splits the raw text into section-
        based chunks (or fixed-size fallback), embeds each chunk, and stores
        them in Weaviate. Any existing chunks for this resume are deleted
        first (idempotent re-index).

        Args:
            resume_id: The MongoDB ObjectId of the Resume document.
            user_id: The owner's user ID (used as Weaviate tenant).

        Returns:
            Number of chunks indexed.

        Raises:
            ValueError: If the resume is not found in MongoDB.
        """
        resume = await self._resume_repo.get_by_id(PydanticObjectId(resume_id))
        if resume is None:
            raise ValueError(f"Resume not found: {resume_id}")

        logger.info("indexing_resume", resume_id=resume_id, user_id=user_id)

        await self._delete_existing(
            self._resume_chunk_weaviate, "resume_id", resume_id, user_id
        )
        await self._resume_chunk_weaviate.ensure_tenant(user_id)

        chunks = chunk_resume(resume.raw_text, resume_id, user_id)
        if not chunks:
            logger.info("indexing_resume_no_chunks", resume_id=resume_id)
            return 0

        return await self._embed_and_store(
            self._resume_chunk_weaviate, chunks, user_id
        )

    async def index_job(self, job_id: str, user_id: str) -> int:
        """
        Index a job description into the JobEmbedding collection.

        Args:
            job_id: The MongoDB ObjectId of the Job document.
            user_id: The owner's user ID (used as Weaviate tenant).

        Returns:
            Number of chunks indexed.

        Raises:
            ValueError: If the job is not found in MongoDB.
        """
        job = await self._job_repo.get_by_id(PydanticObjectId(job_id))
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        logger.info("indexing_job", job_id=job_id, user_id=user_id)

        await self._delete_existing(
            self._job_embedding_weaviate, "job_id", job_id, user_id
        )
        await self._job_embedding_weaviate.ensure_tenant(user_id)

        chunks = chunk_job_description(job.description, job_id, user_id)
        if not chunks:
            logger.info("indexing_job_no_chunks", job_id=job_id)
            return 0

        # Override chunk metadata to include job title for BM25 matching
        enriched_chunks = [
            Chunk(
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                metadata={
                    **chunk.metadata,
                    "title": job.title,
                    "description_summary": chunk.content[:_SUMMARY_MAX_CHARS],
                },
            )
            for chunk in chunks
        ]

        return await self._embed_and_store(
            self._job_embedding_weaviate, enriched_chunks, user_id
        )

    async def index_cover_letter(
        self,
        document_id: str,
        user_id: str,
        company: str = "",
        role: str = "",
    ) -> int:
        """
        Index a cover letter into the CoverLetterEmbedding collection.

        Cover letters are stored as a single embedding (no chunking) since
        they are typically short enough to fit within embedding model limits.

        Args:
            document_id: The MongoDB ObjectId of the DocumentRecord.
            user_id: The owner's user ID (used as Weaviate tenant).
            company: The target company name (from the associated Job).
            role: The target role title (from the associated Job).

        Returns:
            Number of objects indexed (0 or 1).

        Raises:
            ValueError: If the document is not found in MongoDB.
        """
        document = await self._document_repo.get_by_id(
            PydanticObjectId(document_id)
        )
        if document is None:
            raise ValueError(f"Document not found: {document_id}")

        logger.info(
            "indexing_cover_letter",
            document_id=document_id,
            user_id=user_id,
        )

        await self._delete_existing(
            self._cover_letter_weaviate, "doc_id", document_id, user_id
        )
        await self._cover_letter_weaviate.ensure_tenant(user_id)

        if not document.content or not document.content.strip():
            return 0

        chunks = [
            Chunk(
                content=document.content,
                chunk_type="cover_letter",
                metadata={
                    "content_summary": document.content[:_SUMMARY_MAX_CHARS],
                    "company": company,
                    "role": role,
                    "doc_id": document_id,
                },
            )
        ]

        return await self._embed_and_store(
            self._cover_letter_weaviate, chunks, user_id
        )

    async def index_star_story(self, story_id: str, user_id: str) -> int:
        """
        Index a STAR story into the STARStoryEmbedding collection.

        Concatenates all STAR fields (situation, task, action, result) into
        a single text for embedding. The combined narrative provides richer
        semantic context for retrieval than embedding each field separately.

        Args:
            story_id: The MongoDB ObjectId of the STARStory document.
            user_id: The owner's user ID (used as Weaviate tenant).

        Returns:
            Number of objects indexed (0 or 1).

        Raises:
            ValueError: If the story is not found in MongoDB.
        """
        story = await self._star_story_repo.get_by_id(
            PydanticObjectId(story_id)
        )
        if story is None:
            raise ValueError(f"STAR story not found: {story_id}")

        logger.info(
            "indexing_star_story", story_id=story_id, user_id=user_id
        )

        await self._delete_existing(
            self._star_story_weaviate, "story_id", story_id, user_id
        )
        await self._star_story_weaviate.ensure_tenant(user_id)

        # Concatenate STAR fields into a single narrative for embedding
        parts = []
        if story.situation:
            parts.append(f"Situation: {story.situation}")
        if story.task:
            parts.append(f"Task: {story.task}")
        if story.action:
            parts.append(f"Action: {story.action}")
        if story.result:
            parts.append(f"Result: {story.result}")

        combined_text = "\n".join(parts)
        if not combined_text.strip():
            return 0

        chunks = [
            Chunk(
                content=combined_text,
                chunk_type="star_story",
                metadata={
                    "story_summary": combined_text[:_SUMMARY_MAX_CHARS],
                    "tags": story.tags,
                    "story_id": story_id,
                },
            )
        ]

        return await self._embed_and_store(
            self._star_story_weaviate, chunks, user_id
        )

    async def delete_index(
        self,
        collection_name: str,
        property_name: str,
        property_value: str,
        user_id: str,
    ) -> int:
        """
        Delete all indexed objects for a given source document.

        Generic deletion method for any Weaviate collection. Finds all
        objects matching the property filter and deletes them.

        Args:
            collection_name: The Weaviate collection to delete from.
            property_name: The property to filter on (e.g., "resume_id").
            property_value: The value to match.
            user_id: The owner's user ID (used as Weaviate tenant).

        Returns:
            Number of objects deleted.
        """
        repo = WeaviateRepository(collection_name)
        return await self._delete_existing(
            repo, property_name, property_value, user_id
        )

    # -- Internal helpers -----------------------------------------------------

    async def _delete_existing(
        self,
        weaviate_repo: WeaviateRepository,
        property_name: str,
        property_value: str,
        tenant: str,
    ) -> int:
        """
        Find and delete all objects matching a property value.

        Used before re-indexing to ensure stale chunks do not accumulate.
        Silently handles the case where no objects exist (returns 0).

        Returns:
            Number of objects deleted.
        """
        try:
            existing = await weaviate_repo.search_by_property(
                property_name=property_name,
                property_value=property_value,
                tenant=tenant,
            )
        except Exception:
            # If search fails (e.g., tenant doesn't exist yet), treat as
            # no existing objects — the insert will create the tenant.
            logger.debug(
                "delete_existing_search_failed",
                property_name=property_name,
                property_value=property_value,
            )
            return 0

        deleted = 0
        for obj in existing:
            await weaviate_repo.delete_object(obj["uuid"], tenant)
            deleted += 1

        if deleted:
            logger.info(
                "deleted_existing_chunks",
                count=deleted,
                property_name=property_name,
                property_value=property_value,
            )

        return deleted

    async def _embed_and_store(
        self,
        weaviate_repo: WeaviateRepository,
        chunks: list[Chunk],
        tenant: str,
    ) -> int:
        """
        Embed chunk contents and store them in Weaviate.

        Generates embeddings for all chunks in a single batch call (more
        efficient than embedding one at a time), then inserts each chunk
        with its vector into Weaviate.

        Args:
            weaviate_repo: The target Weaviate collection repository.
            chunks: List of Chunk objects to embed and store.
            tenant: The Weaviate tenant (user_id).

        Returns:
            Number of objects stored.
        """
        if not chunks:
            return 0

        texts = [chunk.content for chunk in chunks]
        vectors = await embed_texts(texts)

        stored = 0
        for chunk, vector in zip(chunks, vectors, strict=True):
            await weaviate_repo.insert_object(
                properties=chunk.metadata,
                vector=vector,
                tenant=tenant,
            )
            stored += 1

        logger.info(
            "chunks_indexed",
            count=stored,
            collection=weaviate_repo._collection_name,
        )

        return stored
