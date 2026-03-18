"""
Tests for BaseAgent — the abstract base class for all LLM-powered agents.

Tests verify the complete LLM call lifecycle: model selection, system prompt
injection, cost tracking, circuit breaker integration, and error handling.
All LLM calls are mocked — no real API calls are made.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base import BaseAgent, _extract_user_id
from src.core.exceptions import LLMProviderError
from src.llm.models import ModelConfig, ProviderName, TaskType

# ---------------------------------------------------------------------------
# Concrete test subclass — implements the two abstract methods
# ---------------------------------------------------------------------------


class StubAgent(BaseAgent):
    """Minimal concrete agent for testing BaseAgent behavior."""

    def build_messages(self, state: dict) -> list:
        return [HumanMessage(content=state.get("input", "test input"))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        return {"output": response.content}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent() -> StubAgent:
    return StubAgent(
        name="test_agent",
        task_type=TaskType.GENERAL,
        system_prompt="You are a test agent.",
    )


@pytest.fixture
def mock_manager():
    """Create a mock ModelManager with all methods pre-configured."""
    manager = MagicMock()
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content="mock response")
    config = ModelConfig(
        provider=ProviderName.ANTHROPIC,
        model_name="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        temperature=0.5,
    )
    manager.get_model_with_config.return_value = (model, config)
    manager.create_cost_callback.return_value = MagicMock()
    return manager, model, config


# ---------------------------------------------------------------------------
# Agent initialization
# ---------------------------------------------------------------------------


class TestAgentInit:
    def test_stores_name(self, agent: StubAgent):
        assert agent.name == "test_agent"

    def test_stores_task_type(self, agent: StubAgent):
        assert agent.task_type == TaskType.GENERAL

    def test_stores_system_prompt(self, agent: StubAgent):
        assert agent.system_prompt == "You are a test agent."


# ---------------------------------------------------------------------------
# __call__ — the LLM call lifecycle
# ---------------------------------------------------------------------------


class TestAgentCall:
    async def test_returns_processed_response(self, agent, mock_manager):
        manager, model, _ = mock_manager
        state = {"input": "hello"}
        config = {"configurable": {"user_id": "user123"}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, config)

        assert result == {"output": "mock response"}

    async def test_system_prompt_prepended_to_messages(self, agent, mock_manager):
        manager, model, _ = mock_manager
        state = {"input": "hello"}
        config = {"configurable": {"user_id": "user123"}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            await agent(state, config)

        # Verify the messages passed to ainvoke
        call_args = model.ainvoke.call_args
        messages = call_args[0][0]
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "You are a test agent."
        assert isinstance(messages[1], HumanMessage)
        assert messages[1].content == "hello"

    async def test_correct_task_type_passed(self, agent, mock_manager):
        manager, model, _ = mock_manager
        state = {"input": "test"}
        config = {"configurable": {"user_id": "user123"}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            await agent(state, config)

        manager.get_model_with_config.assert_called_once_with(TaskType.GENERAL)

    async def test_cost_callback_created_with_user_id(self, agent, mock_manager):
        manager, model, _ = mock_manager
        state = {"input": "test"}
        config = {"configurable": {"user_id": "user456"}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            await agent(state, config)

        manager.create_cost_callback.assert_called_once_with(
            user_id="user456",
            agent="test_agent",
            task_type="general",
        )

    async def test_callback_passed_to_model_ainvoke(self, agent, mock_manager):
        manager, model, _ = mock_manager
        callback = MagicMock()
        manager.create_cost_callback.return_value = callback
        state = {"input": "test"}
        config = {"configurable": {"user_id": "user123"}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            await agent(state, config)

        call_kwargs = model.ainvoke.call_args
        assert call_kwargs[1]["config"]["callbacks"] == [callback]

    async def test_record_success_on_successful_call(self, agent, mock_manager):
        manager, model, config = mock_manager
        state = {"input": "test"}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            await agent(state, {"configurable": {"user_id": "u1"}})

        manager.record_success.assert_called_once_with(ProviderName.ANTHROPIC)

    async def test_record_failure_and_raise_on_llm_error(self, agent, mock_manager):
        manager, model, config = mock_manager
        model.ainvoke.side_effect = RuntimeError("API timeout")
        state = {"input": "test"}

        with (
            patch("src.agents.base.get_model_manager", return_value=manager),
            pytest.raises(LLMProviderError, match="LLM call failed"),
        ):
            await agent(state, {"configurable": {"user_id": "u1"}})

        manager.record_failure.assert_called_once_with(ProviderName.ANTHROPIC)
        manager.record_success.assert_not_called()

    async def test_reraises_existing_llm_provider_error(self, agent, mock_manager):
        manager, model, config = mock_manager
        original_error = LLMProviderError(
            detail="rate limited", provider="anthropic"
        )
        model.ainvoke.side_effect = original_error
        state = {"input": "test"}

        with (
            patch("src.agents.base.get_model_manager", return_value=manager),
            pytest.raises(LLMProviderError, match="rate limited"),
        ):
            await agent(state, {"configurable": {"user_id": "u1"}})

        manager.record_failure.assert_called_once_with(ProviderName.ANTHROPIC)

    async def test_handles_none_config(self, agent, mock_manager):
        """user_id defaults to 'unknown' when config is None."""
        manager, model, _ = mock_manager
        state = {"input": "test"}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, None)

        assert result == {"output": "mock response"}
        manager.create_cost_callback.assert_called_once_with(
            user_id="unknown",
            agent="test_agent",
            task_type="general",
        )

    async def test_handles_empty_configurable(self, agent, mock_manager):
        """user_id defaults to 'unknown' when configurable is empty."""
        manager, model, _ = mock_manager
        state = {"input": "test"}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            await agent(state, {"configurable": {}})

        manager.create_cost_callback.assert_called_once_with(
            user_id="unknown",
            agent="test_agent",
            task_type="general",
        )


# ---------------------------------------------------------------------------
# _extract_user_id helper
# ---------------------------------------------------------------------------


class TestExtractUserId:
    def test_extracts_from_config(self):
        assert _extract_user_id({"configurable": {"user_id": "abc"}}) == "abc"

    def test_returns_unknown_for_none(self):
        assert _extract_user_id(None) == "unknown"

    def test_returns_unknown_for_missing_configurable(self):
        assert _extract_user_id({}) == "unknown"

    def test_returns_unknown_for_missing_user_id(self):
        assert _extract_user_id({"configurable": {}}) == "unknown"
