"""
Repository for CoverLetterEmbedding Weaviate collection.

Provides typed search methods for finding past cover letters similar to
the current task. Used by the memory system to retrieve examples of
previously written cover letters for similar roles/companies, enabling
the CoverLetterWriter agent to learn from past outputs.
"""

from src.rag.embeddings import embed_query
from src.repositories.weaviate_base import WeaviateRepository


class CoverLetterEmbeddingRepository(WeaviateRepository):
    """Typed repository for CoverLetterEmbedding vector search operations."""

    def __init__(self) -> None:
        super().__init__("CoverLetterEmbedding")

    async def search_similar_letters(
        self,
        query: str,
        tenant: str,
        limit: int = 3,
    ) -> list[dict]:
        """
        Find past cover letters written for similar roles or companies.

        Uses hybrid search to match both semantic similarity (similar job
        types) and keyword matches (company names, specific technologies).

        Args:
            query: A description of the target role, e.g., job title or
                key requirements.
            tenant: The user's tenant ID.
            limit: Maximum number of past letters to return.

        Returns:
            List of dicts with 'properties' (content_summary, company,
            role, doc_id), 'uuid', and 'score'.
        """
        query_vector = await embed_query(query)
        return await self.hybrid_search(
            query=query,
            query_vector=query_vector,
            tenant=tenant,
            alpha=0.7,
            limit=limit,
        )
