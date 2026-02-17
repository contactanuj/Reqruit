"""
Tests for cost calculation and the CostTrackingCallback.

Tests verify:
- Correct cost calculation from the cost table
- Token extraction from different provider response formats
- LLMUsage document creation in the callback
- Graceful handling of missing or malformed data
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.outputs import LLMResult

from src.llm.cost_tracker import (
    CostTrackingCallback,
    _extract_model_name,
    _extract_token_usage,
    _infer_provider,
    calculate_cost,
)


class TestCalculateCost:
    """Test the pure cost calculation function."""

    def test_known_model_returns_correct_cost(self):
        """Claude Sonnet: $3/M input, $15/M output."""
        cost = calculate_cost(
            "claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=500,
        )
        # (1000 * 3.00 + 500 * 15.00) / 1_000_000 = 0.0105
        assert cost == pytest.approx(0.0105)

    def test_groq_free_model_returns_zero(self):
        cost = calculate_cost(
            "llama-3.3-70b-versatile",
            input_tokens=10000,
            output_tokens=5000,
        )
        assert cost == 0.0

    def test_unknown_model_returns_zero(self):
        """Unknown models default to zero cost (safe fallback)."""
        cost = calculate_cost(
            "some-future-model",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost == 0.0

    def test_zero_tokens_returns_zero(self):
        cost = calculate_cost(
            "claude-sonnet-4-5-20250929",
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == 0.0

    def test_gpt4o_mini_cost(self):
        """GPT-4o-mini: $0.15/M input, $0.60/M output."""
        cost = calculate_cost(
            "gpt-4o-mini",
            input_tokens=2_000_000,
            output_tokens=1_000_000,
        )
        # (2M * 0.15 + 1M * 0.60) / 1M = 0.3 + 0.6 = 0.9
        assert cost == pytest.approx(0.9)


class TestExtractTokenUsage:
    """Test token extraction from provider-specific response formats."""

    def test_anthropic_format(self):
        """Anthropic puts usage under {"usage": {"input_tokens", "output_tokens"}}."""
        llm_output = {"usage": {"input_tokens": 100, "output_tokens": 50}}
        assert _extract_token_usage(llm_output) == (100, 50)

    def test_openai_format(self):
        """OpenAI puts usage under {"token_usage": {"prompt_tokens", "completion_tokens"}}."""
        llm_output = {
            "token_usage": {
                "prompt_tokens": 200,
                "completion_tokens": 75,
                "total_tokens": 275,
            }
        }
        assert _extract_token_usage(llm_output) == (200, 75)

    def test_empty_output_returns_zeros(self):
        assert _extract_token_usage({}) == (0, 0)

    def test_missing_usage_keys_returns_zeros(self):
        """Handles responses without any usage data."""
        llm_output = {"model": "some-model"}
        assert _extract_token_usage(llm_output) == (0, 0)


class TestExtractModelName:
    """Test model name extraction from provider-specific responses."""

    def test_anthropic_model_field(self):
        assert _extract_model_name({"model": "claude-sonnet-4-5-20250929"}) == (
            "claude-sonnet-4-5-20250929"
        )

    def test_openai_model_name_field(self):
        assert _extract_model_name({"model_name": "gpt-4o-mini"}) == "gpt-4o-mini"

    def test_missing_model_returns_unknown(self):
        assert _extract_model_name({}) == "unknown"

    def test_anthropic_preferred_over_openai(self):
        """If both fields exist, 'model' (Anthropic) takes precedence."""
        llm_output = {"model": "claude-model", "model_name": "openai-model"}
        assert _extract_model_name(llm_output) == "claude-model"


class TestInferProvider:
    """Test provider inference from model name prefixes."""

    def test_claude_is_anthropic(self):
        assert _infer_provider("claude-sonnet-4-5-20250929") == "anthropic"

    def test_gpt_is_openai(self):
        assert _infer_provider("gpt-4o-mini") == "openai"

    def test_llama_is_groq(self):
        assert _infer_provider("llama-3.3-70b-versatile") == "groq"

    def test_unknown_prefix_returns_unknown(self):
        assert _infer_provider("some-unknown-model") == "unknown"


class TestCostTrackingCallback:
    """Test the LangChain callback that records LLM usage to MongoDB."""

    @pytest.fixture
    def callback(self):
        return CostTrackingCallback(
            user_id="user123",
            agent="cover_letter_writer",
            task_type="cover_letter",
        )

    def _make_llm_result(self, llm_output: dict) -> LLMResult:
        """Create a minimal LLMResult with the given llm_output."""
        return LLMResult(generations=[[]], llm_output=llm_output)

    async def test_on_llm_end_creates_usage_record(self, callback):
        """Verify that on_llm_end creates and inserts an LLMUsage document."""
        response = self._make_llm_result({
            "model": "claude-sonnet-4-5-20250929",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        })

        mock_insert = AsyncMock()
        with patch(
            "src.db.documents.llm_usage.LLMUsage", autospec=False
        ) as mock_usage_cls:
            mock_instance = MagicMock()
            mock_instance.insert = mock_insert
            mock_usage_cls.return_value = mock_instance

            await callback.on_llm_end(response)

            mock_usage_cls.assert_called_once()
            call_kwargs = mock_usage_cls.call_args[1]
            assert call_kwargs["user_id"] == "user123"
            assert call_kwargs["agent"] == "cover_letter_writer"
            assert call_kwargs["task_type"] == "cover_letter"
            assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
            assert call_kwargs["provider"] == "anthropic"
            assert call_kwargs["input_tokens"] == 100
            assert call_kwargs["output_tokens"] == 50
            assert call_kwargs["total_tokens"] == 150
            assert call_kwargs["cost_usd"] == pytest.approx(0.00105)
            mock_insert.assert_awaited_once()

    async def test_on_llm_end_handles_missing_usage_gracefully(self, callback):
        """Empty llm_output should not crash — records zeros."""
        response = self._make_llm_result({})

        mock_insert = AsyncMock()
        with patch(
            "src.db.documents.llm_usage.LLMUsage", autospec=False
        ) as mock_usage_cls:
            mock_instance = MagicMock()
            mock_instance.insert = mock_insert
            mock_usage_cls.return_value = mock_instance

            await callback.on_llm_end(response)

            call_kwargs = mock_usage_cls.call_args[1]
            assert call_kwargs["input_tokens"] == 0
            assert call_kwargs["output_tokens"] == 0
            assert call_kwargs["cost_usd"] == 0.0

    async def test_on_llm_end_handles_none_llm_output(self, callback):
        """llm_output=None (some edge cases) should not crash."""
        response = LLMResult(generations=[[]], llm_output=None)

        with patch(
            "src.db.documents.llm_usage.LLMUsage", autospec=False
        ) as mock_usage_cls:
            mock_instance = MagicMock()
            mock_instance.insert = AsyncMock()
            mock_usage_cls.return_value = mock_instance

            await callback.on_llm_end(response)
            mock_usage_cls.assert_called_once()

    async def test_on_llm_end_survives_insert_failure(self, callback):
        """Database failure in cost tracking should not raise."""
        response = self._make_llm_result({
            "model": "claude-sonnet-4-5-20250929",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        })

        with patch(
            "src.db.documents.llm_usage.LLMUsage", autospec=False
        ) as mock_usage_cls:
            mock_instance = MagicMock()
            mock_instance.insert = AsyncMock(
                side_effect=RuntimeError("DB unavailable")
            )
            mock_usage_cls.return_value = mock_instance

            # Should not raise — cost tracking failures are swallowed.
            await callback.on_llm_end(response)

    async def test_latency_tracking(self, callback):
        """Latency is calculated from on_llm_start to on_llm_end."""
        # Simulate on_llm_start recording the time.
        await callback.on_llm_start({}, [])
        assert callback._start_time is not None

        response = self._make_llm_result({
            "model": "gpt-4o-mini",
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

        with patch(
            "src.db.documents.llm_usage.LLMUsage", autospec=False
        ) as mock_usage_cls:
            mock_instance = MagicMock()
            mock_instance.insert = AsyncMock()
            mock_usage_cls.return_value = mock_instance

            await callback.on_llm_end(response)

            call_kwargs = mock_usage_cls.call_args[1]
            # Latency should be a non-negative integer (milliseconds).
            assert isinstance(call_kwargs["latency_ms"], int)
            assert call_kwargs["latency_ms"] >= 0

    async def test_on_chat_model_start_records_time(self, callback):
        """on_chat_model_start also records the start time."""
        await callback.on_chat_model_start({}, [[]])
        assert callback._start_time is not None
