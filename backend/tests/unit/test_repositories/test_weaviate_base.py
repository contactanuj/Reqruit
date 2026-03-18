"""
Tests for the generic WeaviateRepository base class.

Verifies tenant management, object insertion, vector search, hybrid search,
and deletion. The Weaviate async client is mocked — these tests focus on
the repository's interaction with the client API and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import VectorSearchError
from src.repositories.weaviate_base import WeaviateRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_weaviate_client():
    """Mock the Weaviate async client returned by get_weaviate_client()."""
    client = MagicMock()

    # Collection handle chain:
    # client.collections.get("Name") -> collection
    # collection.with_tenant("t") -> multi_collection
    collection = MagicMock()
    multi_collection = MagicMock()
    collection.with_tenant.return_value = multi_collection

    # Tenant management
    collection.tenants.get = AsyncMock(return_value={})
    collection.tenants.create = AsyncMock()

    # Data operations
    multi_collection.data.insert = AsyncMock(
        return_value="550e8400-e29b-41d4-a716-446655440000"
    )
    multi_collection.data.exists = AsyncMock(return_value=True)
    multi_collection.data.delete_by_id = AsyncMock()

    # Query operations — build mock response objects
    mock_obj = MagicMock()
    mock_obj.properties = {"content": "test content"}
    mock_obj.uuid = "550e8400-e29b-41d4-a716-446655440000"
    mock_obj.metadata.distance = 0.1
    mock_obj.metadata.score = 0.9

    mock_response = MagicMock()
    mock_response.objects = [mock_obj]

    multi_collection.query.near_vector = AsyncMock(return_value=mock_response)
    multi_collection.query.hybrid = AsyncMock(return_value=mock_response)
    multi_collection.query.fetch_objects = AsyncMock(return_value=mock_response)

    client.collections.get.return_value = collection

    with patch(
        "src.repositories.weaviate_base.get_weaviate_client",
        return_value=client,
    ):
        yield client, collection, multi_collection


@pytest.fixture
def repo():
    """Create a WeaviateRepository for testing."""
    return WeaviateRepository("TestCollection")


# ---------------------------------------------------------------------------
# Tenant management
# ---------------------------------------------------------------------------


class TestEnsureTenant:
    async def test_creates_tenant_when_missing(self, repo, mock_weaviate_client):
        """ensure_tenant creates a new tenant when it doesn't exist."""
        _, collection, _ = mock_weaviate_client
        collection.tenants.get.return_value = {}

        await repo.ensure_tenant("user-123")

        collection.tenants.create.assert_called_once()
        tenant_arg = collection.tenants.create.call_args[0][0][0]
        assert tenant_arg.name == "user-123"

    async def test_skips_creation_when_tenant_exists(
        self, repo, mock_weaviate_client
    ):
        """ensure_tenant does nothing when the tenant already exists."""
        _, collection, _ = mock_weaviate_client
        collection.tenants.get.return_value = {"user-123": MagicMock()}

        await repo.ensure_tenant("user-123")

        collection.tenants.create.assert_not_called()

    async def test_wraps_error_in_vector_search_error(
        self, repo, mock_weaviate_client
    ):
        """ensure_tenant wraps unexpected errors in VectorSearchError."""
        _, collection, _ = mock_weaviate_client
        collection.tenants.get.side_effect = Exception("connection lost")

        with pytest.raises(VectorSearchError, match="Failed to ensure tenant"):
            await repo.ensure_tenant("user-123")


# ---------------------------------------------------------------------------
# Insert
# ---------------------------------------------------------------------------


class TestInsertObject:
    async def test_returns_uuid(self, repo, mock_weaviate_client):
        """insert_object returns the UUID of the inserted object."""
        result = await repo.insert_object(
            properties={"content": "test"},
            vector=[0.1] * 384,
            tenant="user-1",
        )
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    async def test_passes_properties_and_vector(self, repo, mock_weaviate_client):
        """insert_object forwards properties and vector to the client."""
        _, _, multi = mock_weaviate_client

        await repo.insert_object(
            properties={"content": "hello"},
            vector=[0.5] * 384,
            tenant="user-1",
        )

        multi.data.insert.assert_called_once_with(
            properties={"content": "hello"},
            vector=[0.5] * 384,
        )

    async def test_wraps_error_in_vector_search_error(
        self, repo, mock_weaviate_client
    ):
        """insert_object wraps failures in VectorSearchError."""
        _, _, multi = mock_weaviate_client
        multi.data.insert.side_effect = Exception("insert failed")

        with pytest.raises(VectorSearchError, match="Failed to insert"):
            await repo.insert_object(
                properties={"content": "test"},
                vector=[0.1] * 384,
                tenant="user-1",
            )


# ---------------------------------------------------------------------------
# Vector search
# ---------------------------------------------------------------------------


class TestSearchByVector:
    async def test_returns_formatted_results(self, repo, mock_weaviate_client):
        """search_by_vector returns dicts with properties, uuid, and score."""
        results = await repo.search_by_vector(
            query_vector=[0.1] * 384,
            tenant="user-1",
        )

        assert len(results) == 1
        assert results[0]["properties"]["content"] == "test content"
        assert results[0]["uuid"] == "550e8400-e29b-41d4-a716-446655440000"
        assert results[0]["score"] == pytest.approx(0.9)  # 1.0 - 0.1 distance

    async def test_passes_limit(self, repo, mock_weaviate_client):
        """search_by_vector forwards the limit parameter."""
        _, _, multi = mock_weaviate_client

        await repo.search_by_vector(
            query_vector=[0.1] * 384,
            tenant="user-1",
            limit=10,
        )

        call_kwargs = multi.query.near_vector.call_args[1]
        assert call_kwargs["limit"] == 10

    async def test_wraps_error(self, repo, mock_weaviate_client):
        """search_by_vector wraps failures in VectorSearchError."""
        _, _, multi = mock_weaviate_client
        multi.query.near_vector.side_effect = Exception("search error")

        with pytest.raises(VectorSearchError, match="Vector search failed"):
            await repo.search_by_vector([0.1] * 384, "user-1")


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------


class TestHybridSearch:
    async def test_returns_formatted_results(self, repo, mock_weaviate_client):
        """hybrid_search returns dicts with properties, uuid, and score."""
        results = await repo.hybrid_search(
            query="test query",
            query_vector=[0.1] * 384,
            tenant="user-1",
        )

        assert len(results) == 1
        assert results[0]["score"] == 0.9

    async def test_passes_alpha_and_limit(self, repo, mock_weaviate_client):
        """hybrid_search forwards alpha and limit parameters."""
        _, _, multi = mock_weaviate_client

        await repo.hybrid_search(
            query="test",
            query_vector=[0.1] * 384,
            tenant="user-1",
            alpha=0.5,
            limit=3,
        )

        call_kwargs = multi.query.hybrid.call_args[1]
        assert call_kwargs["alpha"] == 0.5
        assert call_kwargs["limit"] == 3

    async def test_wraps_error(self, repo, mock_weaviate_client):
        """hybrid_search wraps failures in VectorSearchError."""
        _, _, multi = mock_weaviate_client
        multi.query.hybrid.side_effect = Exception("hybrid error")

        with pytest.raises(VectorSearchError, match="Hybrid search failed"):
            await repo.hybrid_search("test", [0.1] * 384, "user-1")


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDeleteObject:
    async def test_returns_true_when_deleted(self, repo, mock_weaviate_client):
        """delete_object returns True when the object exists and is deleted."""
        result = await repo.delete_object("some-uuid", "user-1")
        assert result is True

    async def test_returns_false_when_not_found(self, repo, mock_weaviate_client):
        """delete_object returns False when the object doesn't exist."""
        _, _, multi = mock_weaviate_client
        multi.data.exists.return_value = False

        result = await repo.delete_object("missing-uuid", "user-1")
        assert result is False

    async def test_wraps_error(self, repo, mock_weaviate_client):
        """delete_object wraps failures in VectorSearchError."""
        _, _, multi = mock_weaviate_client
        multi.data.exists.side_effect = Exception("delete error")

        with pytest.raises(VectorSearchError, match="Failed to delete"):
            await repo.delete_object("some-uuid", "user-1")


# ---------------------------------------------------------------------------
# Property search
# ---------------------------------------------------------------------------


class TestSearchByProperty:
    async def test_returns_matching_objects(self, repo, mock_weaviate_client):
        """search_by_property returns dicts with properties and uuid."""
        results = await repo.search_by_property(
            property_name="resume_id",
            property_value="resume-1",
            tenant="user-1",
        )

        assert len(results) == 1
        assert results[0]["properties"]["content"] == "test content"
        assert results[0]["uuid"] == "550e8400-e29b-41d4-a716-446655440000"

    async def test_returns_empty_for_no_matches(self, repo, mock_weaviate_client):
        """search_by_property returns empty list when nothing matches."""
        _, _, multi = mock_weaviate_client
        empty_response = MagicMock()
        empty_response.objects = []
        multi.query.fetch_objects.return_value = empty_response

        results = await repo.search_by_property(
            property_name="resume_id",
            property_value="nonexistent",
            tenant="user-1",
        )

        assert results == []

    async def test_wraps_error_in_vector_search_error(
        self, repo, mock_weaviate_client
    ):
        """search_by_property wraps failures in VectorSearchError."""
        _, _, multi = mock_weaviate_client
        multi.query.fetch_objects.side_effect = Exception("filter error")

        with pytest.raises(VectorSearchError, match="Property search failed"):
            await repo.search_by_property("resume_id", "r1", "user-1")
