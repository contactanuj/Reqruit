"""
Tests for the tailor_resume node in the application assembly graph.

Verifies ApplicationOrchestratorAgent is called with correct state mapping
and that the result is stored properly in graph state.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.workflows.graphs.application_assembly import tailor_resume


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(user_id: str = "user-123") -> dict:
    return {"configurable": {"user_id": user_id, "thread_id": "test-thread"}}


def _state(**overrides) -> dict:
    base = {
        "decoded_jd": '{"required_skills": ["Python"]}',
        "fit_analysis": '{"overall": 85}',
        "skills_summary": "Senior Python developer",
        "locale_context": "",
        "selected_resume_blocks": '[{"content": "Python dev", "score": 0.9}]',
        "messages": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTailorResume:
    """Tests for the tailor_resume graph node."""

    async def test_calls_orchestrator_agent(self) -> None:
        """AC #2: Calls ApplicationOrchestratorAgent."""
        with patch(
            "src.workflows.graphs.application_assembly._orchestrator",
            new_callable=AsyncMock,
        ) as mock_agent:
            mock_agent.return_value = {"application_strategy": "# Tailored Resume\n\nPython, FastAPI..."}
            result = await tailor_resume(_state(), _config())

            mock_agent.assert_called_once()

    async def test_maps_state_keys_to_agent_expectations(self) -> None:
        """AC #2: Agent receives jd_analysis, fit_analysis, skills_summary, etc."""
        with patch(
            "src.workflows.graphs.application_assembly._orchestrator",
            new_callable=AsyncMock,
        ) as mock_agent:
            mock_agent.return_value = {"application_strategy": "tailored content"}
            await tailor_resume(_state(), _config())

            call_args = mock_agent.call_args[0]
            agent_state = call_args[0]
            assert "jd_analysis" in agent_state
            assert "fit_analysis" in agent_state
            assert "skills_summary" in agent_state
            assert "locale_context" in agent_state
            assert "relevant_resume_blocks" in agent_state
            assert "messages" in agent_state

    async def test_stores_tailored_resume_in_state(self) -> None:
        """AC #2: tailored_resume stored in result dict."""
        with patch(
            "src.workflows.graphs.application_assembly._orchestrator",
            new_callable=AsyncMock,
        ) as mock_agent:
            mock_agent.return_value = {"application_strategy": "# Resume\nPython expert"}
            result = await tailor_resume(_state(), _config())

            assert result["tailored_resume"] == "# Resume\nPython expert"
            assert result["application_strategy"] == "# Resume\nPython expert"

    async def test_status_set_to_resume_tailored(self) -> None:
        """AC #2: Status updated to 'resume_tailored'."""
        with patch(
            "src.workflows.graphs.application_assembly._orchestrator",
            new_callable=AsyncMock,
        ) as mock_agent:
            mock_agent.return_value = {"application_strategy": "content"}
            result = await tailor_resume(_state(), _config())

            assert result["status"] == "resume_tailored"

    async def test_handles_empty_application_strategy(self) -> None:
        """Gracefully handles agent returning empty application_strategy."""
        with patch(
            "src.workflows.graphs.application_assembly._orchestrator",
            new_callable=AsyncMock,
        ) as mock_agent:
            mock_agent.return_value = {}
            result = await tailor_resume(_state(), _config())

            assert result["tailored_resume"] == ""
            assert result["status"] == "resume_tailored"
