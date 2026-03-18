"""Tests for VisaNavigatorAgent."""

from langchain_core.messages import HumanMessage

from src.agents.visa_navigator import VisaNavigatorAgent
from src.llm.models import TaskType


class TestVisaNavigatorAgent:
    def test_name(self) -> None:
        agent = VisaNavigatorAgent()
        assert agent.name == "visa_navigator"

    def test_task_type(self) -> None:
        agent = VisaNavigatorAgent()
        assert agent.task_type == TaskType.VISA_NAVIGATION

    def test_has_system_prompt(self) -> None:
        agent = VisaNavigatorAgent()
        assert "visa" in agent.system_prompt.lower()

    def test_build_messages_full_context(self) -> None:
        agent = VisaNavigatorAgent()
        state = {
            "nationality": "IN",
            "target_market": "US",
            "visa_requirements": [{"type": "H-1B"}],
            "qualifications": ["MS Computer Science"],
            "years_experience": 5,
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "IN" in messages[0].content
        assert "US" in messages[0].content
        assert "H-1B" in messages[0].content

    def test_build_messages_empty(self) -> None:
        agent = VisaNavigatorAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "No context provided" in messages[0].content

    def test_process_response(self) -> None:
        agent = VisaNavigatorAgent()

        class MockResponse:
            content = "H-1B visa requires employer sponsorship..."

        result = agent.process_response(MockResponse(), {})
        assert result == {"visa_analysis": "H-1B visa requires employer sponsorship..."}
