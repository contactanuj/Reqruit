"""
Tests for the memory retrieval orchestrator.

Verifies that retrieve_memories correctly looks up recipes, delegates to
Weaviate search, scores and merges results, and returns formatted context.
The retriever bridge is mocked — these tests focus on the orchestration
logic, not the underlying search or embedding.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.memory.retrieval import (
    _extract_content,
    _humanize_collection_name,
    format_memory_context,
    retrieve_memories,
)
from src.memory.types import MemoryContext, MemoryItem

# ---------------------------------------------------------------------------
# retrieve_memories
# ---------------------------------------------------------------------------


class TestRetrieveMemories:
    async def test_raises_for_unknown_agent(self):
        """retrieve_memories raises ValueError for an unregistered agent."""
        with pytest.raises(ValueError, match="No memory recipe"):
            await retrieve_memories("nonexistent_agent", "query", "user-1")

    @patch("src.memory.retrieval.hybrid_search", new_callable=AsyncMock)
    async def test_searches_weaviate_collections(self, mock_search):
        """retrieve_memories queries each Weaviate collection in the recipe."""
        mock_search.return_value = [
            {
                "properties": {"content": "Python experience"},
                "uuid": "u1",
                "score": 0.9,
            }
        ]

        await retrieve_memories(
            "cover_letter_writer", "Python developer", "user-1"
        )

        # cover_letter_writer recipe has 2 Weaviate collections
        assert mock_search.call_count == 2
        collection_args = [
            call.kwargs["collection_name"]
            for call in mock_search.call_args_list
        ]
        assert "ResumeChunk" in collection_args
        assert "CoverLetterEmbedding" in collection_args

    @patch("src.memory.retrieval.hybrid_search", new_callable=AsyncMock)
    async def test_returns_memory_context(self, mock_search):
        """retrieve_memories returns a MemoryContext with items and formatted text."""
        mock_search.return_value = [
            {
                "properties": {"content": "test content"},
                "uuid": "u1",
                "score": 0.8,
            }
        ]

        context = await retrieve_memories(
            "cover_letter_writer", "test query", "user-1"
        )

        assert isinstance(context, MemoryContext)
        assert len(context.items) > 0
        assert context.formatted != ""

    @patch("src.memory.retrieval.hybrid_search", new_callable=AsyncMock)
    async def test_scores_items_by_relevance_weight(self, mock_search):
        """Items from Weaviate are scored with relevance_weight multiplier."""
        mock_search.return_value = [
            {
                "properties": {"content": "test"},
                "uuid": "u1",
                "score": 1.0,
            }
        ]

        context = await retrieve_memories(
            "cover_letter_writer", "query", "user-1"
        )

        # cover_letter_writer has relevance_weight=0.7
        # So score = 1.0 * 0.7 = 0.7
        assert context.items[0].score == pytest.approx(0.7)

    @patch("src.memory.retrieval.hybrid_search", new_callable=AsyncMock)
    async def test_limits_results_to_max_results(self, mock_search):
        """retrieve_memories respects the recipe's max_results limit."""
        # Return more results than max_results (5 for cover_letter_writer)
        mock_search.return_value = [
            {"properties": {"content": f"item {i}"}, "uuid": f"u{i}", "score": 0.5}
            for i in range(10)
        ]

        context = await retrieve_memories(
            "cover_letter_writer", "query", "user-1"
        )

        # 2 collections * 10 results = 20, but max_results=5
        assert len(context.items) <= 5

    @patch("src.memory.retrieval.hybrid_search", new_callable=AsyncMock)
    async def test_sorts_by_score_descending(self, mock_search):
        """Items are sorted by score in descending order."""
        mock_search.side_effect = [
            [{"properties": {"content": "low"}, "uuid": "u1", "score": 0.3}],
            [{"properties": {"content_summary": "high"}, "uuid": "u2", "score": 0.9}],
        ]

        context = await retrieve_memories(
            "cover_letter_writer", "query", "user-1"
        )

        scores = [item.score for item in context.items]
        assert scores == sorted(scores, reverse=True)

    @patch("src.memory.retrieval.hybrid_search", new_callable=AsyncMock)
    async def test_handles_empty_results(self, mock_search):
        """retrieve_memories returns empty context when no results found."""
        mock_search.return_value = []

        context = await retrieve_memories(
            "cover_letter_writer", "obscure query", "user-1"
        )

        assert context.items == []
        assert context.formatted == ""

    @patch("src.memory.retrieval.hybrid_search", new_callable=AsyncMock)
    async def test_graceful_on_search_failure(self, mock_search):
        """retrieve_memories handles search failures without crashing."""
        mock_search.side_effect = Exception("Weaviate down")

        context = await retrieve_memories(
            "cover_letter_writer", "query", "user-1"
        )

        # Should return empty context, not raise
        assert context.items == []


# ---------------------------------------------------------------------------
# format_memory_context
# ---------------------------------------------------------------------------


class TestFormatMemoryContext:
    def test_empty_items_returns_empty_string(self):
        """format_memory_context returns empty string for no items."""
        assert format_memory_context([]) == ""

    def test_formats_items_with_header(self):
        """format_memory_context includes the section header."""
        items = [
            MemoryItem(
                content="Python experience",
                source="weaviate",
                score=0.9,
                metadata={"collection": "ResumeChunk"},
            )
        ]
        result = format_memory_context(items)
        assert "## Relevant Context from Memory" in result
        assert "Python experience" in result

    def test_groups_by_collection(self):
        """Items from different collections get separate subsections."""
        items = [
            MemoryItem(
                content="resume chunk",
                source="weaviate",
                score=0.9,
                metadata={"collection": "ResumeChunk"},
            ),
            MemoryItem(
                content="cover letter",
                source="weaviate",
                score=0.8,
                metadata={"collection": "CoverLetterEmbedding"},
            ),
        ]
        result = format_memory_context(items)
        assert "### Resume Chunk" in result
        assert "### Cover Letter Embedding" in result


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_extract_content_resume_chunk(self):
        """_extract_content uses 'content' field for ResumeChunk."""
        props = {"content": "Python dev", "chunk_type": "skills"}
        assert _extract_content(props, "ResumeChunk") == "Python dev"

    def test_extract_content_cover_letter(self):
        """_extract_content uses 'content_summary' for CoverLetterEmbedding."""
        props = {"content_summary": "Cover letter for Acme"}
        assert _extract_content(props, "CoverLetterEmbedding") == "Cover letter for Acme"

    def test_extract_content_star_story(self):
        """_extract_content uses 'story_summary' for STARStoryEmbedding."""
        props = {"story_summary": "Led a team of 5"}
        assert _extract_content(props, "STARStoryEmbedding") == "Led a team of 5"

    def test_extract_content_unknown_collection(self):
        """_extract_content falls back to 'content' for unknown collections."""
        props = {"content": "fallback"}
        assert _extract_content(props, "UnknownCollection") == "fallback"

    def test_humanize_collection_name(self):
        """_humanize_collection_name converts PascalCase to spaced words."""
        assert _humanize_collection_name("ResumeChunk") == "Resume Chunk"
        assert _humanize_collection_name("CoverLetterEmbedding") == "Cover Letter Embedding"
        assert _humanize_collection_name("Simple") == "Simple"
