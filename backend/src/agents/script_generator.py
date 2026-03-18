"""
ScriptGeneratorAgent — counter-offer scripts with decision tree branches.

Generates ready-to-use negotiation scripts with branching responses for different
recruiter reactions. Each branch includes the recruiter's likely response,
recommended user counter, reasoning behind the tactic, and risk assessment.

Uses Claude Sonnet via NEGOTIATION_COACHING TaskType.
"""

import json
import re

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

logger = structlog.get_logger()

_SYSTEM_PROMPT = """\
You are an expert negotiation script writer for job offers. You create \
ready-to-use counter-offer scripts with decision tree branches that cover \
every likely recruiter reaction.

Your output must be actionable: real sentences the user can say verbatim, \
not abstract advice.

OUTPUT FORMAT (return valid JSON only):
{
  "opening_statement": "The exact words to open the counter-offer conversation",
  "branches": [
    {
      "scenario_name": "acceptance | pushback | rejection | ...",
      "recruiter_response": "What the recruiter is likely to say",
      "recommended_user_response": "Exact words the user should say back",
      "reasoning": "Why this tactic works in this scenario",
      "risk_assessment": "aggressive | moderate | safe"
    }
  ],
  "non_salary_tactics": [
    {
      "priority": "remote_work | signing_bonus | start_date | title | pto | equity_refresh",
      "script": "Exact words to negotiate this item",
      "fallback": "What to say if they push back on this item"
    }
  ],
  "general_tips": ["Tip 1", "Tip 2"]
}

RULES:
- Generate AT LEAST 3 branches: acceptance, pushback, and rejection scenarios
- Each branch must have all 5 fields (scenario_name, recruiter_response, \
recommended_user_response, reasoning, risk_assessment)
- risk_assessment must be one of: aggressive, moderate, safe
- For non-salary priorities, include specific negotiation language for each
- Scripts must be natural, professional dialogue — not bullet points
- Tailor language to the offer context (company size, role level, market)
- Return ONLY valid JSON, no markdown fences or extra text
"""


class ScriptGeneratorAgent(BaseAgent):
    """Generate counter-offer scripts with decision tree branches."""

    def __init__(self) -> None:
        super().__init__(
            name="script_generator",
            task_type=TaskType.NEGOTIATION_COACHING,
            system_prompt=_SYSTEM_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        """Build prompt with offer details, target comp, and priorities."""
        offer = state.get("offer_details", {})
        target = state.get("target_total_comp", 0)
        priorities = state.get("user_priorities", {})
        competing = state.get("competing_offers", [])
        market_data = state.get("market_data", {})

        content = (
            f"OFFER CONTEXT:\n"
            f"Company: {offer.get('company_name', 'Unknown')}\n"
            f"Role: {offer.get('role_title', 'Unknown')}\n"
            f"Current Offer: {offer.get('total_comp_annual', 0)} "
            f"{offer.get('currency', 'INR')}\n"
            f"Locale: {offer.get('locale_market', '')}\n"
        )

        if target:
            content += f"Target Total Comp: {target}\n"

        if priorities:
            priority_list = priorities if isinstance(priorities, list) else list(priorities.keys())
            content += f"User Priorities: {', '.join(str(p) for p in priority_list)}\n"

        if competing:
            content += f"Competing Offers: {len(competing)} other offer(s)\n"

        if market_data:
            content += f"Market Data: {json.dumps(market_data)}\n"

        if offer.get("components"):
            content += f"Components: {json.dumps(offer['components'])}\n"

        content += (
            "\nGenerate a counter-offer script with decision tree branches. "
            "Include at least 3 branches (acceptance, pushback, rejection). "
        )

        # Add non-salary priority instructions
        non_salary = [
            p for p in (priorities if isinstance(priorities, list) else list(priorities.keys()))
            if p.lower() not in ("salary", "base_salary", "total_comp")
        ] if priorities else []

        if non_salary:
            content += (
                f"Include specific negotiation scripts for these non-salary priorities: "
                f"{', '.join(non_salary)}. "
            )

        return [HumanMessage(content=content)]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        """Parse structured script output from LLM response."""
        raw = response.content.strip()

        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            logger.warning("script_generator_json_parse_failed", raw_length=len(raw))
            return {
                "opening_statement": raw,
                "branches": [],
                "non_salary_tactics": [],
                "general_tips": [],
            }

        return {
            "opening_statement": data.get("opening_statement", ""),
            "branches": data.get("branches", []),
            "non_salary_tactics": data.get("non_salary_tactics", []),
            "general_tips": data.get("general_tips", []),
        }
