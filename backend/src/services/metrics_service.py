"""
LLM usage metrics aggregation service.

Reads from the `llm_usage` MongoDB collection to provide cost summaries,
per-agent breakdowns, and budget enforcement.

Design decisions
----------------
Why a service (not querying LLMUsage directly in routes):
    Aggregation logic belongs in the service layer. Routes stay thin and
    testable; the aggregation queries are isolated and mockable.

Why raw PyMongo aggregation pipelines (not Beanie find_many):
    Beanie's find_many returns full documents, forcing Python-side aggregation.
    MongoDB's $group and $sum run server-side — faster and uses no bandwidth
    for the unused fields. Beanie exposes the underlying collection via
    LLMUsage.get_motor_collection() for raw pipeline access.

Why return dataclasses (not raw dicts):
    Type safety — callers get IDE autocomplete on result fields. Dataclasses
    are also trivially serializable to JSON via dataclasses.asdict().
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from beanie import PydanticObjectId

from src.db.documents.llm_usage import LLMUsage

logger = structlog.get_logger()


@dataclass
class UsageSummary:
    """Aggregated LLM usage for a time window."""

    total_cost_usd: float
    total_tokens: int
    total_calls: int
    window_days: int


@dataclass
class AgentBreakdown:
    """Cost and token usage broken down by agent."""

    agent: str
    cost_usd: float
    total_tokens: int
    call_count: int


@dataclass
class ModelBreakdown:
    """Cost and token usage broken down by model."""

    model: str
    provider: str
    cost_usd: float
    total_tokens: int
    call_count: int


class MetricsService:
    """Aggregates LLM usage metrics from the llm_usage collection."""

    # ---------------------------------------------------------------------------
    # Per-user queries
    # ---------------------------------------------------------------------------

    async def get_user_summary(
        self,
        user_id: PydanticObjectId,
        days: int = 30,
    ) -> UsageSummary:
        """
        Total cost and token usage for a user over the last N days.

        Args:
            user_id: The user's MongoDB ObjectId.
            days: Look-back window in days.

        Returns:
            UsageSummary with totals for the window.
        """
        since = datetime.now(UTC) - timedelta(days=days)
        pipeline = [
            {"$match": {"user_id": user_id, "created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": None,
                    "total_cost_usd": {"$sum": "$cost_usd"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_calls": {"$sum": 1},
                }
            },
        ]
        results = await LLMUsage.aggregate(pipeline).to_list()
        if not results:
            return UsageSummary(
                total_cost_usd=0.0,
                total_tokens=0,
                total_calls=0,
                window_days=days,
            )
        r = results[0]
        return UsageSummary(
            total_cost_usd=round(r["total_cost_usd"], 6),
            total_tokens=r["total_tokens"],
            total_calls=r["total_calls"],
            window_days=days,
        )

    async def get_user_agent_breakdown(
        self,
        user_id: PydanticObjectId,
        days: int = 30,
    ) -> list[AgentBreakdown]:
        """
        Cost and token usage per agent for a user over the last N days.

        Returns a list sorted by cost descending (most expensive agent first).
        """
        since = datetime.now(UTC) - timedelta(days=days)
        pipeline = [
            {"$match": {"user_id": user_id, "created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": "$agent",
                    "cost_usd": {"$sum": "$cost_usd"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "call_count": {"$sum": 1},
                }
            },
            {"$sort": {"cost_usd": -1}},
        ]
        results = await LLMUsage.aggregate(pipeline).to_list()
        return [
            AgentBreakdown(
                agent=r["_id"] or "unknown",
                cost_usd=round(r["cost_usd"], 6),
                total_tokens=r["total_tokens"],
                call_count=r["call_count"],
            )
            for r in results
        ]

    async def is_over_budget(
        self,
        user_id: PydanticObjectId,
        daily_limit_usd: float,
    ) -> bool:
        """
        Check if a user has exceeded their daily LLM spending limit.

        Used by the ModelManager before making LLM calls. Returns False
        on any database error — fail open to avoid blocking users.
        """
        try:
            summary = await self.get_user_summary(user_id, days=1)
            return summary.total_cost_usd >= daily_limit_usd
        except Exception as e:
            logger.warning("budget_check_failed", user_id=str(user_id), error=str(e))
            return False

    # ---------------------------------------------------------------------------
    # System-wide queries (admin / monitoring)
    # ---------------------------------------------------------------------------

    async def get_model_breakdown(self, days: int = 7) -> list[ModelBreakdown]:
        """
        System-wide cost and usage per model over the last N days.

        Useful for identifying which model drives the most cost across all users.
        """
        since = datetime.now(UTC) - timedelta(days=days)
        pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": {"model": "$model", "provider": "$provider"},
                    "cost_usd": {"$sum": "$cost_usd"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "call_count": {"$sum": 1},
                }
            },
            {"$sort": {"cost_usd": -1}},
        ]
        results = await LLMUsage.aggregate(pipeline).to_list()
        return [
            ModelBreakdown(
                model=r["_id"].get("model", "unknown"),
                provider=r["_id"].get("provider", "unknown"),
                cost_usd=round(r["cost_usd"], 6),
                total_tokens=r["total_tokens"],
                call_count=r["call_count"],
            )
            for r in results
        ]
