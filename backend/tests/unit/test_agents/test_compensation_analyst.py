"""Tests for CompensationAnalystAgent."""

from langchain_core.messages import HumanMessage

from src.agents.compensation_analyst import CompensationAnalystAgent
from src.llm.models import TaskType


class TestCompensationAnalystAgent:
    """Tests for CompensationAnalystAgent initialization and message building."""

    def test_name(self) -> None:
        agent = CompensationAnalystAgent()
        assert agent.name == "compensation_analyst"

    def test_task_type(self) -> None:
        agent = CompensationAnalystAgent()
        assert agent.task_type == TaskType.COMPENSATION_ANALYSIS

    def test_has_system_prompt(self) -> None:
        agent = CompensationAnalystAgent()
        assert "compensation" in agent.system_prompt.lower()

    def test_build_messages_with_data(self) -> None:
        agent = CompensationAnalystAgent()
        state = {
            "compensation_data": {
                "source": {"amount": 1000000, "currency": "INR"},
                "target": {"amount": 12000, "currency": "USD"},
            }
        }

        messages = agent.build_messages(state)

        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "1000000" in messages[0].content

    def test_build_messages_empty_data(self) -> None:
        agent = CompensationAnalystAgent()
        state = {}

        messages = agent.build_messages(state)

        assert len(messages) == 1
        # Should still produce a message (with empty JSON)

    def test_process_response(self) -> None:
        agent = CompensationAnalystAgent()

        class MockResponse:
            content = "The Indian offer provides better purchasing power..."

        result = agent.process_response(MockResponse(), {})

        assert result == {"analysis_narrative": "The Indian offer provides better purchasing power..."}
