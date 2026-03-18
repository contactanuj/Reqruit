"""
CompensationAnalystAgent — qualitative salary comparison narrative.

This agent provides contextual, narrative analysis on top of the
quantitative compensation data computed by LocaleService. It explains
trade-offs between offers in different markets considering cost of living,
visa uncertainty, benefits gaps, and relocation factors.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class CompensationAnalystAgent(BaseAgent):
    """Provides narrative analysis for compensation comparisons."""

    def __init__(self) -> None:
        super().__init__(
            name="compensation_analyst",
            task_type=TaskType.COMPENSATION_ANALYSIS,
            system_prompt=(
                "You are a compensation analyst specializing in cross-market salary "
                "comparison. Given two compensation breakdowns with PPP adjustment data, "
                "provide a concise narrative covering:\n"
                "1. Which offer provides better purchasing power\n"
                "2. Key trade-offs (benefits, visa risk, career growth)\n"
                "3. Cost of living context for the specific cities\n"
                "4. A clear recommendation with reasoning\n\n"
                "Be factual and precise. Use specific numbers from the data provided. "
                "Do not speculate about data not given."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        """Build messages with compensation comparison data."""
        compensation_data = state.get("compensation_data", {})
        content = json.dumps(compensation_data, default=str)
        return [HumanMessage(content=content)]

    def process_response(self, response, state: dict) -> dict:
        """Return the narrative analysis."""
        return {"analysis_narrative": response.content}
