"""
Repository for ResumeChunk Weaviate collection.

Provides typed search methods for finding resume sections that match
a query. Used by the memory system to retrieve relevant resume context
when agents generate cover letters or prepare interview responses.

The ResumeChunk collection stores chunked resume sections (skills,
experience, education, etc.) with their embeddings. Chunks are created
during profile setup when the user uploads a resume.
"""

from src.rag.embeddings import embed_query
from src.repositories.weaviate_base import WeaviateRepository


class ResumeChunkRepository(WeaviateRepository):
    """Typed repository for ResumeChunk vector search operations."""

    def __init__(self) -> None:
        super().__init__("ResumeChunk")

    async def search_by_job_description(
        self,
        query: str,
        tenant: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Find resume sections most relevant to a job description.

        Embeds the query and performs a hybrid search (BM25 + vector) to
        find resume chunks that best match the job requirements. Hybrid
        search works well here because job descriptions contain specific
        keywords (technologies, job titles) alongside semantic meaning.

        Args:
            query: The job description text or a query derived from it.
            tenant: The user's tenant ID.
            limit: Maximum number of chunks to return.

        Returns:
            List of dicts with 'properties' (content, chunk_type, resume_id,
            user_id), 'uuid', and 'score'.
        """
        query_vector = await embed_query(query)
        return await self.hybrid_search(
            query=query,
            query_vector=query_vector,
            tenant=tenant,
            alpha=0.7,
            limit=limit,
        )
