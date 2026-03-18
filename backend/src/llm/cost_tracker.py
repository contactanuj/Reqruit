"""
LLM cost tracking — automatic usage recording via LangChain callbacks.

Every LLM call generates a usage record in the llm_usage MongoDB collection.
This module provides two components:
1. calculate_cost() — pure function that converts token counts to USD.
2. CostTrackingCallback — LangChain AsyncCallbackHandler that records usage
   automatically when attached to an LLM call.

Design decisions
----------------
Why a LangChain callback (not manual logging after each call):
    LangGraph agents call LLMs through complex workflows with branching,
    retries, and streaming. Manually inserting a usage record after each
    .ainvoke() or .astream() call is error-prone — easy to miss a call site,
    especially in LangGraph subgraphs.

    LangChain's callback system hooks into every LLM call automatically.
    Attach the callback once, and it logs usage for invoke, stream, batch,
    and LangGraph node calls — zero changes to agent code.

Why AsyncCallbackHandler (not BaseCallbackHandler):
    Our entire stack is async. AsyncCallbackHandler.on_llm_end is a coroutine,
    so we can await Beanie's .insert() directly. The synchronous
    BaseCallbackHandler would require spawning a task or using sync DB calls.

Why extract model name from LLM response (not passed at construction):
    The CostTrackingCallback is created before the LLM call, but the actual
    model resolved by the provider (which may differ from the requested model
    due to aliases or defaults) is only known after the call completes.
    Extracting the model name from llm_output in on_llm_end ensures accuracy.

Why silent failure on tracking errors:
    Cost tracking is observability — it should never block an LLM response.
    If the database is temporarily unavailable or the response format is
    unexpected, we log a warning and continue. The LLM result is still
    returned to the user.

Usage
-----
Standalone cost calculation:
    cost = calculate_cost("claude-sonnet-4-5-20250929", input_tokens=500, output_tokens=200)

Automatic tracking in an LLM call:
    callback = CostTrackingCallback(user_id=user_id, agent="cover_letter_writer",
                                    task_type="cover_letter")
    result = await model.ainvoke(messages, config={"callbacks": [callback]})
"""

import time
from typing import Any

import structlog
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from src.core.config import get_settings
from src.db.documents.usage_ledger import UsageTier
from src.llm.models import COST_PER_MILLION_TOKENS, ProviderName

logger = structlog.get_logger()


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the USD cost for an LLM call.

    Looks up the model's per-million-token pricing and applies it to the
    actual token counts. Returns 0.0 for unknown models — this is a safe
    fallback that avoids crashing on new models before the cost table is
    updated.

    Args:
        model: Model identifier (e.g., "claude-sonnet-4-5-20250929").
        input_tokens: Number of tokens in the prompt.
        output_tokens: Number of tokens in the response.

    Returns:
        Cost in USD, rounded to 6 decimal places.
    """
    rates = COST_PER_MILLION_TOKENS.get(model)
    if rates is None:
        logger.debug("cost_unknown_model", model=model)
        return 0.0

    input_rate, output_rate = rates
    cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    return round(cost, 6)


def _extract_token_usage(llm_output: dict[str, Any]) -> tuple[int, int]:
    """
    Extract input and output token counts from provider-specific LLM output.

    Different providers format token usage differently in LLMResult.llm_output:
    - Anthropic: {"usage": {"input_tokens": X, "output_tokens": Y}}
    - OpenAI/Groq: {"token_usage": {"prompt_tokens": X, "completion_tokens": Y}}

    Returns (0, 0) if token usage is not found — some edge cases (e.g.,
    streaming with certain providers) may not include usage data.
    """
    # Anthropic format
    usage = llm_output.get("usage", {})
    if "input_tokens" in usage:
        return usage["input_tokens"], usage["output_tokens"]

    # OpenAI / Groq format
    token_usage = llm_output.get("token_usage", {})
    if "prompt_tokens" in token_usage:
        return token_usage["prompt_tokens"], token_usage["completion_tokens"]

    return 0, 0


def _extract_model_name(llm_output: dict[str, Any]) -> str:
    """
    Extract the model name from provider-specific LLM output.

    - Anthropic: {"model": "claude-..."}
    - OpenAI/Groq: {"model_name": "gpt-..."}

    Returns "unknown" if the model name is not found.
    """
    return llm_output.get("model") or llm_output.get("model_name", "unknown")


def _infer_provider(model_name: str) -> str:
    """
    Infer the provider from a model name prefix.

    This is a best-effort mapping used for the provider field in LLMUsage
    records. Falls back to "unknown" for unrecognized prefixes.
    """
    if model_name.startswith("claude"):
        return ProviderName.ANTHROPIC
    if model_name.startswith("gpt"):
        return ProviderName.OPENAI
    if model_name.startswith("llama"):
        return ProviderName.GROQ
    return "unknown"


class CostTrackingCallback(AsyncCallbackHandler):
    """
    LangChain callback that records LLM usage to MongoDB automatically.

    Hooks into on_llm_end (called after every LLM response) to extract token
    counts, calculate cost, and insert an LLMUsage document. Also tracks
    latency by recording the start time in on_llm_start / on_chat_model_start.

    Attributes:
        user_id: The user whose action triggered this LLM call.
        agent: Which agent made the call (e.g., "cover_letter_writer").
        task_type: What the call was for (e.g., "cover_letter").
    """

    def __init__(
        self,
        user_id: str,
        agent: str,
        task_type: str,
        tier: UsageTier = UsageTier.FREE,
    ) -> None:
        super().__init__()
        self.user_id = user_id
        self.agent = agent
        self.task_type = task_type
        self.tier = tier
        self._start_time: float | None = None

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Record the start time for latency measurement."""
        self._start_time = time.monotonic()

    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        **kwargs: Any,
    ) -> None:
        """Record the start time for chat model calls (more specific hook)."""
        self._start_time = time.monotonic()

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Extract usage data from the LLM response and persist it.

        This is called after every LLM call completes (both streaming and
        non-streaming). It extracts token counts and model name from the
        provider-specific llm_output dict, calculates cost, and inserts
        an LLMUsage record.

        Wrapped in try/except because cost tracking must never break an
        LLM response. If the database is unavailable or the response format
        is unexpected, we log a warning and continue.
        """
        try:
            llm_output = response.llm_output or {}

            model_name = _extract_model_name(llm_output)
            input_tokens, output_tokens = _extract_token_usage(llm_output)
            cost = calculate_cost(model_name, input_tokens, output_tokens)
            provider = _infer_provider(model_name)

            # Calculate latency if we captured the start time.
            latency_ms = 0
            if self._start_time is not None:
                latency_ms = int((time.monotonic() - self._start_time) * 1000)

            # Lazy import to avoid circular dependency — LLMUsage is a Beanie
            # Document defined in the db layer, which this llm module should
            # not import at module level.
            from src.db.documents.llm_usage import LLMUsage

            usage = LLMUsage(
                user_id=self.user_id,
                agent=self.agent,
                model=model_name,
                provider=provider,
                task_type=self.task_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            )
            await usage.insert()

            logger.debug(
                "llm_usage_recorded",
                model=model_name,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            )

            # Update the per-user UsageLedger for real-time cost attribution.
            try:
                from src.repositories.usage_ledger_repository import (
                    UsageLedgerRepository,
                )

                ledger_repo = UsageLedgerRepository()
                settings = get_settings()
                await ledger_repo.increment_usage(
                    user_id=self.user_id,
                    tokens=input_tokens + output_tokens,
                    cost_usd=cost,
                    feature=self.task_type,
                    model_name=model_name,
                    tier=self.tier,
                    tier_settings=settings.tier,
                )
            except Exception:
                logger.warning("usage_ledger_update_failed", exc_info=True)

        except Exception:
            # Cost tracking is observability — never block the LLM response.
            logger.warning("cost_tracking_failed", exc_info=True)
