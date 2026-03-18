"""
Tests for the select_resume_blocks node in the application assembly graph.

Verifies Weaviate hybrid search integration, fallback behavior,
and correct state updates — all with mocked retriever.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.workflows.graphs.application_assembly import select_resume_blocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(user_id: str = "user-123") -> dict:
    return {"configurable": {"user_id": user_id, "thread_id": "test-thread"}}


def _state(decoded_jd: str = "", jd_text: str = "Default JD", resume_text: str = "Full resume") -> dict:
    return {
        "decoded_jd": decoded_jd,
        "jd_text": jd_text,
        "resume_text": resume_text,
        "messages": [],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSelectResumeBlocks:
    """Tests for the select_resume_blocks graph node."""

    async def test_calls_hybrid_search_with_correct_params(self) -> None:
        """AC #1: Calls hybrid_search with ResumeChunk, user tenant, limit=10, alpha=0.7."""
        decoded = json.dumps({"required_skills": ["Python", "FastAPI"], "preferred_skills": ["Docker"]})
        with patch(
            "src.workflows.graphs.application_assembly.hybrid_search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = [
                {"properties": {"content": "Python dev"}, "score": 0.95},
            ]
            await select_resume_blocks(_state(decoded_jd=decoded), _config())

            mock_search.assert_called_once_with(
                collection_name="ResumeChunk",
                query="Python, FastAPI, Docker",
                tenant="user-123",
                limit=10,
                alpha=0.7,
            )

    async def test_stores_results_in_state(self) -> None:
        """AC #1: Results serialized as JSON string in selected_resume_blocks."""
        decoded = json.dumps({"required_skills": ["Python"], "preferred_skills": []})
        with patch(
            "src.workflows.graphs.application_assembly.hybrid_search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = [
                {"properties": {"content": "Python developer with 5 years"}, "score": 0.95},
                {"properties": {"content": "Led team of 8 engineers"}, "score": 0.87},
            ]
            result = await select_resume_blocks(_state(decoded_jd=decoded), _config())

            blocks = json.loads(result["selected_resume_blocks"])
            assert len(blocks) == 2
            assert blocks[0]["content"] == "Python developer with 5 years"
            assert blocks[0]["score"] == 0.95
            assert result["resume_block_fallback"] is False
            assert result["status"] == "blocks_selected"

    async def test_fallback_on_empty_results(self) -> None:
        """AC #3: Falls back to full resume_text when Weaviate returns empty."""
        decoded = json.dumps({"required_skills": ["Python"], "preferred_skills": []})
        with patch(
            "src.workflows.graphs.application_assembly.hybrid_search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []
            result = await select_resume_blocks(
                _state(decoded_jd=decoded, resume_text="Full resume fallback text"),
                _config(),
            )

            blocks = json.loads(result["selected_resume_blocks"])
            assert result["resume_block_fallback"] is True
            assert blocks[0]["content"] == "Full resume fallback text"
            assert blocks[0]["score"] == 0.0
            assert result["status"] == "blocks_selected"

    async def test_fallback_on_search_exception(self) -> None:
        """AC #3: Falls back gracefully when hybrid_search raises."""
        decoded = json.dumps({"required_skills": ["Python"], "preferred_skills": []})
        with patch(
            "src.workflows.graphs.application_assembly.hybrid_search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = Exception("Weaviate connection failed")
            result = await select_resume_blocks(
                _state(decoded_jd=decoded, resume_text="Fallback resume"),
                _config(),
            )

            assert result["resume_block_fallback"] is True
            assert result["status"] == "blocks_selected"

    async def test_uses_jd_text_when_no_skills_parsed(self) -> None:
        """Falls back to jd_text as query when decoded_jd has no parseable skills."""
        with patch(
            "src.workflows.graphs.application_assembly.hybrid_search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = [{"properties": {"content": "Some block"}, "score": 0.5}]
            await select_resume_blocks(
                _state(decoded_jd="not valid json", jd_text="Senior Python developer needed"),
                _config(),
            )

            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["query"] == "Senior Python developer needed"

    async def test_tenant_uses_user_id_from_config(self) -> None:
        """NFR-14: tenant isolation — search scoped to user_id."""
        decoded = json.dumps({"required_skills": ["Go"], "preferred_skills": []})
        with patch(
            "src.workflows.graphs.application_assembly.hybrid_search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []
            await select_resume_blocks(_state(decoded_jd=decoded), _config(user_id="tenant-xyz"))

            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["tenant"] == "tenant-xyz"
