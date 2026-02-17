"""
Repository for STARStoryEmbedding Weaviate collection.

Provides typed search methods for finding STAR stories (Situation, Task,
Action, Result) that match interview questions or job requirements. Used
by the interview preparation agents to retrieve relevant behavioral
examples from the user's story bank.
"""

from src.rag.embeddings import embed_query
from src.repositories.weaviate_base import WeaviateRepository


class STARStoryEmbeddingRepository(WeaviateRepository):
    """Typed repository for STARStoryEmbedding vector search operations."""

    def __init__(self) -> None:
        super().__init__("STARStoryEmbedding")

    async def search_by_question(
        self,
        query: str,
        tenant: str,
        limit: int = 3,
    ) -> list[dict]:
        """
        Find STAR stories relevant to an interview question or topic.

        Embeds the question and searches for stories whose summaries are
        semantically similar. Useful for "Tell me about a time when..."
        style behavioral interview questions.

        Args:
            query: The interview question or topic to match against.
            tenant: The user's tenant ID.
            limit: Maximum number of stories to return.

        Returns:
            List of dicts with 'properties' (story_summary, tags,
            story_id), 'uuid', and 'score'.
        """
        query_vector = await embed_query(query)
        return await self.hybrid_search(
            query=query,
            query_vector=query_vector,
            tenant=tenant,
            alpha=0.7,
            limit=limit,
        )
