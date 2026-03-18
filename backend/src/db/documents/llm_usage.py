"""
LLM usage tracking document model — cost and performance monitoring.

Every LLM API call is logged as an LLMUsage record. This provides:
- Cost tracking per user, agent, and model
- Latency monitoring for performance optimization
- Token consumption for budget enforcement
- Agent activity metrics for evaluation

Design decisions
----------------
Why a dedicated collection (not application logs):
    LLM costs can spiral quickly. A dedicated collection with structured
    fields enables real-time budget queries ("how much has this user spent
    today?") and aggregation pipelines for dashboards. Generic log files
    would require parsing and are harder to query.

Why store both input_tokens and output_tokens (not just total):
    LLM providers charge differently for input vs output tokens. Storing
    them separately enables accurate cost calculation when pricing changes,
    and helps identify whether cost is driven by large prompts (input) or
    verbose responses (output).

Why cost_usd is pre-calculated:
    Storing the cost at write time (using the current pricing) avoids
    retrospective recalculation when pricing changes. The cost at the time
    of the call is what we actually paid.

Why compound index on (agent, model):
    Common dashboard queries include "cost breakdown by agent" and "which
    model is used most." The compound index supports both patterns.
"""

from beanie import Indexed, PydanticObjectId
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class LLMUsage(TimestampedDocument):
    """
    Single LLM API call usage record.

    Fields:
        user_id: The user whose action triggered this LLM call.
        agent: Which agent made the call (e.g., "cover_letter_writer").
        model: Model identifier (e.g., "claude-sonnet-4-20250514").
        provider: Provider name (e.g., "anthropic", "openai", "groq").
        task_type: What the call was for (e.g., "cover_letter", "matching").
        input_tokens: Number of tokens in the prompt.
        output_tokens: Number of tokens in the response.
        total_tokens: input_tokens + output_tokens (denormalized for queries).
        cost_usd: Pre-calculated cost in USD at the time of the call.
        latency_ms: Round-trip time in milliseconds.
    """

    user_id: Indexed(PydanticObjectId)
    agent: str = ""
    model: str = ""
    provider: str = ""
    task_type: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0

    class Settings:
        name = "llm_usage"
        indexes = [
            IndexModel(
                [("agent", ASCENDING), ("model", ASCENDING)],
                name="agent_model_idx",
            ),
        ]
