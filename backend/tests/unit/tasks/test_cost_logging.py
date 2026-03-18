"""Tests for structured LLM call logging within Celery tasks."""

from unittest.mock import patch

from src.tasks.cost_logging import extract_cost_from_callback, log_llm_call


class TestLogLlmCall:
    async def test_emits_structlog_event_with_all_fields(self):
        """log_llm_call emits llm_call_in_task event with all required fields."""
        with patch("src.tasks.cost_logging.logger") as mock_logger:
            log_llm_call(
                model="claude-sonnet-4-20250514",
                token_count=1500,
                latency_ms=850.5,
                cost_estimate=0.003,
                user_id="user-abc",
                feature_category="cover_letter",
                task_id="task-xyz",
            )

            mock_logger.info.assert_called_once_with(
                "llm_call_in_task",
                model="claude-sonnet-4-20250514",
                token_count=1500,
                latency_ms=850.5,
                cost_estimate=0.003,
                user_id="user-abc",
                feature_category="cover_letter",
                task_id="task-xyz",
            )


class TestExtractCostFromCallback:
    async def test_returns_cost_dict_and_logs(self):
        """extract_cost_from_callback returns dict and calls log_llm_call."""
        with patch("src.tasks.cost_logging.logger"):
            result = extract_cost_from_callback(
                total_tokens=2000,
                total_cost_usd=0.05,
                model="gpt-4o",
                latency_ms=1200.0,
                user_id="user-123",
                feature_category="resume_tailor",
                task_id="task-456",
            )

            assert result == {
                "llm_tokens_used": 2000,
                "llm_cost_usd": 0.05,
            }

    async def test_logs_via_log_llm_call(self):
        """extract_cost_from_callback calls log_llm_call internally."""
        with patch("src.tasks.cost_logging.logger") as mock_logger:
            extract_cost_from_callback(
                total_tokens=500,
                total_cost_usd=0.01,
                model="llama-3",
                latency_ms=300.0,
                user_id="user-abc",
                feature_category="skills_analysis",
                task_id="task-789",
            )

            mock_logger.info.assert_called_once_with(
                "llm_call_in_task",
                model="llama-3",
                token_count=500,
                latency_ms=300.0,
                cost_estimate=0.01,
                user_id="user-abc",
                feature_category="skills_analysis",
                task_id="task-789",
            )
