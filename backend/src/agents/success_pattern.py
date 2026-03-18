"""
Success pattern agent — identifies actionable patterns from application outcomes.

Given aggregated application data (response rates, strategies used, resume
versions, submission methods), identifies what works and what doesn't.

Uses GPT-4o-mini (SUCCESS_PATTERN) for deterministic analysis.
"""

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

SUCCESS_PATTERN_PROMPT = """\
You are a data analyst specializing in job application outcomes. Given \
aggregated application data (response rates, strategies used, resume \
versions, submission methods), identify actionable patterns. Output \
structured JSON with: top_performing_strategies, underperforming_approaches, \
recommendations, confidence_level.\
"""


class SuccessPatternAgent(BaseAgent):
    """Analyzes application outcome data to identify success patterns."""

    def __init__(self) -> None:
        super().__init__(
            name="success_pattern",
            task_type=TaskType.SUCCESS_PATTERN,
            system_prompt=SUCCESS_PATTERN_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        analytics_data = state.get("analytics_data", "")
        return [
            HumanMessage(
                content=(
                    "Analyze the following application outcome data and "
                    "identify actionable patterns:\n\n"
                    f"{analytics_data}"
                )
            )
        ]

    def process_response(self, response, state: dict) -> dict:
        return {"success_insights": response.content}
