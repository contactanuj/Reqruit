"""
LLM provider factory — creates LangChain chat model instances from config.

Design decisions
----------------
Why a factory function (not direct construction in ModelManager):
    Isolates LangChain provider imports to this module. The ModelManager
    calls create_chat_model() without knowing which LangChain class to
    import. If a provider package changes its API, only this file changes.

Why create instances on-demand (not cached at startup):
    Different tasks use different model configurations (model name, max_tokens,
    temperature). A cover letter task uses Claude Sonnet with temperature=0.7,
    while data extraction uses GPT-4o-mini with temperature=0.0. Creating
    instances on-demand with task-specific parameters is simpler than
    maintaining a cache of every (model, temperature, max_tokens) combination.

    LangChain model constructors are cheap — they store parameters without
    making API calls. The actual API call happens when you invoke the model.

Why detect_available_providers checks API keys:
    Not every developer has all three API keys configured. A contributor
    working on the frontend only needs Groq (free). Detecting availability
    by key presence lets the ModelManager skip unconfigured providers
    gracefully instead of crashing on startup.

Usage
-----
    from src.llm.providers import create_chat_model, detect_available_providers

    available = detect_available_providers(settings)
    model = create_chat_model(ProviderName.ANTHROPIC, "claude-sonnet-4-5-20250929",
                              max_tokens=2048, temperature=0.7, settings=settings)
"""

import structlog
from langchain_core.language_models import BaseChatModel

from src.core.config import Settings
from src.llm.models import ProviderName

logger = structlog.get_logger()


def detect_available_providers(settings: Settings) -> set[ProviderName]:
    """
    Return the set of providers that have API keys configured.

    Checks each provider's API key in settings. If the key is a non-empty
    string, the provider is considered available. Logs a warning for each
    missing key so developers know which providers are skipped.
    """
    available: set[ProviderName] = set()
    provider_keys = {
        ProviderName.ANTHROPIC: settings.anthropic.api_key,
        ProviderName.OPENAI: settings.openai.api_key,
        ProviderName.GROQ: settings.groq.api_key,
    }

    for provider, key in provider_keys.items():
        if key:
            available.add(provider)
        else:
            logger.warning("provider_api_key_missing", provider=provider.value)

    return available


def create_chat_model(
    provider: ProviderName,
    model_name: str,
    *,
    max_tokens: int,
    temperature: float,
    settings: Settings,
) -> BaseChatModel:
    """
    Create a LangChain chat model instance for the given provider and config.

    Returns a BaseChatModel that can be used with .invoke(), .ainvoke(),
    .stream(), .bind_tools(), and .with_structured_output() — all standard
    LangChain APIs that LangGraph agents depend on.

    Args:
        provider: Which LLM provider to use.
        model_name: Provider-specific model identifier.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
        settings: Application settings containing API keys.

    Raises:
        ValueError: If the provider is not recognized.
    """
    if provider == ProviderName.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=settings.anthropic.api_key,
        )

    if provider == ProviderName.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=settings.openai.api_key,
        )

    if provider == ProviderName.GROQ:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=settings.groq.api_key,
        )

    msg = f"Unknown provider: {provider}"
    raise ValueError(msg)
