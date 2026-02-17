"""
Generic base repository for Weaviate vector database operations.

Parallel to BaseRepository[T] for MongoDB — provides standard CRUD and
search operations for any Weaviate collection. Collection-specific
repositories (ResumeChunkRepository, CoverLetterEmbeddingRepository, etc.)
extend this class with typed convenience methods.

Design decisions
----------------
Why a base class (not standalone functions):
    The 4 Weaviate collections (ResumeChunk, JobEmbedding, CoverLetterEmbedding,
    STARStoryEmbedding) share identical operations: insert with vector, search
    by vector, hybrid search, delete. A base class avoids repeating the same
    Weaviate client calls, error handling, and tenant management in each
    repository.

    This mirrors how BaseRepository[T] for MongoDB avoids duplicating find,
    create, update, delete across UserRepository, JobRepository, etc.

Why tenant-per-user (not query-level filtering):
    Weaviate's native multi-tenancy physically isolates each tenant's data in
    a separate shard. This is more secure (no accidental cross-user leakage)
    and more performant (smaller index per tenant) than filtering by user_id
    on every query.

    Each user gets a tenant created at registration time. All repository
    methods require a tenant parameter — there is no way to accidentally
    query another user's data.

Why wrap errors in VectorSearchError:
    Same principle as BaseRepository wrapping MongoDB errors in DatabaseError.
    Callers get a clean domain exception without needing to handle Weaviate-
    specific exception types. The original exception is chained via `from exc`
    for debugging.

Usage
-----
    from src.repositories.weaviate_base import WeaviateRepository

    repo = WeaviateRepository("CoverLetterEmbedding")
    await repo.ensure_tenant("user-123")
    object_id = await repo.insert_object(
        properties={"content_summary": "...", "company": "Acme"},
        vector=[0.1, 0.2, ...],  # 384 dims
        tenant="user-123",
    )
    results = await repo.hybrid_search(
        query="Python backend developer",
        query_vector=[0.1, 0.2, ...],
        tenant="user-123",
        alpha=0.7,
    )
"""

import structlog
import weaviate
from weaviate.classes.query import Filter, MetadataQuery
from weaviate.classes.tenants import Tenant, TenantActivityStatus

from src.core.exceptions import VectorSearchError
from src.db.weaviate_client import get_weaviate_client

logger = structlog.get_logger()


class WeaviateRepository:
    """
    Generic repository providing standard vector operations for a Weaviate collection.

    Manages tenant lifecycle, object insertion with pre-computed vectors,
    vector search, hybrid search, and deletion. All methods require a tenant
    parameter for multi-tenancy isolation.
    """

    def __init__(self, collection_name: str) -> None:
        """
        Initialize with the target Weaviate collection name.

        Args:
            collection_name: Must match one of the collections defined in
                weaviate_client.WEAVIATE_COLLECTIONS (e.g., "ResumeChunk").
        """
        self._collection_name = collection_name

    def _get_collection(
        self, client: weaviate.WeaviateAsyncClient
    ) -> weaviate.collections.CollectionAsync:
        """Get the collection handle from the client."""
        return client.collections.get(self._collection_name)

    # -- Tenant management ----------------------------------------------------

    async def ensure_tenant(self, tenant: str) -> None:
        """
        Create a tenant if it does not already exist.

        Idempotent — safe to call on every request. Weaviate returns the
        existing tenants list, and we only create if the target is missing.

        Args:
            tenant: The tenant identifier (typically user_id).
        """
        try:
            client = get_weaviate_client()
            collection = self._get_collection(client)

            existing = await collection.tenants.get()
            if tenant not in existing:
                await collection.tenants.create(
                    [Tenant(name=tenant, activity_status=TenantActivityStatus.ACTIVE)]
                )
                logger.debug(
                    "weaviate_tenant_created",
                    collection=self._collection_name,
                    tenant=tenant,
                )
        except RuntimeError:
            raise
        except Exception as exc:
            raise VectorSearchError(
                detail=(
                    f"Failed to ensure tenant '{tenant}' "
                    f"in {self._collection_name}: {exc}"
                )
            ) from exc

    # -- Insert ---------------------------------------------------------------

    async def insert_object(
        self,
        properties: dict,
        vector: list[float],
        tenant: str,
    ) -> str:
        """
        Insert an object with a pre-computed embedding vector.

        The vector is generated by our embedding service (BGE-small-en-v1.5)
        before calling this method. Weaviate stores it in the HNSW index for
        efficient nearest-neighbor search.

        Args:
            properties: The object's properties (must match the collection schema).
            vector: Pre-computed embedding vector (384 dimensions for BGE-small).
            tenant: The tenant to insert into.

        Returns:
            The UUID of the inserted object (as a string).

        Raises:
            VectorSearchError: If the insert operation fails.
        """
        try:
            client = get_weaviate_client()
            collection = self._get_collection(client)
            multi_collection = collection.with_tenant(tenant)

            result = await multi_collection.data.insert(
                properties=properties,
                vector=vector,
            )
            return str(result)
        except RuntimeError:
            raise
        except Exception as exc:
            raise VectorSearchError(
                detail=(
                    f"Failed to insert into {self._collection_name} "
                    f"(tenant={tenant}): {exc}"
                )
            ) from exc

    # -- Search ---------------------------------------------------------------

    async def search_by_vector(
        self,
        query_vector: list[float],
        tenant: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Pure vector nearest-neighbor search.

        Finds the closest objects by cosine similarity to the query vector.
        Use this when you have an embedding and want semantically similar
        results without keyword matching.

        Args:
            query_vector: The query embedding vector.
            tenant: The tenant to search within.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with 'properties', 'uuid', and 'score' keys.

        Raises:
            VectorSearchError: If the search fails.
        """
        try:
            client = get_weaviate_client()
            collection = self._get_collection(client)
            multi_collection = collection.with_tenant(tenant)

            response = await multi_collection.query.near_vector(
                near_vector=query_vector,
                limit=limit,
                return_metadata=MetadataQuery(distance=True),
            )

            return [
                {
                    "properties": dict(obj.properties),
                    "uuid": str(obj.uuid),
                    "score": 1.0 - (obj.metadata.distance or 0.0),
                }
                for obj in response.objects
            ]
        except RuntimeError:
            raise
        except Exception as exc:
            raise VectorSearchError(
                detail=(
                    f"Vector search failed in {self._collection_name} "
                    f"(tenant={tenant}): {exc}"
                )
            ) from exc

    async def hybrid_search(
        self,
        query: str,
        query_vector: list[float],
        tenant: str,
        alpha: float = 0.7,
        limit: int = 5,
    ) -> list[dict]:
        """
        Hybrid search combining BM25 keyword matching and vector similarity.

        The alpha parameter controls the blend:
        - alpha=1.0 → pure vector search (semantic similarity only)
        - alpha=0.0 → pure BM25 keyword search
        - alpha=0.7 → 70% vector + 30% BM25 (default, good for most tasks)

        Hybrid search is preferred over pure vector search when the query
        contains specific terms (company names, job titles, technologies)
        that keyword matching can capture directly.

        Args:
            query: The text query for BM25 keyword matching.
            query_vector: The query embedding vector for semantic matching.
            tenant: The tenant to search within.
            alpha: Balance between vector (1.0) and keyword (0.0) search.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with 'properties', 'uuid', and 'score' keys.

        Raises:
            VectorSearchError: If the search fails.
        """
        try:
            client = get_weaviate_client()
            collection = self._get_collection(client)
            multi_collection = collection.with_tenant(tenant)

            response = await multi_collection.query.hybrid(
                query=query,
                vector=query_vector,
                alpha=alpha,
                limit=limit,
                return_metadata=MetadataQuery(score=True),
            )

            return [
                {
                    "properties": dict(obj.properties),
                    "uuid": str(obj.uuid),
                    "score": obj.metadata.score or 0.0,
                }
                for obj in response.objects
            ]
        except RuntimeError:
            raise
        except Exception as exc:
            raise VectorSearchError(
                detail=(
                    f"Hybrid search failed in {self._collection_name} "
                    f"(tenant={tenant}): {exc}"
                )
            ) from exc

    # -- Property search ------------------------------------------------------

    async def search_by_property(
        self,
        property_name: str,
        property_value: str,
        tenant: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Find objects matching a specific property value.

        Used by the indexing service for delete-before-reindex: find all
        existing chunks for a given resume_id or job_id, then delete them
        before inserting fresh chunks. This ensures stale embeddings do not
        accumulate when a document is re-indexed.

        Uses Weaviate v4's Filter API for exact property matching. No vector
        search is involved — this is a pure metadata filter query.

        Args:
            property_name: The property to filter on (e.g., "resume_id").
            property_value: The exact value to match.
            tenant: The tenant to search within.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with 'properties' and 'uuid' keys.

        Raises:
            VectorSearchError: If the query fails.
        """
        try:
            client = get_weaviate_client()
            collection = self._get_collection(client)
            multi_collection = collection.with_tenant(tenant)

            response = await multi_collection.query.fetch_objects(
                filters=Filter.by_property(property_name).equal(property_value),
                limit=limit,
            )

            return [
                {
                    "properties": dict(obj.properties),
                    "uuid": str(obj.uuid),
                }
                for obj in response.objects
            ]
        except RuntimeError:
            raise
        except Exception as exc:
            raise VectorSearchError(
                detail=(
                    f"Property search failed in {self._collection_name} "
                    f"({property_name}={property_value}, tenant={tenant}): {exc}"
                )
            ) from exc

    # -- Delete ---------------------------------------------------------------

    async def delete_object(self, object_id: str, tenant: str) -> bool:
        """
        Delete an object by its UUID.

        Args:
            object_id: The UUID of the object to delete.
            tenant: The tenant that owns the object.

        Returns:
            True if the object was deleted, False if it did not exist.

        Raises:
            VectorSearchError: If the delete operation fails.
        """
        try:
            client = get_weaviate_client()
            collection = self._get_collection(client)
            multi_collection = collection.with_tenant(tenant)

            # Weaviate's delete does not raise if the object is missing —
            # we check existence first to return an accurate boolean.
            existing = await multi_collection.data.exists(object_id)
            if not existing:
                return False

            await multi_collection.data.delete_by_id(object_id)
            return True
        except RuntimeError:
            raise
        except Exception as exc:
            raise VectorSearchError(
                detail=(
                    f"Failed to delete {object_id} from "
                    f"{self._collection_name} (tenant={tenant}): {exc}"
                )
            ) from exc
