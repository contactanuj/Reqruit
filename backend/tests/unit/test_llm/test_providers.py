"""
Tests for the provider factory functions.

These tests verify that:
- Available providers are detected correctly from API key presence
- The factory creates the right LangChain class for each provider
- Missing API keys are handled gracefully with warnings
"""

from unittest.mock import MagicMock, patch

import pytest

from src.llm.models import ProviderName
from src.llm.providers import create_chat_model, detect_available_providers

# ---------------------------------------------------------------------------
# detect_available_providers
# ---------------------------------------------------------------------------


class TestDetectAvailableProviders:
    """Test provider availability detection from API key configuration."""

    def _make_settings(
        self,
        anthropic_key: str = "",
        openai_key: str = "",
        groq_key: str = "",
    ) -> MagicMock:
        settings = MagicMock()
        settings.anthropic.api_key = anthropic_key
        settings.openai.api_key = openai_key
        settings.groq.api_key = groq_key
        return settings

    def test_all_keys_present(self):
        settings = self._make_settings(
            anthropic_key="sk-ant-xxx",
            openai_key="sk-xxx",
            groq_key="gsk-xxx",
        )
        available = detect_available_providers(settings)
        assert available == {
            ProviderName.ANTHROPIC,
            ProviderName.OPENAI,
            ProviderName.GROQ,
        }

    def test_no_keys_present(self):
        settings = self._make_settings()
        available = detect_available_providers(settings)
        assert available == set()

    def test_partial_keys(self):
        """Only Groq has a key — common for free-tier-only development."""
        settings = self._make_settings(groq_key="gsk-xxx")
        available = detect_available_providers(settings)
        assert available == {ProviderName.GROQ}

    def test_empty_string_key_is_not_available(self):
        """An empty string API key means the provider is not configured."""
        settings = self._make_settings(anthropic_key="")
        available = detect_available_providers(settings)
        assert ProviderName.ANTHROPIC not in available


# ---------------------------------------------------------------------------
# create_chat_model
# ---------------------------------------------------------------------------


class TestCreateChatModel:
    """Test model instance creation for each provider."""

    @pytest.fixture
    def settings(self):
        s = MagicMock()
        s.anthropic.api_key = "test-key"
        s.openai.api_key = "test-key"
        s.groq.api_key = "test-key"
        return s

    def test_creates_anthropic_model(self, settings):
        with patch("langchain_anthropic.ChatAnthropic") as mock_chat_cls:
            mock_model = MagicMock()
            mock_chat_cls.return_value = mock_model

            result = create_chat_model(
                ProviderName.ANTHROPIC,
                "claude-sonnet-4-5-20250929",
                max_tokens=2048,
                temperature=0.7,
                settings=settings,
            )

            assert result is mock_model
            mock_chat_cls.assert_called_once_with(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                temperature=0.7,
                api_key="test-key",
            )

    def test_creates_openai_model(self, settings):
        with patch("langchain_openai.ChatOpenAI") as mock_chat_cls:
            mock_model = MagicMock()
            mock_chat_cls.return_value = mock_model

            result = create_chat_model(
                ProviderName.OPENAI,
                "gpt-4o-mini",
                max_tokens=1024,
                temperature=0.0,
                settings=settings,
            )

            assert result is mock_model
            mock_chat_cls.assert_called_once_with(
                model="gpt-4o-mini",
                max_tokens=1024,
                temperature=0.0,
                api_key="test-key",
            )

    def test_creates_groq_model(self, settings):
        with patch("langchain_groq.ChatGroq") as mock_chat_cls:
            mock_model = MagicMock()
            mock_chat_cls.return_value = mock_model

            result = create_chat_model(
                ProviderName.GROQ,
                "llama-3.3-70b-versatile",
                max_tokens=4096,
                temperature=0.3,
                settings=settings,
            )

            assert result is mock_model
            mock_chat_cls.assert_called_once_with(
                model="llama-3.3-70b-versatile",
                max_tokens=4096,
                temperature=0.3,
                api_key="test-key",
            )

    def test_unknown_provider_raises_value_error(self, settings):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_chat_model(
                "not_a_provider",
                "some-model",
                max_tokens=512,
                temperature=0.5,
                settings=settings,
            )
