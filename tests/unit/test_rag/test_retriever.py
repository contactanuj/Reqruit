"""
Tests for the RAG retriever bridge functions.

Verifies that hybrid_search and semantic_search correctly embed the query
and delegate to the WeaviateRepository. The embedding service and Weaviate
client are mocked — these tests focus on the wiring between the two.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag import retriever

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_embed_query():
    """Mock embed_query to return a known vector."""
    with patch("src.rag.retriever.embed_query", new_callable=AsyncMock) as mock:
        mock.return_value = [0.1] * 384
        yield mock


@pytest.fixture
def mock_weaviate_repo():
    """Mock WeaviateRepository to capture search calls."""
    with patch("src.rag.retriever.WeaviateRepository") as mock_cls:
        repo_instance = MagicMock()
        repo_instance.hybrid_search = AsyncMock(
            return_value=[
                {"properties": {"content": "result 1"}, "uuid": "u1", "score": 0.9},
            ]
        )
        repo_instance.search_by_vector = AsyncMock(
            return_value=[
                {"properties": {"content": "result 2"}, "uuid": "u2", "score": 0.8},
            ]
        )
        mock_cls.return_value = repo_instance
        yield mock_cls, repo_instance


# ---------------------------------------------------------------------------
# hybrid_search
# ---------------------------------------------------------------------------


class TestHybridSearch:
    async def test_embeds_query_and_searches(
        self, mock_embed_query, mock_weaviate_repo
    ):
        """hybrid_search embeds the query then calls repo.hybrid_search."""
        mock_cls, repo = mock_weaviate_repo

        results = await retriever.hybrid_search(
            "ResumeChunk", "Python developer", "user-1"
        )

        mock_embed_query.assert_called_once_with("Python developer")
        mock_cls.assert_called_once_with("ResumeChunk")
        repo.hybrid_search.assert_called_once_with(
            query="Python developer",
            query_vector=[0.1] * 384,
            tenant="user-1",
            alpha=0.7,
            limit=5,
        )
        assert len(results) == 1
        assert results[0]["properties"]["content"] == "result 1"

    async def test_passes_custom_alpha_and_limit(
        self, mock_embed_query, mock_weaviate_repo
    ):
        """hybrid_search forwards alpha and limit parameters."""
        _, repo = mock_weaviate_repo

        await retriever.hybrid_search(
            "JobEmbedding", "senior role", "user-2", limit=10, alpha=0.5
        )

        repo.hybrid_search.assert_called_once_with(
            query="senior role",
            query_vector=[0.1] * 384,
            tenant="user-2",
            alpha=0.5,
            limit=10,
        )

    async def test_returns_empty_list_when_no_results(
        self, mock_embed_query, mock_weaviate_repo
    ):
        """hybrid_search returns empty list when no matches found."""
        _, repo = mock_weaviate_repo
        repo.hybrid_search.return_value = []

        results = await retriever.hybrid_search(
            "ResumeChunk", "obscure query", "user-1"
        )
        assert results == []


# ---------------------------------------------------------------------------
# semantic_search
# ---------------------------------------------------------------------------


class TestSemanticSearch:
    async def test_embeds_query_and_searches(
        self, mock_embed_query, mock_weaviate_repo
    ):
        """semantic_search embeds the query then calls repo.search_by_vector."""
        mock_cls, repo = mock_weaviate_repo

        results = await retriever.semantic_search(
            "STARStoryEmbedding", "leadership", "user-1"
        )

        mock_embed_query.assert_called_once_with("leadership")
        mock_cls.assert_called_once_with("STARStoryEmbedding")
        repo.search_by_vector.assert_called_once_with(
            query_vector=[0.1] * 384,
            tenant="user-1",
            limit=5,
        )
        assert len(results) == 1

    async def test_passes_custom_limit(
        self, mock_embed_query, mock_weaviate_repo
    ):
        """semantic_search forwards the limit parameter."""
        _, repo = mock_weaviate_repo

        await retriever.semantic_search(
            "ResumeChunk", "test", "user-1", limit=3
        )

        repo.search_by_vector.assert_called_once_with(
            query_vector=[0.1] * 384,
            tenant="user-1",
            limit=3,
        )
