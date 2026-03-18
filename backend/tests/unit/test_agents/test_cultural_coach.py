"""Tests for CulturalCoachAgent."""

from langchain_core.messages import HumanMessage

from src.agents.cultural_coach import CulturalCoachAgent
from src.llm.models import TaskType


class TestCulturalCoachAgent:
    def test_name(self) -> None:
        agent = CulturalCoachAgent()
        assert agent.name == "cultural_coach"

    def test_task_type(self) -> None:
        agent = CulturalCoachAgent()
        assert agent.task_type == TaskType.CULTURAL_COACHING

    def test_has_system_prompt(self) -> None:
        agent = CulturalCoachAgent()
        assert "cultural" in agent.system_prompt.lower()

    def test_build_messages_full_context(self) -> None:
        agent = CulturalCoachAgent()
        state = {
            "target_market": "US",
            "cultural_context": {"formality_level": "casual", "interview_style": "behavioral-heavy"},
            "hiring_process": {"notice_period_norm_days": 14},
            "user_background": "Indian engineer with 5 years experience",
            "specific_concerns": "salary negotiation",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "US" in messages[0].content
        assert "salary negotiation" in messages[0].content

    def test_build_messages_empty(self) -> None:
        agent = CulturalCoachAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "No context provided" in messages[0].content

    def test_process_response(self) -> None:
        agent = CulturalCoachAgent()

        class MockResponse:
            content = "In US interviews, be direct..."

        result = agent.process_response(MockResponse(), {})
        assert result == {"cultural_coaching": "In US interviews, be direct..."}
