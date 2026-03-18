"""
Tests for the generate_cover_letter node in the application assembly graph.

Verifies CoverLetterWriter agent is called with correct state mapping
and that the cover letter is stored properly in graph state.
"""

from unittest.mock import AsyncMock, patch

from src.workflows.graphs.application_assembly import generate_cover_letter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(user_id: str = "user-123") -> dict:
    return {"configurable": {"user_id": user_id, "thread_id": "test-thread"}}


def _state(**overrides) -> dict:
    base = {
        "tailored_resume": "# Tailored Resume\nPython expert with 8 years",
        "resume_text": "Full resume text — should not be primary",
        "decoded_jd": '{"required_skills": ["Python", "FastAPI"]}',
        "feedback": "",
        "messages": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateCoverLetter:
    """Tests for the generate_cover_letter graph node."""

    async def test_calls_cover_letter_writer(self) -> None:
        """AC #1: Calls CoverLetterWriter agent."""
        with patch(
            "src.workflows.graphs.application_assembly._cover_letter_writer",
            new_callable=AsyncMock,
        ) as mock_writer:
            mock_writer.return_value = {"cover_letter": "Dear Hiring Manager..."}
            await generate_cover_letter(_state(), _config())
            mock_writer.assert_called_once()

    async def test_uses_tailored_resume_as_resume_text(self) -> None:
        """AC #1: Uses tailored_resume (not raw resume_text) for the cover letter."""
        with patch(
            "src.workflows.graphs.application_assembly._cover_letter_writer",
            new_callable=AsyncMock,
        ) as mock_writer:
            mock_writer.return_value = {"cover_letter": "Dear..."}
            await generate_cover_letter(_state(), _config())

            call_args = mock_writer.call_args[0][0]
            assert call_args["resume_text"] == "# Tailored Resume\nPython expert with 8 years"

    async def test_maps_decoded_jd_to_requirements_analysis(self) -> None:
        """AC #1: Maps decoded_jd to CoverLetterWriter's requirements_analysis key."""
        with patch(
            "src.workflows.graphs.application_assembly._cover_letter_writer",
            new_callable=AsyncMock,
        ) as mock_writer:
            mock_writer.return_value = {"cover_letter": "Dear..."}
            await generate_cover_letter(_state(), _config())

            call_args = mock_writer.call_args[0][0]
            assert "requirements_analysis" in call_args

    async def test_stores_cover_letter_in_result(self) -> None:
        """AC #1: cover_letter stored in result dict."""
        with patch(
            "src.workflows.graphs.application_assembly._cover_letter_writer",
            new_callable=AsyncMock,
        ) as mock_writer:
            mock_writer.return_value = {"cover_letter": "Dear Hiring Manager, I am writing..."}
            result = await generate_cover_letter(_state(), _config())

            assert result["cover_letter"] == "Dear Hiring Manager, I am writing..."

    async def test_status_set_to_cover_letter_generated(self) -> None:
        """AC #1: Status updated to 'cover_letter_generated'."""
        with patch(
            "src.workflows.graphs.application_assembly._cover_letter_writer",
            new_callable=AsyncMock,
        ) as mock_writer:
            mock_writer.return_value = {"cover_letter": "content"}
            result = await generate_cover_letter(_state(), _config())

            assert result["status"] == "cover_letter_generated"

    async def test_falls_back_to_resume_text_when_no_tailored(self) -> None:
        """Falls back to resume_text if tailored_resume is empty."""
        with patch(
            "src.workflows.graphs.application_assembly._cover_letter_writer",
            new_callable=AsyncMock,
        ) as mock_writer:
            mock_writer.return_value = {"cover_letter": "Dear..."}
            await generate_cover_letter(_state(tailored_resume=""), _config())

            call_args = mock_writer.call_args[0][0]
            assert call_args["resume_text"] == "Full resume text — should not be primary"
