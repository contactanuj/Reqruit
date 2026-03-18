"""
Tests for the load_locale node in the application assembly graph.

Verifies locale loading from user profile and market config,
default-to-US behavior, and correct state updates.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from src.workflows.graphs.application_assembly import load_locale


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(user_id: str = "user-123") -> dict:
    return {"configurable": {"user_id": user_id, "thread_id": "test-thread"}}


def _state() -> dict:
    return {"locale_context": ""}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoadLocale:
    async def test_india_user_gets_in_formatting(self) -> None:
        """AC #1: IN user gets India formatting rules."""
        mock_user = MagicMock()
        mock_user.locale_profile = MagicMock(
            primary_market="IN", target_markets=[]
        )

        mock_market_config = MagicMock()
        mock_market_config.resume_conventions = MagicMock(
            include_photo=False,
            include_dob=True,
            include_declaration=True,
            expected_pages_min=2,
            expected_pages_max=3,
            paper_size="A4",
            expected_salary_field=True,
        )

        with (
            patch(
                "src.workflows.graphs.application_assembly.User"
            ) as mock_user_cls,
            patch(
                "src.workflows.graphs.application_assembly._locale_service"
            ) as mock_svc,
        ):
            mock_user_cls.find_one = AsyncMock(return_value=mock_user)
            mock_user_cls.id = "user-123"
            mock_svc.get_market_config = AsyncMock(
                return_value=mock_market_config
            )
            result = await load_locale(_state(), _config())

        assert "FORMAT FOR IN MARKET" in result["locale_context"]
        assert "A4" in result["locale_context"]
        assert result["locale_defaulted"] is False

    async def test_us_user_gets_us_formatting(self) -> None:
        """AC #3: US user gets US formatting rules."""
        mock_user = MagicMock()
        mock_user.locale_profile = MagicMock(
            primary_market="US", target_markets=[]
        )

        mock_market_config = MagicMock()
        mock_market_config.resume_conventions = MagicMock(
            include_photo=False,
            include_dob=False,
            include_declaration=False,
            expected_pages_min=1,
            expected_pages_max=1,
            paper_size="letter",
            expected_salary_field=False,
        )

        with (
            patch(
                "src.workflows.graphs.application_assembly.User"
            ) as mock_user_cls,
            patch(
                "src.workflows.graphs.application_assembly._locale_service"
            ) as mock_svc,
        ):
            mock_user_cls.find_one = AsyncMock(return_value=mock_user)
            mock_user_cls.id = "user-123"
            mock_svc.get_market_config = AsyncMock(
                return_value=mock_market_config
            )
            result = await load_locale(_state(), _config())

        assert "FORMAT FOR US MARKET" in result["locale_context"]
        assert "letter" in result["locale_context"].lower()
        assert result["locale_defaulted"] is False

    async def test_no_locale_defaults_to_us(self) -> None:
        """AC #5: No locale set defaults to US with locale_defaulted flag."""
        mock_user = MagicMock()
        mock_user.locale_profile = None

        with patch(
            "src.workflows.graphs.application_assembly.User"
        ) as mock_user_cls:
            mock_user_cls.find_one = AsyncMock(return_value=mock_user)
            mock_user_cls.id = "user-123"
            result = await load_locale(_state(), _config())

        assert "FORMAT FOR US MARKET" in result["locale_context"]
        assert "locale_defaulted: true" in result["locale_context"]
        assert result["locale_defaulted"] is True

    async def test_no_user_defaults_to_us(self) -> None:
        """AC #5: No user found defaults to US."""
        with patch(
            "src.workflows.graphs.application_assembly.User"
        ) as mock_user_cls:
            mock_user_cls.find_one = AsyncMock(return_value=None)
            mock_user_cls.id = "user-123"
            result = await load_locale(_state(), _config())

        assert "FORMAT FOR US MARKET" in result["locale_context"]
        assert "locale_defaulted: true" in result["locale_context"]
        assert result["locale_defaulted"] is True

    async def test_empty_primary_market_defaults_to_us(self) -> None:
        """AC #5: Empty primary_market defaults to US."""
        mock_user = MagicMock()
        mock_user.locale_profile = MagicMock(
            primary_market="", target_markets=[]
        )

        with patch(
            "src.workflows.graphs.application_assembly.User"
        ) as mock_user_cls:
            mock_user_cls.find_one = AsyncMock(return_value=mock_user)
            mock_user_cls.id = "user-123"
            result = await load_locale(_state(), _config())

        assert "FORMAT FOR US MARKET" in result["locale_context"]
        assert result["locale_defaulted"] is True

    async def test_market_config_none_uses_fallback_defaults(self) -> None:
        """Falls back to hardcoded defaults when MarketConfig not found."""
        mock_user = MagicMock()
        mock_user.locale_profile = MagicMock(
            primary_market="IN", target_markets=[]
        )

        with (
            patch(
                "src.workflows.graphs.application_assembly.User"
            ) as mock_user_cls,
            patch(
                "src.workflows.graphs.application_assembly._locale_service"
            ) as mock_svc,
        ):
            mock_user_cls.find_one = AsyncMock(return_value=mock_user)
            mock_user_cls.id = "user-123"
            mock_svc.get_market_config = AsyncMock(return_value=None)
            result = await load_locale(_state(), _config())

        assert "FORMAT FOR IN MARKET" in result["locale_context"]
        assert result["locale_defaulted"] is False

    async def test_graph_compiles_with_load_locale(self) -> None:
        """Graph still compiles with the new load_locale node."""
        from langgraph.checkpoint.memory import MemorySaver

        from src.workflows.graphs.application_assembly import (
            build_application_assembly_graph,
        )

        checkpointer = MemorySaver()
        graph = build_application_assembly_graph(checkpointer)
        assert graph is not None
        node_names = set(graph.get_graph().nodes.keys())
        assert "load_locale" in node_names
