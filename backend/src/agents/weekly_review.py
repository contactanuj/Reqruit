"""
WeeklyReviewAgent — LLM-powered weekly job search strategy review.

Uses Claude Sonnet (temp=0.7) to generate analytical weekly reviews with
metrics comparison, tactical adjustments, and next-week goals.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

logger = structlog.get_logger()

WEEKLY_REVIEW_PROMPT = """\
You are a career strategy coach reviewing a job seeker's weekly activity. \
Produce a structured weekly review with honest, actionable feedback.

Your review must include:
1. This week's metrics summary
2. Comparison to last week (improvements and declines)
3. Tactical adjustments based on what's working and what isn't
4. Exactly 3 specific, actionable goals for next week

If an inflection warning is provided (significant drop in conversion rates), \
incorporate specific pivot suggestions into your tactical adjustments.

If data_driven is false (fewer than 5 applications), provide encouragement \
and generic best practices rather than data-driven insights. Be empathetic — \
job searching is emotionally draining.

Return a JSON object with these exact keys:
{
  "summary": "<1-2 sentence overview>",
  "tactical_adjustments": ["<adjustment 1>", "<adjustment 2>", ...],
  "next_week_goals": ["<goal 1>", "<goal 2>", "<goal 3>"],
  "encouragement": "<motivational message>"
}

Be direct, specific, and actionable. Use actual numbers from the data.\
"""


class WeeklyReviewAgent(BaseAgent):
    """LLM-powered weekly strategy review for job seekers."""

    def __init__(self) -> None:
        super().__init__(
            name="weekly_review",
            task_type=TaskType.WEEKLY_REVIEW,
            system_prompt=WEEKLY_REVIEW_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = []

        metrics = state.get("current_metrics")
        if metrics:
            parts.append(f"This week's metrics: {json.dumps(metrics)}")

        prev_metrics = state.get("previous_metrics")
        if prev_metrics:
            parts.append(f"Last week's metrics: {json.dumps(prev_metrics)}")

        inflection = state.get("inflection_warning")
        if inflection:
            parts.append(f"INFLECTION WARNING: {inflection}")

        data_driven = state.get("data_driven", True)
        if not data_driven:
            parts.append("NOTE: Insufficient data this week (fewer than 5 applications). Provide encouragement and generic best practices.")

        if not parts:
            parts.append("No activity data available. Provide generic job search encouragement.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        # Strip markdown fences if present
        if "```json" in content:
            content = content.split("```json", 1)[1]
            if "```" in content:
                content = content.split("```", 1)[0]
        elif "```" in content:
            content = content.split("```", 1)[1]
            if "```" in content:
                content = content.split("```", 1)[0]

        try:
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict):
                return {
                    "summary": parsed.get("summary", ""),
                    "tactical_adjustments": parsed.get("tactical_adjustments", []),
                    "next_week_goals": parsed.get("next_week_goals", [])[:3],
                    "encouragement": parsed.get("encouragement", ""),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Fallback: return raw content as summary
        logger.warning("weekly_review_parse_failed", raw_length=len(response.content))
        return {
            "summary": response.content[:500],
            "tactical_adjustments": [],
            "next_week_goals": ["Submit 5 applications", "Network with 2 contacts", "Practice 1 mock interview"],
            "encouragement": "Keep going — consistency beats perfection.",
        }


weekly_review_agent = WeeklyReviewAgent()
