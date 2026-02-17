"""
Tests for the ModelManager and module-level lifecycle functions.

These tests mock the provider factory and circuit breaker to verify
routing logic in isolation — no real LLM API calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import LLMProviderError
from src.llm.circuit_breaker import CircuitBreaker
from src.llm.cost_tracker import CostTrackingCallback
from src.llm.manager import (
    ModelManager,
    close_model_manager,
    get_model_manager,
    init_model_manager,
)
from src.llm.models import ProviderName, TaskType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_settings():
    """Minimal mock settings with all API keys present."""
    settings = MagicMock()
    settings.anthropic.api_key = "test-anthropic-key"
    settings.openai.api_key = "test-openai-key"
    settings.groq.api_key = "test-groq-key"
    return settings


@pytest.fixture
def all_providers() -> set[ProviderName]:
    return {ProviderName.ANTHROPIC, ProviderName.OPENAI, ProviderName.GROQ}


@pytest.fixture
def circuit_breaker():
    return CircuitBreaker()


@pytest.fixture
def manager(mock_settings, all_providers, circuit_breaker):
    return ModelManager(
        settings=mock_settings,
        available_providers=all_providers,
        circuit_breaker=circuit_breaker,
    )


# ---------------------------------------------------------------------------
# ModelManager.get_model tests
# ---------------------------------------------------------------------------


class TestGetModel:
    """Test model selection and fallback routing."""

    def test_returns_model_for_primary_provider(self, manager):
        """Primary provider (first in routing table) is selected."""
        with patch(
            "src.llm.manager.create_chat_model"
        ) as mock_create:
            mock_model = MagicMock()
            mock_create.return_value = mock_model

            result = manager.get_model(TaskType.COVER_LETTER)

            assert result is mock_model
            # Cover letter primary is Anthropic (Claude Sonnet).
            call_kwargs = mock_create.call_args
            assert call_kwargs.kwargs["provider"] == ProviderName.ANTHROPIC

    def test_falls_back_when_primary_circuit_open(self, manager):
        """When the primary provider is unhealthy, use the fallback."""
        # Open Anthropic's circuit.
        manager._circuit_breaker.record_failure(ProviderName.ANTHROPIC)
        manager._circuit_breaker.record_failure(ProviderName.ANTHROPIC)
        manager._circuit_breaker.record_failure(ProviderName.ANTHROPIC)

        with patch(
            "src.llm.manager.create_chat_model"
        ) as mock_create:
            mock_model = MagicMock()
            mock_create.return_value = mock_model

            result = manager.get_model(TaskType.COVER_LETTER)

            assert result is mock_model
            # Fallback for cover letter is Groq.
            call_kwargs = mock_create.call_args
            assert call_kwargs.kwargs["provider"] == ProviderName.GROQ

    def test_skips_provider_with_missing_api_key(self, mock_settings, circuit_breaker):
        """Providers without API keys are skipped."""
        # Only Groq available.
        manager = ModelManager(
            settings=mock_settings,
            available_providers={ProviderName.GROQ},
            circuit_breaker=circuit_breaker,
        )

        with patch(
            "src.llm.manager.create_chat_model"
        ) as mock_create:
            mock_model = MagicMock()
            mock_create.return_value = mock_model

            result = manager.get_model(TaskType.COVER_LETTER)

            assert result is mock_model
            call_kwargs = mock_create.call_args
            assert call_kwargs.kwargs["provider"] == ProviderName.GROQ

    def test_raises_when_all_providers_unavailable(
        self, mock_settings, circuit_breaker
    ):
        """LLMProviderError when no provider can serve the task."""
        manager = ModelManager(
            settings=mock_settings,
            available_providers=set(),  # No providers at all.
            circuit_breaker=circuit_breaker,
        )

        with pytest.raises(LLMProviderError, match="All providers unavailable"):
            manager.get_model(TaskType.COVER_LETTER)

    def test_raises_with_correct_error_code(
        self, mock_settings, circuit_breaker
    ):
        manager = ModelManager(
            settings=mock_settings,
            available_providers=set(),
            circuit_breaker=circuit_breaker,
        )

        with pytest.raises(LLMProviderError) as exc_info:
            manager.get_model(TaskType.GENERAL)
        assert exc_info.value.error_code == "LLM_ALL_PROVIDERS_UNAVAILABLE"


class TestGetModelWithConfig:
    """Test get_model_with_config returns both model and config."""

    def test_returns_model_and_config_tuple(self, manager):
        with patch(
            "src.llm.manager.create_chat_model"
        ) as mock_create:
            mock_model = MagicMock()
            mock_create.return_value = mock_model

            model, config = manager.get_model_with_config(TaskType.DATA_EXTRACTION)

            assert model is mock_model
            assert config.provider == ProviderName.OPENAI
            assert config.temperature == 0.0

    def test_raises_when_all_unavailable(self, mock_settings, circuit_breaker):
        manager = ModelManager(
            settings=mock_settings,
            available_providers=set(),
            circuit_breaker=circuit_breaker,
        )
        with pytest.raises(LLMProviderError):
            manager.get_model_with_config(TaskType.QUICK_CHAT)


# ---------------------------------------------------------------------------
# Convenience methods
# ---------------------------------------------------------------------------


class TestConvenienceMethods:
    """Test cost callback creation and circuit breaker delegation."""

    def test_create_cost_callback(self, manager):
        callback = manager.create_cost_callback(
            user_id="user1",
            agent="test_agent",
            task_type="cover_letter",
        )
        assert isinstance(callback, CostTrackingCallback)
        assert callback.user_id == "user1"
        assert callback.agent == "test_agent"
        assert callback.task_type == "cover_letter"

    def test_record_success_delegates_to_circuit_breaker(self, manager):
        # Should not raise — just verifying delegation.
        manager.record_success(ProviderName.ANTHROPIC)

    def test_record_failure_delegates_to_circuit_breaker(self, manager):
        manager.record_failure(ProviderName.ANTHROPIC)
        status = manager.get_circuit_status()
        # One failure is not enough to open (threshold=3 by default).
        assert status["anthropic"] == "closed"

    def test_available_providers_property(self, manager, all_providers):
        assert manager.available_providers == all_providers

    def test_get_circuit_status(self, manager):
        # Access a provider to create its circuit entry.
        manager._circuit_breaker.is_available(ProviderName.ANTHROPIC)
        status = manager.get_circuit_status()
        assert "anthropic" in status


# ---------------------------------------------------------------------------
# Module-level lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Test init_model_manager, close_model_manager, get_model_manager."""

    def setup_method(self):
        """Ensure clean state before each test."""
        # Import and reset the module-level _manager.
        import src.llm.manager as mgr_module
        self._original = mgr_module._manager
        mgr_module._manager = None

    def teardown_method(self):
        """Restore original state after each test."""
        import src.llm.manager as mgr_module
        mgr_module._manager = self._original

    def test_get_manager_raises_before_init(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            get_model_manager()

    def test_init_creates_manager(self, mock_settings):
        with patch(
            "src.llm.manager.detect_available_providers",
            return_value={ProviderName.GROQ},
        ):
            init_model_manager(mock_settings)

        manager = get_model_manager()
        assert isinstance(manager, ModelManager)
        assert ProviderName.GROQ in manager.available_providers

    def test_close_clears_manager(self, mock_settings):
        with patch(
            "src.llm.manager.detect_available_providers",
            return_value=set(),
        ):
            init_model_manager(mock_settings)

        close_model_manager()

        with pytest.raises(RuntimeError, match="not initialized"):
            get_model_manager()

    def test_init_close_init_works(self, mock_settings):
        """Verify re-initialization after close works correctly."""
        with patch(
            "src.llm.manager.detect_available_providers",
            return_value={ProviderName.ANTHROPIC},
        ):
            init_model_manager(mock_settings)
            close_model_manager()
            init_model_manager(mock_settings)

        manager = get_model_manager()
        assert ProviderName.ANTHROPIC in manager.available_providers
