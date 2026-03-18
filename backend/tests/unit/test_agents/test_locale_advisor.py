"""Tests for LocaleAdvisorAgent."""

from langchain_core.messages import HumanMessage

from src.agents.locale_advisor import LocaleAdvisorAgent
from src.llm.models import TaskType


class TestLocaleAdvisorAgent:
    """Tests for LocaleAdvisorAgent initialization and message building."""

    def test_name(self) -> None:
        agent = LocaleAdvisorAgent()
        assert agent.name == "locale_advisor"

    def test_task_type(self) -> None:
        agent = LocaleAdvisorAgent()
        assert agent.task_type == TaskType.LOCALE_ADVISORY

    def test_has_system_prompt(self) -> None:
        agent = LocaleAdvisorAgent()
        assert "market-aware" in agent.system_prompt.lower()

    def test_build_messages_with_all_context(self) -> None:
        agent = LocaleAdvisorAgent()
        state = {
            "market_config": {"region_code": "IN", "region_name": "India"},
            "user_locale_profile": {"primary_market": "IN"},
            "query": "What salary should I expect?",
        }

        messages = agent.build_messages(state)

        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "India" in messages[0].content
        assert "What salary should I expect?" in messages[0].content

    def test_build_messages_query_only(self) -> None:
        agent = LocaleAdvisorAgent()
        state = {"query": "Help me with my resume"}

        messages = agent.build_messages(state)

        assert len(messages) == 1
        assert "Help me with my resume" in messages[0].content

    def test_build_messages_empty_state(self) -> None:
        agent = LocaleAdvisorAgent()
        state = {}

        messages = agent.build_messages(state)

        assert len(messages) == 1

    def test_process_response(self) -> None:
        agent = LocaleAdvisorAgent()

        class MockResponse:
            content = "Here is my advice..."

        result = agent.process_response(MockResponse(), {})

        assert result == {"advisor_response": "Here is my advice..."}
