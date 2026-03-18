"""Tests for RegionalResumeAgent."""

from langchain_core.messages import HumanMessage

from src.agents.regional_resume import RegionalResumeAgent
from src.llm.models import TaskType


class TestRegionalResumeAgent:
    def test_name(self) -> None:
        agent = RegionalResumeAgent()
        assert agent.name == "regional_resume"

    def test_task_type(self) -> None:
        agent = RegionalResumeAgent()
        assert agent.task_type == TaskType.REGIONAL_RESUME

    def test_has_system_prompt(self) -> None:
        agent = RegionalResumeAgent()
        assert "resume" in agent.system_prompt.lower()

    def test_build_messages_full_context(self) -> None:
        agent = RegionalResumeAgent()
        state = {
            "resume_content": "John Doe, Software Engineer...",
            "resume_conventions": {"include_photo": False, "paper_size": "letter"},
            "target_market": "US",
            "cultural_context": {"formality_level": "casual"},
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "US" in messages[0].content
        assert "John Doe" in messages[0].content

    def test_build_messages_minimal(self) -> None:
        agent = RegionalResumeAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "No context provided" in messages[0].content

    def test_process_response(self) -> None:
        agent = RegionalResumeAgent()

        class MockResponse:
            content = "Remove the declaration section..."

        result = agent.process_response(MockResponse(), {})
        assert result == {"resume_guidance": "Remove the declaration section..."}
