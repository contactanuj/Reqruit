"""
CompensationCoachAgent — generates anchoring scripts for salary negotiations.

Produces 3+ locale-aware scripts with strategy explanations and risk levels.
India locale uses CTC-hike framing; US locale uses market-rate framing.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

logger = structlog.get_logger()

COMPENSATION_COACH_PROMPT = """\
You are an expert compensation negotiation coach. Generate 3 or more \
anchoring scripts for the "What are your salary expectations?" question.

For each script, provide a JSON object with:
- script_text: The exact words to say
- strategy_name: One of "anchoring_high", "deflecting", "range_based", "value_based"
- strategy_explanation: Why this strategy works in this context
- risk_level: "low", "medium", or "high" based on how aggressive the anchoring is

LOCALE RULES:
- If locale is "IN" (India): Use CTC-hike framing. Reference current CTC and target \
  as a percentage growth. Indian norms: 20-50% hike is standard for job changes.
- If locale is "US": Use market-rate framing. NEVER reference current salary \
  (illegal to ask in many states). Frame around market data and total comp ranges.

If company context is provided, reference company-specific signals \
(funding stage, known comp bands, Glassdoor data) to calibrate the anchoring range.

Also include a "general_tips" JSON array with 2-3 general negotiation tips.

Return a JSON object with two keys: "scripts" (array of script objects) and \
"general_tips" (array of tip strings).\
"""


class CompensationCoachAgent(BaseAgent):
    """Generates locale-aware salary anchoring scripts."""

    def __init__(self) -> None:
        super().__init__(
            name="compensation_coach",
            task_type=TaskType.NEGOTIATION_COACHING,
            system_prompt=COMPENSATION_COACH_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        locale = state.get("locale", "IN")
        if locale == "IN":
            comp_label = "Current CTC"
            comp_value = state.get("current_ctc", "Not provided")
        else:
            comp_label = "Current salary"
            comp_value = state.get("current_salary", "Not provided")

        user_msg = (
            f"Locale: {locale}\n"
            f"{comp_label}: {comp_value}\n"
            f"Target range: {state.get('target_range_min')} - {state.get('target_range_max')}\n"
            f"Role: {state.get('role_title')}\n"
            f"Company: {state.get('company_name')}\n"
            f"City: {state.get('city', 'Not specified')}\n"
            f"Company context: {state.get('company_context', 'None provided')}"
        )

        return [HumanMessage(content=user_msg)]

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
                scripts = parsed.get("scripts", [])
                tips = parsed.get("general_tips", [])
                return {"scripts": json.dumps(scripts), "general_tips": json.dumps(tips)}
            if isinstance(parsed, list):
                return {"scripts": json.dumps(parsed), "general_tips": json.dumps([])}
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: return raw text as single script
        return {
            "scripts": json.dumps([{
                "script_text": response.content,
                "strategy_name": "general",
                "strategy_explanation": "General coaching advice",
                "risk_level": "medium",
            }]),
            "general_tips": json.dumps([]),
        }


compensation_coach_agent = CompensationCoachAgent()
