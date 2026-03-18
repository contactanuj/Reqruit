"""
Weaviate vector database async client and collection management.

Design decisions
----------------
Why Weaviate (not pgvector or Pinecone):
    Weaviate is a purpose-built vector database with dedicated HNSW indexing,
    built-in hybrid search (BM25 + vector), metadata filtering, and native
    multi-tenancy. All features used in this project are free (self-hosted).

    pgvector: good for small-scale embeddings but shares PostgreSQL resources.
    Pinecone: managed service with per-query costs. Weaviate self-hosted is
    free and gives us full control.

Why Weaviate v4 collections API (not v3 client.query.get):
    Weaviate Python client v4 introduced a collections-based API that is
    type-safe and more Pythonic. The v3 API (client.query.get().with_*)
    is deprecated. All code uses the v4 patterns.

Why app-side embeddings (not Weaviate vectorizer modules):
    We generate embeddings in our application using BGE-small-en-v1.5 (free,
    local, 384 dimensions). This gives us full control over the embedding
    model — no API costs, no vendor lock-in, works offline.

    Weaviate's text2vec-openai module would add API costs per embedding.
    Using Configure.Vectorizer.none() tells Weaviate we will provide vectors.

Why multi-tenancy:
    Each user's vector data is physically isolated in Weaviate via native
    multi-tenancy. Tenants are created per-user at registration time. This
    provides data isolation without query-level filtering, which is both
    more secure and more performant.

Why HNSW with cosine distance:
    BGE-small-en-v1.5 is trained with cosine similarity. HNSW (Hierarchical
    Navigable Small World) is the standard ANN algorithm — good balance of
    speed, accuracy, and memory usage for our scale.

Usage
-----
In the FastAPI lifespan (src/api/main.py):
    from src.db.weaviate_client import connect_weaviate, close_weaviate

    async def lifespan(app):
        await connect_weaviate(settings)
        yield
        await close_weaviate()

Direct collection access:
    client = get_weaviate_client()
    resume_chunks = client.collections.get("ResumeChunk")
    results = await resume_chunks.query.hybrid(query="Python FastAPI", alpha=0.7)
"""

from urllib.parse import urlparse

import structlog
import weaviate
from weaviate.classes.config import Configure, DataType, Property, VectorDistances

from src.core.config import Settings

logger = structlog.get_logger()

# Module-level async client reference. Set by connect_weaviate(),
# cleared by close_weaviate().
_client: weaviate.WeaviateAsyncClient | None = None


# ---------------------------------------------------------------------------
# Collection schemas
# ---------------------------------------------------------------------------
# Each dict entry maps a collection name to its property definitions.
# All collections share the same vector config (app-side BGE-small, HNSW
# cosine) and have multi-tenancy enabled for per-user data isolation.

WEAVIATE_COLLECTIONS: dict[str, list[Property]] = {
    "ResumeChunk": [
        Property(name="content", data_type=DataType.TEXT),
        Property(name="chunk_type", data_type=DataType.TEXT),
        Property(name="resume_id", data_type=DataType.TEXT),
        Property(name="user_id", data_type=DataType.TEXT),
    ],
    "JobEmbedding": [
        Property(name="title", data_type=DataType.TEXT),
        Property(name="description_summary", data_type=DataType.TEXT),
        Property(name="job_id", data_type=DataType.TEXT),
        Property(name="user_id", data_type=DataType.TEXT),
    ],
    "CoverLetterEmbedding": [
        Property(name="content_summary", data_type=DataType.TEXT),
        Property(name="company", data_type=DataType.TEXT),
        Property(name="role", data_type=DataType.TEXT),
        Property(name="doc_id", data_type=DataType.TEXT),
    ],
    "STARStoryEmbedding": [
        Property(name="story_summary", data_type=DataType.TEXT),
        Property(name="tags", data_type=DataType.TEXT_ARRAY),
        Property(name="story_id", data_type=DataType.TEXT),
    ],
}


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------


async def connect_weaviate(settings: Settings) -> None:
    """
    Initialize the Weaviate async client and ensure collections exist.

    Uses use_async_with_local() for Docker/self-hosted instances (no API key)
    or use_async_with_weaviate_cloud() for Weaviate Cloud Services (with key).

    Args:
        settings: Application settings containing Weaviate URL and API key.
    """
    global _client

    parsed_url = urlparse(settings.weaviate.url)
    host = parsed_url.hostname or "localhost"
    port = parsed_url.port or 8080

    logger.info("weaviate_connecting", host=host, port=port)

    if settings.weaviate.api_key:
        # Weaviate Cloud Services (production)
        _client = weaviate.use_async_with_weaviate_cloud(
            cluster_url=settings.weaviate.url,
            auth_credentials=weaviate.auth.AuthApiKey(settings.weaviate.api_key),
        )
    else:
        # Local Docker instance (development)
        # Default gRPC port is 50051, matching our docker-compose.yml.
        _client = weaviate.use_async_with_local(
            host=host,
            port=port,
            grpc_port=50051,
        )

    await _client.connect()
    await _ensure_collections()

    logger.info(
        "weaviate_connected",
        host=host,
        collections=len(WEAVIATE_COLLECTIONS),
    )


async def close_weaviate() -> None:
    """
    Close the Weaviate async client connection.

    Safe to call multiple times (idempotent).
    """
    global _client

    if _client is not None:
        await _client.close()
        _client = None
        logger.info("weaviate_disconnected")


async def get_weaviate_status() -> dict:
    """
    Check Weaviate connectivity and return a status dict for the readiness probe.

    Returns:
        {"status": "ok"} if reachable, {"status": "error", "detail": "..."} if not.
    """
    if _client is None:
        return {"status": "error", "detail": "not initialized"}
    try:
        ready = await _client.is_ready()
        if ready:
            return {"status": "ok"}
        return {"status": "error", "detail": "not ready"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def get_weaviate_client() -> weaviate.WeaviateAsyncClient:
    """
    Return the active Weaviate async client.

    For use in RAG retriever, embedding storage, and other vector operations.

    Raises:
        RuntimeError: If called before connect_weaviate().
    """
    if _client is None:
        msg = "Weaviate client not initialized. Call connect_weaviate() first."
        raise RuntimeError(msg)
    return _client


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------


async def _ensure_collections() -> None:
    """
    Create Weaviate collections if they do not already exist.

    Each collection is configured with:
    - No vectorizer (app-side embedding via BGE-small-en-v1.5)
    - HNSW index with cosine distance (matches BGE-small's training)
    - Multi-tenancy enabled (per-user data isolation)

    This function is idempotent — safe to run on every startup. Existing
    collections are skipped.
    """
    if _client is None:
        msg = "Weaviate client not initialized."
        raise RuntimeError(msg)

    for name, properties in WEAVIATE_COLLECTIONS.items():
        exists = await _client.collections.exists(name)
        if exists:
            logger.debug("weaviate_collection_exists", collection=name)
            continue

        await _client.collections.create(
            name=name,
            vectorizer_config=Configure.Vectorizer.none(),
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
            ),
            multi_tenancy_config=Configure.multi_tenancy(enabled=True),
            properties=properties,
        )
        logger.info("weaviate_collection_created", collection=name)
