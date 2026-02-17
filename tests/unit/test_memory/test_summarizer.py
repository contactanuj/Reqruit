"""
Tests for message summarization.

Verifies threshold-based triggering, the split strategy (summarize old,
keep recent), LLM integration via ModelManager, and the graph node wrapper.
The LLM is mocked — these tests focus on the summarization logic, not
the model's output quality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.memory.summarizer import (
    DEFAULT_MAX_MESSAGES,
    summarize_if_needed,
    summarize_messages,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_model_manager():
    """Mock the ModelManager to return a controlled LLM response."""
    manager = MagicMock()
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(
        content="Summary: User discussed Python job requirements."
    )
    manager.get_model.return_value = model

    with patch(
        "src.memory.summarizer.get_model_manager", return_value=manager
    ):
        yield manager, model


def _make_messages(count: int) -> list:
    """Create a list of alternating Human/AI messages."""
    messages = []
    for i in range(count):
        if i % 2 == 0:
            messages.append(HumanMessage(content=f"User message {i}"))
        else:
            messages.append(AIMessage(content=f"AI response {i}"))
    return messages


# ---------------------------------------------------------------------------
# summarize_messages — threshold behavior
# ---------------------------------------------------------------------------


class TestSummarizationThreshold:
    async def test_below_threshold_returns_unchanged(self):
        """Messages below the threshold are returned as-is (no LLM call)."""
        messages = _make_messages(5)
        result = await summarize_messages(messages, max_messages=10)
        assert result == messages

    async def test_at_threshold_returns_unchanged(self):
        """Messages exactly at the threshold are returned as-is."""
        messages = _make_messages(10)
        result = await summarize_messages(messages, max_messages=10)
        assert result == messages

    async def test_empty_messages_returns_empty(self):
        """Empty message list is returned as-is."""
        result = await summarize_messages([], max_messages=10)
        assert result == []


# ---------------------------------------------------------------------------
# summarize_messages — summarization behavior
# ---------------------------------------------------------------------------


class TestSummarizationBehavior:
    async def test_above_threshold_calls_llm(self, mock_model_manager):
        """Messages above threshold trigger an LLM summarization call."""
        _, model = mock_model_manager
        messages = _make_messages(12)

        await summarize_messages(messages, max_messages=10)

        model.ainvoke.assert_called_once()

    async def test_result_starts_with_system_message(self, mock_model_manager):
        """Summarized result starts with a SystemMessage containing the summary."""
        messages = _make_messages(12)

        result = await summarize_messages(messages, max_messages=10)

        assert isinstance(result[0], SystemMessage)
        assert "Summary" in result[0].content

    async def test_preserves_recent_messages(self, mock_model_manager):
        """Recent messages (second half) are preserved verbatim."""
        messages = _make_messages(12)
        split_point = 6  # 12 // 2

        result = await summarize_messages(messages, max_messages=10)

        # First element is the summary SystemMessage
        recent = result[1:]
        assert len(recent) == len(messages[split_point:])
        for original, preserved in zip(messages[split_point:], recent, strict=True):
            assert original.content == preserved.content

    async def test_uses_general_task_type(self, mock_model_manager):
        """Summarization uses TaskType.GENERAL for cheap, fast inference."""
        from src.llm.models import TaskType

        manager, _ = mock_model_manager
        messages = _make_messages(12)

        await summarize_messages(messages, max_messages=10)

        manager.get_model.assert_called_once_with(TaskType.GENERAL)

    async def test_graceful_on_llm_failure(self):
        """If LLM fails, original messages are returned unchanged."""
        with patch(
            "src.memory.summarizer.get_model_manager",
            side_effect=RuntimeError("manager not initialized"),
        ):
            messages = _make_messages(12)
            result = await summarize_messages(messages, max_messages=10)

            # Should return originals, not crash
            assert result == messages


# ---------------------------------------------------------------------------
# summarize_if_needed — graph node
# ---------------------------------------------------------------------------


class TestSummarizeIfNeeded:
    async def test_returns_empty_dict_below_threshold(self):
        """Graph node returns empty dict when no summarization needed."""
        state = {"messages": _make_messages(5)}
        config = {"configurable": {"thread_id": "t1", "user_id": "u1"}}

        result = await summarize_if_needed(state, config)

        assert result == {}

    async def test_returns_summarized_messages_above_threshold(
        self, mock_model_manager
    ):
        """Graph node returns summarized messages when above threshold."""
        state = {"messages": _make_messages(DEFAULT_MAX_MESSAGES + 5)}
        config = {"configurable": {"thread_id": "t1", "user_id": "u1"}}

        result = await summarize_if_needed(state, config)

        assert "messages" in result
        assert isinstance(result["messages"][0], SystemMessage)

    async def test_handles_missing_messages_key(self):
        """Graph node handles state without 'messages' key."""
        state = {}
        config = {"configurable": {"thread_id": "t1", "user_id": "u1"}}

        result = await summarize_if_needed(state, config)

        assert result == {}
