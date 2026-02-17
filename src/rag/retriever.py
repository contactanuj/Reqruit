"""
Weaviate search bridge — thin async functions connecting the embedding
service to Weaviate repositories.

These functions handle the two-step pattern that every search requires:
1. Embed the query text into a vector.
2. Pass the vector to a Weaviate repository for search.

This bridge exists so that callers (the memory retrieval orchestrator,
future RAG pipelines) do not need to manually call embed_query() then
construct a WeaviateRepository. It is a convenience layer, not an
abstraction — callers can always bypass it and use the embedding service
and repositories directly.

Usage
-----
    from src.rag.retriever import semantic_search, hybrid_search

    # Find resume chunks similar to a job description
    results = await hybrid_search("ResumeChunk", "Python developer", "user-123")

    # Pure vector search (no BM25 keywords)
    results = await semantic_search("STARStoryEmbedding", "leadership", "user-123")
"""

from src.rag.embeddings import embed_query
from src.repositories.weaviate_base import WeaviateRepository


async def hybrid_search(
    collection_name: str,
    query: str,
    tenant: str,
    limit: int = 5,
    alpha: float = 0.7,
) -> list[dict]:
    """
    Embed a query and perform hybrid search on a Weaviate collection.

    Combines BM25 keyword matching with vector semantic similarity.
    Preferred over pure vector search when queries contain specific terms
    (company names, technologies) alongside semantic meaning.

    Args:
        collection_name: The Weaviate collection to search.
        query: The text query (used for both embedding and BM25).
        tenant: The user's tenant ID for multi-tenancy isolation.
        limit: Maximum number of results.
        alpha: Balance between vector (1.0) and keyword (0.0) search.

    Returns:
        List of dicts with 'properties', 'uuid', and 'score'.
    """
    query_vector = await embed_query(query)
    repo = WeaviateRepository(collection_name)
    return await repo.hybrid_search(
        query=query,
        query_vector=query_vector,
        tenant=tenant,
        alpha=alpha,
        limit=limit,
    )


async def semantic_search(
    collection_name: str,
    query: str,
    tenant: str,
    limit: int = 5,
) -> list[dict]:
    """
    Embed a query and perform pure vector search on a Weaviate collection.

    Uses only cosine similarity — no keyword matching. Best for queries
    where meaning matters more than exact terms (e.g., "Tell me about a
    time you showed leadership" matching stories about team management).

    Args:
        collection_name: The Weaviate collection to search.
        query: The text query to embed.
        tenant: The user's tenant ID for multi-tenancy isolation.
        limit: Maximum number of results.

    Returns:
        List of dicts with 'properties', 'uuid', and 'score'.
    """
    query_vector = await embed_query(query)
    repo = WeaviateRepository(collection_name)
    return await repo.search_by_vector(
        query_vector=query_vector,
        tenant=tenant,
        limit=limit,
    )
