"""
Tests for the human_review node in the application assembly graph.

Verifies interrupt() payload, approve/revise/reject Command routing.
"""

from unittest.mock import patch

from langgraph.graph import END
from langgraph.types import Command

from src.workflows.graphs.application_assembly import human_review


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config() -> dict:
    return {"configurable": {"thread_id": "t-1", "user_id": "u-1"}}


def _state(**overrides) -> dict:
    base = {
        "tailored_resume": "Resume content",
        "cover_letter": "CL content",
        "micro_pitch": "Pitch content",
        "fit_analysis": "Fit analysis",
        "application_strategy": "Strategy",
        "feedback": "",
        "messages": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHumanReview:
    """Tests for the human_review graph node."""

    async def test_interrupt_called_with_complete_payload(self) -> None:
        """AC #1: interrupt() includes all package components."""
        with patch(
            "src.workflows.graphs.application_assembly.interrupt",
            return_value={"action": "approve"},
        ) as mock_interrupt:
            await human_review(_state(), _config())

            payload = mock_interrupt.call_args[0][0]
            assert "tailored_resume" in payload
            assert "cover_letter" in payload
            assert "micro_pitch" in payload
            assert "fit_analysis" in payload
            assert "application_strategy" in payload
            assert "message" in payload

    async def test_approve_returns_command_to_end(self) -> None:
        """AC #2: approve → Command to END with status 'approved'."""
        with patch(
            "src.workflows.graphs.application_assembly.interrupt",
            return_value={"action": "approve"},
        ):
            result = await human_review(_state(), _config())

        assert isinstance(result, Command)
        assert result.update["status"] == "approved"
        assert result.goto == END

    async def test_revise_returns_command_to_tailor_resume(self) -> None:
        """AC #4: revise → Command to tailor_resume with feedback."""
        with patch(
            "src.workflows.graphs.application_assembly.interrupt",
            return_value={"action": "revise", "feedback": "More detail on Python"},
        ):
            result = await human_review(_state(), _config())

        assert isinstance(result, Command)
        assert result.update["status"] == "revision_requested"
        assert result.update["feedback"] == "More detail on Python"
        assert result.goto == "tailor_resume"

    async def test_reject_returns_command_to_end(self) -> None:
        """AC #5: reject → Command to END with status 'rejected'."""
        with patch(
            "src.workflows.graphs.application_assembly.interrupt",
            return_value={"action": "reject"},
        ):
            result = await human_review(_state(), _config())

        assert isinstance(result, Command)
        assert result.update["status"] == "rejected"
        assert result.goto == END

    async def test_default_action_is_approve(self) -> None:
        """Unknown action defaults to approve."""
        with patch(
            "src.workflows.graphs.application_assembly.interrupt",
            return_value={},
        ):
            result = await human_review(_state(), _config())

        assert isinstance(result, Command)
        assert result.update["status"] == "approved"
