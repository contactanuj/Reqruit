"""Tests for SuccessPatternAgent."""

from langchain_core.messages import HumanMessage

from src.agents.success_pattern import SuccessPatternAgent
from src.llm.models import TaskType


class TestSuccessPatternAgent:
    def test_name(self) -> None:
        agent = SuccessPatternAgent()
        assert agent.name == "success_pattern"

    def test_task_type(self) -> None:
        agent = SuccessPatternAgent()
        assert agent.task_type == TaskType.SUCCESS_PATTERN

    def test_has_system_prompt(self) -> None:
        agent = SuccessPatternAgent()
        assert "data analyst" in agent.system_prompt.lower()

    def test_build_messages_with_data(self) -> None:
        agent = SuccessPatternAgent()
        state = {
            "analytics_data": '{"response_rate": 0.3, "top_method": "referral"}'
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "response_rate" in messages[0].content

    def test_build_messages_empty(self) -> None:
        agent = SuccessPatternAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1

    def test_process_response(self) -> None:
        agent = SuccessPatternAgent()

        class MockResponse:
            content = '{"top_performing_strategies": ["referral"], "confidence_level": "high"}'

        result = agent.process_response(MockResponse(), {})
        assert "success_insights" in result
        assert "top_performing_strategies" in result["success_insights"]
