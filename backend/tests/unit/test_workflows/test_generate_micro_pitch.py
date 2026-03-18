"""
Tests for the generate_micro_pitch node in the application assembly graph.

Verifies STAR story retrieval via semantic_search, fallback when no stories,
and correct state updates with structured micro_pitch output.
"""

import json
from unittest.mock import AsyncMock, patch

from src.workflows.graphs.application_assembly import generate_micro_pitch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(user_id: str = "user-123") -> dict:
    return {"configurable": {"user_id": user_id, "thread_id": "test-thread"}}


def _state(**overrides) -> dict:
    base = {
        "decoded_jd": '{"required_skills": ["Python", "microservices"]}',
        "fit_analysis": '{"overall": 85}',
        "skills_summary": "Senior Python developer",
        "locale_context": "",
        "selected_resume_blocks": '[{"content": "Python dev", "score": 0.9}]',
        "jd_text": "Python developer role",
        "messages": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateMicroPitch:
    """Tests for the generate_micro_pitch graph node."""

    async def test_retrieves_star_stories_via_semantic_search(self) -> None:
        """AC #2: Uses semantic_search on STARStoryEmbedding collection."""
        with (
            patch(
                "src.workflows.graphs.application_assembly.semantic_search",
                new_callable=AsyncMock,
            ) as mock_search,
            patch(
                "src.workflows.graphs.application_assembly._orchestrator",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_search.return_value = [
                {"properties": {"content": "Led migration to microservices"}, "score": 0.92},
            ]
            mock_agent.return_value = {"application_strategy": "pitch content"}
            await generate_micro_pitch(_state(), _config())

            mock_search.assert_called_once_with(
                collection_name="STARStoryEmbedding",
                query="Python, microservices",
                tenant="user-123",
                limit=5,
            )

    async def test_calls_orchestrator_with_star_stories(self) -> None:
        """AC #2: Passes STAR stories to ApplicationOrchestratorAgent."""
        with (
            patch(
                "src.workflows.graphs.application_assembly.semantic_search",
                new_callable=AsyncMock,
            ) as mock_search,
            patch(
                "src.workflows.graphs.application_assembly._orchestrator",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_search.return_value = [
                {"properties": {"content": "Led team of 8"}, "score": 0.9},
            ]
            mock_agent.return_value = {"application_strategy": "pitch"}
            await generate_micro_pitch(_state(), _config())

            mock_agent.assert_called_once()
            call_state = mock_agent.call_args[0][0]
            assert "STAR Stories" in call_state["relevant_resume_blocks"]

    async def test_star_stories_available_true_when_found(self) -> None:
        """AC #2: star_stories_available is True when stories are found."""
        with (
            patch(
                "src.workflows.graphs.application_assembly.semantic_search",
                new_callable=AsyncMock,
            ) as mock_search,
            patch(
                "src.workflows.graphs.application_assembly._orchestrator",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_search.return_value = [
                {"properties": {"content": "story 1"}, "score": 0.9},
                {"properties": {"content": "story 2"}, "score": 0.85},
            ]
            mock_agent.return_value = {"application_strategy": "pitch"}
            result = await generate_micro_pitch(_state(), _config())

            micro = json.loads(result["micro_pitch"])
            assert micro["star_stories_available"] is True
            assert len(micro["star_stories_used"]) == 2
            assert result["star_stories_available"] is True

    async def test_fallback_when_no_star_stories(self) -> None:
        """AC #3: Falls back gracefully when no STAR stories in Weaviate."""
        with (
            patch(
                "src.workflows.graphs.application_assembly.semantic_search",
                new_callable=AsyncMock,
            ) as mock_search,
            patch(
                "src.workflows.graphs.application_assembly._orchestrator",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_search.return_value = []
            mock_agent.return_value = {"application_strategy": "pitch from resume only"}
            result = await generate_micro_pitch(_state(), _config())

            micro = json.loads(result["micro_pitch"])
            assert micro["star_stories_available"] is False
            assert micro["star_stories_used"] == []
            assert micro["pitch_text"] == "pitch from resume only"
            assert result["star_stories_available"] is False

    async def test_fallback_on_search_exception(self) -> None:
        """AC #3: Falls back gracefully when semantic_search raises."""
        with (
            patch(
                "src.workflows.graphs.application_assembly.semantic_search",
                new_callable=AsyncMock,
            ) as mock_search,
            patch(
                "src.workflows.graphs.application_assembly._orchestrator",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_search.side_effect = Exception("Weaviate down")
            mock_agent.return_value = {"application_strategy": "fallback pitch"}
            result = await generate_micro_pitch(_state(), _config())

            micro = json.loads(result["micro_pitch"])
            assert micro["star_stories_available"] is False
            assert result["status"] == "micro_pitch_generated"

    async def test_status_set_to_micro_pitch_generated(self) -> None:
        """Status updated to 'micro_pitch_generated'."""
        with (
            patch(
                "src.workflows.graphs.application_assembly.semantic_search",
                new_callable=AsyncMock,
            ) as mock_search,
            patch(
                "src.workflows.graphs.application_assembly._orchestrator",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_search.return_value = []
            mock_agent.return_value = {"application_strategy": "pitch"}
            result = await generate_micro_pitch(_state(), _config())

            assert result["status"] == "micro_pitch_generated"

    async def test_tenant_isolation(self) -> None:
        """NFR-14: STAR story search scoped to user_id."""
        with (
            patch(
                "src.workflows.graphs.application_assembly.semantic_search",
                new_callable=AsyncMock,
            ) as mock_search,
            patch(
                "src.workflows.graphs.application_assembly._orchestrator",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_search.return_value = []
            mock_agent.return_value = {"application_strategy": "pitch"}
            await generate_micro_pitch(_state(), _config(user_id="tenant-xyz"))

            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["tenant"] == "tenant-xyz"
