"""
LLM Provider Layer — model routing, cost tracking, circuit breaker, fallback logic.

Public API:
    Lifecycle:
        init_model_manager(settings)   — call during app startup
        close_model_manager()          — call during app shutdown
        get_model_manager()            — get the active ModelManager

    Types:
        TaskType      — what the LLM call is for (determines model selection)
        ProviderName  — which provider (anthropic, openai, groq)

    Callbacks:
        CostTrackingCallback — attach to LLM calls for automatic usage recording
"""

from src.llm.cost_tracker import CostTrackingCallback
from src.llm.manager import close_model_manager, get_model_manager, init_model_manager
from src.llm.models import ProviderName, TaskType

__all__ = [
    "CostTrackingCallback",
    "ProviderName",
    "TaskType",
    "close_model_manager",
    "get_model_manager",
    "init_model_manager",
]
