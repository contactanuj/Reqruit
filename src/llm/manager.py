"""
ModelManager — the central orchestrator for LLM provider routing and lifecycle.

This module provides two things:
1. The ModelManager class — routes tasks to the right model, manages the
   circuit breaker, and creates cost tracking callbacks.
2. Module-level lifecycle functions — init, close, get — matching the pattern
   established by mongodb.py and weaviate_client.py.

Design decisions
----------------
Why get_model() returns BaseChatModel (not a wrapper):
    LangGraph agents need to call .bind_tools(), .with_structured_output(),
    and pass models directly to graph nodes. These are LangChain APIs that
    operate on BaseChatModel. Wrapping the model in a custom class would
    break these integrations or require proxying every method.

    Cost tracking and circuit breaker logic are handled outside the model:
    - Cost: via CostTrackingCallback (passed as a callback to .ainvoke())
    - Circuit breaker: via record_success/record_failure (called by the agent
      after each LLM call)

    This keeps the model object "pure LangChain" while the ModelManager
    handles our custom concerns.

Why create models on-demand (not pre-cached):
    Different tasks use different configurations — cover letters need
    temperature=0.7, data extraction needs temperature=0.0. Since the same
    provider serves multiple tasks with different configs, we create model
    instances per-request with the right parameters.

    LangChain model constructors are cheap (no I/O, just store params).
    Caching by (provider, model_name, max_tokens, temperature) is possible
    but adds complexity without measurable benefit at our scale.

Why module-level lifecycle (not a class singleton):
    Matches the pattern in mongodb.py and weaviate_client.py:
    - _manager variable holds the instance
    - init_model_manager() creates it
    - close_model_manager() clears it
    - get_model_manager() returns it or raises RuntimeError

    FastAPI's lifespan calls init on startup and close on shutdown.
    This pattern is simple, testable, and consistent across the codebase.

Usage
-----
In the FastAPI lifespan (src/api/main.py):
    from src.llm.manager import init_model_manager, close_model_manager

    async def lifespan(app):
        init_model_manager(settings)
        yield
        close_model_manager()

In an agent:
    from src.llm.manager import get_model_manager
    from src.llm.models import TaskType

    manager = get_model_manager()
    model = manager.get_model(TaskType.COVER_LETTER)
    callback = manager.create_cost_callback(user_id, "cover_letter_writer",
                                            TaskType.COVER_LETTER)
    result = await model.ainvoke(messages, config={"callbacks": [callback]})
    manager.record_success(ProviderName.ANTHROPIC)
"""

import structlog
from langchain_core.language_models import BaseChatModel

from src.core.config import Settings
from src.core.exceptions import LLMProviderError
from src.llm.circuit_breaker import CircuitBreaker
from src.llm.cost_tracker import CostTrackingCallback
from src.llm.models import ROUTING_TABLE, ModelConfig, ProviderName, TaskType
from src.llm.providers import create_chat_model, detect_available_providers

logger = structlog.get_logger()


class ModelManager:
    """
    Routes tasks to LLM models with fallback and circuit breaking.

    The manager holds the application settings, a set of available providers
    (those with API keys configured), and a circuit breaker. When asked for
    a model, it walks the routing table for the requested task type, skipping
    unavailable or unhealthy providers, and returns the first viable model.

    Attributes:
        _settings: Application settings (contains API keys for all providers).
        _available_providers: Providers with valid API keys configured.
        _circuit_breaker: Per-provider health tracking.
    """

    def __init__(
        self,
        settings: Settings,
        available_providers: set[ProviderName],
        circuit_breaker: CircuitBreaker,
    ) -> None:
        self._settings = settings
        self._available_providers = available_providers
        self._circuit_breaker = circuit_breaker

    def get_model(self, task_type: TaskType) -> BaseChatModel:
        """
        Get a configured LLM for the given task type.

        Walks the routing table in priority order (primary model first,
        then fallbacks). Skips providers that are:
        - Not configured (missing API key)
        - Unhealthy (circuit breaker is open)

        Returns the first available model, configured with the task's
        max_tokens and temperature.

        Args:
            task_type: What the LLM call is for — determines model selection.

        Returns:
            A BaseChatModel instance ready for .ainvoke() or .astream().

        Raises:
            LLMProviderError: If no provider is available for this task.
        """
        configs = ROUTING_TABLE.get(task_type, [])
        if not configs:
            raise LLMProviderError(
                detail=f"No routing configuration for task type: {task_type}",
                provider="none",
                error_code="LLM_NO_ROUTE",
            )

        for config in configs:
            if config.provider not in self._available_providers:
                logger.debug(
                    "provider_skipped_no_key",
                    provider=config.provider.value,
                    task_type=task_type.value,
                )
                continue

            if not self._circuit_breaker.is_available(config.provider):
                logger.debug(
                    "provider_skipped_circuit_open",
                    provider=config.provider.value,
                    task_type=task_type.value,
                )
                continue

            return self._create_model(config)

        # All providers exhausted — no model available for this task.
        raise LLMProviderError(
            detail=(
                f"All providers unavailable for task '{task_type}'. "
                f"Configured providers: "
                f"{[c.provider.value for c in configs]}"
            ),
            provider="all",
            error_code="LLM_ALL_PROVIDERS_UNAVAILABLE",
        )

    def get_model_with_config(
        self, task_type: TaskType
    ) -> tuple[BaseChatModel, ModelConfig]:
        """
        Get a configured LLM and its ModelConfig for the given task type.

        Same routing logic as get_model(), but also returns the resolved
        ModelConfig. Useful when the caller needs to know which model was
        selected (e.g., for logging or passing to record_success/failure).

        Returns:
            A tuple of (model, config).

        Raises:
            LLMProviderError: If no provider is available for this task.
        """
        configs = ROUTING_TABLE.get(task_type, [])
        if not configs:
            raise LLMProviderError(
                detail=f"No routing configuration for task type: {task_type}",
                provider="none",
                error_code="LLM_NO_ROUTE",
            )

        for config in configs:
            if config.provider not in self._available_providers:
                continue
            if not self._circuit_breaker.is_available(config.provider):
                continue
            return self._create_model(config), config

        raise LLMProviderError(
            detail=(
                f"All providers unavailable for task '{task_type}'. "
                f"Configured providers: "
                f"{[c.provider.value for c in configs]}"
            ),
            provider="all",
            error_code="LLM_ALL_PROVIDERS_UNAVAILABLE",
        )

    def create_cost_callback(
        self, user_id: str, agent: str, task_type: str
    ) -> CostTrackingCallback:
        """
        Create a cost tracking callback with the given context.

        The returned callback should be passed to the LLM call via the
        callbacks config parameter. It automatically records usage to
        MongoDB when the LLM call completes.

        Args:
            user_id: The user whose action triggered this call.
            agent: Which agent is making the call.
            task_type: What the call is for.
        """
        return CostTrackingCallback(
            user_id=user_id,
            agent=agent,
            task_type=task_type,
        )

    def record_success(self, provider: ProviderName) -> None:
        """Record a successful LLM call for circuit breaker tracking."""
        self._circuit_breaker.record_success(provider)

    def record_failure(self, provider: ProviderName) -> None:
        """Record a failed LLM call for circuit breaker tracking."""
        self._circuit_breaker.record_failure(provider)

    def get_circuit_status(self) -> dict[str, str]:
        """Return circuit breaker status for all providers (for health checks)."""
        return self._circuit_breaker.get_status()

    @property
    def available_providers(self) -> set[ProviderName]:
        """Return the set of providers with valid API keys."""
        return self._available_providers

    def _create_model(self, config: ModelConfig) -> BaseChatModel:
        """Create a LangChain model instance from a routing table config."""
        return create_chat_model(
            provider=config.provider,
            model_name=config.model_name,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            settings=self._settings,
        )


# ---------------------------------------------------------------------------
# Module-level lifecycle (matches mongodb.py / weaviate_client.py)
# ---------------------------------------------------------------------------

_manager: ModelManager | None = None


def init_model_manager(settings: Settings) -> None:
    """
    Initialize the global ModelManager.

    Called during FastAPI lifespan startup, after MongoDB is connected
    (the cost tracking callback needs Beanie for .insert()).

    Detects available providers from API key configuration, creates
    the circuit breaker, and stores the manager instance.

    Args:
        settings: Application settings containing API keys.
    """
    global _manager

    available = detect_available_providers(settings)
    circuit_breaker = CircuitBreaker()

    _manager = ModelManager(
        settings=settings,
        available_providers=available,
        circuit_breaker=circuit_breaker,
    )

    logger.info(
        "model_manager_initialized",
        available_providers=sorted(p.value for p in available),
        provider_count=len(available),
    )


def close_model_manager() -> None:
    """
    Clear the global ModelManager.

    Called during FastAPI lifespan shutdown. LangChain model instances
    do not hold persistent connections, so there is nothing to close —
    we just clear the reference.
    """
    global _manager
    _manager = None
    logger.info("model_manager_closed")


def get_model_manager() -> ModelManager:
    """
    Return the active ModelManager instance.

    Raises:
        RuntimeError: If called before init_model_manager().
    """
    if _manager is None:
        msg = "ModelManager not initialized. Call init_model_manager() first."
        raise RuntimeError(msg)
    return _manager
