"""
Tests for RequirementsAnalyst and CoverLetterWriter agents.

Verifies agent configuration (task type, name), message construction
(build_messages), and response extraction (process_response). LLM calls
are not made — these tests focus on the agent-specific logic that sits
on top of BaseAgent.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.agents.cover_letter import CoverLetterWriter, RequirementsAnalyst
from src.llm.models import ModelConfig, ProviderName, TaskType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_manager():
    """Pre-configured mock ModelManager for agent call tests."""
    manager = MagicMock()
    model = AsyncMock()
    config = ModelConfig(
        provider=ProviderName.ANTHROPIC,
        model_name="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        temperature=0.7,
    )
    manager.get_model_with_config.return_value = (model, config)
    manager.create_cost_callback.return_value = MagicMock()
    return manager, model


# ---------------------------------------------------------------------------
# RequirementsAnalyst
# ---------------------------------------------------------------------------


class TestRequirementsAnalyst:
    def test_task_type(self):
        agent = RequirementsAnalyst()
        assert agent.task_type == TaskType.DATA_EXTRACTION

    def test_name(self):
        agent = RequirementsAnalyst()
        assert agent.name == "requirements_analyst"

    def test_build_messages_includes_job_description(self):
        agent = RequirementsAnalyst()
        state = {"job_description": "Senior Python Developer at Acme Corp"}
        messages = agent.build_messages(state)

        assert len(messages) == 1
        assert "Senior Python Developer at Acme Corp" in messages[0].content

    def test_build_messages_handles_missing_job_description(self):
        agent = RequirementsAnalyst()
        state = {}
        messages = agent.build_messages(state)

        # Should not crash — returns a message with empty JD
        assert len(messages) == 1

    def test_process_response_extracts_analysis(self):
        agent = RequirementsAnalyst()
        response = AIMessage(content="1. Python\n2. FastAPI\n3. 5+ years")
        result = agent.process_response(response, {})

        assert result == {
            "requirements_analysis": "1. Python\n2. FastAPI\n3. 5+ years"
        }

    async def test_full_call_returns_analysis(self, mock_manager):
        manager, model = mock_manager
        model.ainvoke.return_value = AIMessage(content="Key requirements: ...")

        agent = RequirementsAnalyst()
        state = {"job_description": "We need a Python dev"}
        config = {"configurable": {"user_id": "u1"}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, config)

        assert result == {"requirements_analysis": "Key requirements: ..."}


# ---------------------------------------------------------------------------
# CoverLetterWriter
# ---------------------------------------------------------------------------


class TestCoverLetterWriter:
    def test_task_type(self):
        agent = CoverLetterWriter()
        assert agent.task_type == TaskType.COVER_LETTER

    def test_name(self):
        agent = CoverLetterWriter()
        assert agent.name == "cover_letter_writer"

    def test_build_messages_includes_requirements_and_resume(self):
        agent = CoverLetterWriter()
        state = {
            "requirements_analysis": "Need Python + FastAPI",
            "resume_text": "10 years Python experience",
            "feedback": "",
            "cover_letter": "",
        }
        messages = agent.build_messages(state)

        assert len(messages) == 1
        content = messages[0].content
        assert "Need Python + FastAPI" in content
        assert "10 years Python experience" in content
        assert "Write a tailored cover letter" in content

    def test_build_messages_includes_feedback_on_revision(self):
        agent = CoverLetterWriter()
        state = {
            "requirements_analysis": "Need Python",
            "resume_text": "Python dev",
            "feedback": "Make it more specific",
            "cover_letter": "Dear Hiring Manager...",
        }
        messages = agent.build_messages(state)

        content = messages[0].content
        assert "Make it more specific" in content
        assert "Dear Hiring Manager..." in content
        assert "Revision Feedback" in content
        assert "revise the cover letter" in content

    def test_build_messages_no_revision_without_feedback(self):
        """Even if cover_letter exists, no revision section without feedback."""
        agent = CoverLetterWriter()
        state = {
            "requirements_analysis": "Need Python",
            "resume_text": "Python dev",
            "feedback": "",
            "cover_letter": "Dear Hiring Manager...",
        }
        messages = agent.build_messages(state)

        content = messages[0].content
        assert "Revision Feedback" not in content
        assert "Write a tailored cover letter" in content

    def test_process_response_extracts_cover_letter(self):
        agent = CoverLetterWriter()
        response = AIMessage(content="Dear Hiring Manager,\n\nI am writing...")
        result = agent.process_response(response, {})

        assert result == {
            "cover_letter": "Dear Hiring Manager,\n\nI am writing..."
        }

    async def test_full_call_returns_cover_letter(self, mock_manager):
        manager, model = mock_manager
        model.ainvoke.return_value = AIMessage(content="Dear Sir/Madam...")

        agent = CoverLetterWriter()
        state = {
            "requirements_analysis": "Python required",
            "resume_text": "Experienced Python dev",
            "feedback": "",
            "cover_letter": "",
        }
        config = {"configurable": {"user_id": "u1"}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, config)

        assert result == {"cover_letter": "Dear Sir/Madam..."}
