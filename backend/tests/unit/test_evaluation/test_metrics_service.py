"""Unit tests for src/services/metrics_service.py."""

from unittest.mock import AsyncMock, patch

from beanie import PydanticObjectId

from src.services.metrics_service import (
    AgentBreakdown,
    MetricsService,
    ModelBreakdown,
    UsageSummary,
)


def _make_object_id() -> PydanticObjectId:
    return PydanticObjectId("507f1f77bcf86cd799439011")


class TestGetUserSummary:
    async def test_returns_zero_summary_when_no_records(self):
        svc = MetricsService()
        with patch.object(
            type(svc).__mro__[0],  # MetricsService itself
            "get_user_summary",
            new_callable=AsyncMock,
        ):
            pass  # test the aggregate path via mocking LLMUsage

        # Mock the aggregate pipeline returning empty list
        with patch("src.services.metrics_service.LLMUsage") as mock_usage:
            mock_usage.aggregate.return_value.to_list = AsyncMock(return_value=[])
            result = await svc.get_user_summary(_make_object_id(), days=30)

        assert isinstance(result, UsageSummary)
        assert result.total_cost_usd == 0.0
        assert result.total_tokens == 0
        assert result.total_calls == 0
        assert result.window_days == 30

    async def test_returns_aggregated_values(self):
        svc = MetricsService()
        fake_result = [
            {"total_cost_usd": 0.0123456, "total_tokens": 5000, "total_calls": 10}
        ]
        with patch("src.services.metrics_service.LLMUsage") as mock_usage:
            mock_usage.aggregate.return_value.to_list = AsyncMock(
                return_value=fake_result
            )
            result = await svc.get_user_summary(_make_object_id(), days=7)

        assert result.total_cost_usd == round(0.0123456, 6)
        assert result.total_tokens == 5000
        assert result.total_calls == 10
        assert result.window_days == 7

    async def test_cost_is_rounded_to_6_decimals(self):
        svc = MetricsService()
        fake_result = [
            {"total_cost_usd": 0.00000012345, "total_tokens": 100, "total_calls": 1}
        ]
        with patch("src.services.metrics_service.LLMUsage") as mock_usage:
            mock_usage.aggregate.return_value.to_list = AsyncMock(
                return_value=fake_result
            )
            result = await svc.get_user_summary(_make_object_id())

        assert result.total_cost_usd == round(0.00000012345, 6)


class TestGetUserAgentBreakdown:
    async def test_returns_agent_list_sorted_by_cost(self):
        svc = MetricsService()
        fake_results = [
            {"_id": "cover_letter_writer", "cost_usd": 0.05, "total_tokens": 2000, "call_count": 5},
            {"_id": "resume_tailor", "cost_usd": 0.02, "total_tokens": 800, "call_count": 2},
        ]
        with patch("src.services.metrics_service.LLMUsage") as mock_usage:
            mock_usage.aggregate.return_value.to_list = AsyncMock(
                return_value=fake_results
            )
            result = await svc.get_user_agent_breakdown(_make_object_id(), days=30)

        assert len(result) == 2
        assert isinstance(result[0], AgentBreakdown)
        assert result[0].agent == "cover_letter_writer"
        assert result[0].cost_usd == 0.05
        assert result[0].call_count == 5

    async def test_empty_returns_empty_list(self):
        svc = MetricsService()
        with patch("src.services.metrics_service.LLMUsage") as mock_usage:
            mock_usage.aggregate.return_value.to_list = AsyncMock(return_value=[])
            result = await svc.get_user_agent_breakdown(_make_object_id())

        assert result == []

    async def test_none_agent_id_becomes_unknown(self):
        svc = MetricsService()
        fake_results = [
            {"_id": None, "cost_usd": 0.01, "total_tokens": 100, "call_count": 1}
        ]
        with patch("src.services.metrics_service.LLMUsage") as mock_usage:
            mock_usage.aggregate.return_value.to_list = AsyncMock(
                return_value=fake_results
            )
            result = await svc.get_user_agent_breakdown(_make_object_id())

        assert result[0].agent == "unknown"


class TestIsOverBudget:
    async def test_returns_false_when_under_limit(self):
        svc = MetricsService()
        with patch.object(
            svc, "get_user_summary", new_callable=AsyncMock,
            return_value=UsageSummary(total_cost_usd=0.05, total_tokens=100, total_calls=1, window_days=1),
        ):
            result = await svc.is_over_budget(_make_object_id(), daily_limit_usd=1.0)
        assert result is False

    async def test_returns_true_when_at_limit(self):
        svc = MetricsService()
        with patch.object(
            svc, "get_user_summary", new_callable=AsyncMock,
            return_value=UsageSummary(total_cost_usd=1.0, total_tokens=100, total_calls=1, window_days=1),
        ):
            result = await svc.is_over_budget(_make_object_id(), daily_limit_usd=1.0)
        assert result is True

    async def test_returns_false_on_database_error(self):
        """Fail open — never block a user due to a metrics query error."""
        svc = MetricsService()
        with patch.object(
            svc, "get_user_summary", new_callable=AsyncMock,
            side_effect=Exception("DB connection refused"),
        ):
            result = await svc.is_over_budget(_make_object_id(), daily_limit_usd=1.0)
        assert result is False


class TestGetModelBreakdown:
    async def test_returns_model_list(self):
        svc = MetricsService()
        fake_results = [
            {
                "_id": {"model": "claude-sonnet-4-6", "provider": "anthropic"},
                "cost_usd": 0.10,
                "total_tokens": 10000,
                "call_count": 20,
            },
            {
                "_id": {"model": "llama-3.1-8b-instant", "provider": "groq"},
                "cost_usd": 0.0,
                "total_tokens": 5000,
                "call_count": 50,
            },
        ]
        with patch("src.services.metrics_service.LLMUsage") as mock_usage:
            mock_usage.aggregate.return_value.to_list = AsyncMock(
                return_value=fake_results
            )
            result = await svc.get_model_breakdown(days=7)

        assert len(result) == 2
        assert isinstance(result[0], ModelBreakdown)
        assert result[0].model == "claude-sonnet-4-6"
        assert result[0].provider == "anthropic"
        assert result[1].provider == "groq"

    async def test_missing_id_fields_become_unknown(self):
        svc = MetricsService()
        fake_results = [
            {"_id": {}, "cost_usd": 0.01, "total_tokens": 100, "call_count": 1}
        ]
        with patch("src.services.metrics_service.LLMUsage") as mock_usage:
            mock_usage.aggregate.return_value.to_list = AsyncMock(
                return_value=fake_results
            )
            result = await svc.get_model_breakdown()

        assert result[0].model == "unknown"
        assert result[0].provider == "unknown"
