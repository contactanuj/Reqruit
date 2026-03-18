"""Structured logging helpers for LLM calls within Celery tasks."""

import structlog

logger = structlog.get_logger()


def log_llm_call(
    *,
    model: str,
    token_count: int,
    latency_ms: float,
    cost_estimate: float,
    user_id: str,
    feature_category: str,
    task_id: str,
) -> None:
    """
    Emit a structured log entry for an LLM call made within a Celery task.

    Task implementations should call this after each LLM invocation,
    passing metrics from the CostTrackingCallback. The log entry can be
    ingested by log aggregation systems (ELK, Datadog) for cost dashboards.
    """
    logger.info(
        "llm_call_in_task",
        model=model,
        token_count=token_count,
        latency_ms=latency_ms,
        cost_estimate=cost_estimate,
        user_id=user_id,
        feature_category=feature_category,
        task_id=task_id,
    )


def extract_cost_from_callback(
    *,
    total_tokens: int,
    total_cost_usd: float,
    model: str,
    latency_ms: float,
    user_id: str,
    feature_category: str,
    task_id: str,
) -> dict:
    """
    Extract cost fields from callback data, log the call, and return a dict.

    Returns a dict with ``llm_tokens_used`` and ``llm_cost_usd`` keys
    suitable for inclusion in a task's return value so BaseTask.on_success
    can persist them to the TaskRecord.
    """
    log_llm_call(
        model=model,
        token_count=total_tokens,
        latency_ms=latency_ms,
        cost_estimate=total_cost_usd,
        user_id=user_id,
        feature_category=feature_category,
        task_id=task_id,
    )
    return {
        "llm_tokens_used": total_tokens,
        "llm_cost_usd": total_cost_usd,
    }
