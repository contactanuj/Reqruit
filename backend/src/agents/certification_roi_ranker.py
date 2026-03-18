"""
CertificationROIRankerAgent — ranks certifications by return on investment.

Uses GPT-4o-mini (temp=0.0) for deterministic ROI analysis of certifications
based on career goals, market demand, and locale-specific weighting
(e.g., AWS certs weighted higher in India GCC market).
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent, extract_json
from src.llm.models import TaskType

logger = structlog.get_logger()

CERTIFICATION_ROI_PROMPT = """\
You are a certification ROI analyst. Rank certifications by their return on investment \
for the user's specific career context.

For each certification, calculate an ROI score (0-100) based on:
- Market demand multiplier (how much it increases job opportunities)
- Salary impact (typical salary increase after certification)
- Cost (exam fees, study materials, time investment)
- Relevance to career goals
- Locale-specific weighting (e.g., AWS/Azure certs are especially valued in India's \
  GCC market; PMP is valued in service companies)

Return JSON:
{
  "certifications": [
    {
      "name": "AWS Solutions Architect - Associate",
      "provider": "Amazon Web Services",
      "roi_score": 85,
      "cost_usd": 300,
      "study_hours": 120,
      "salary_impact_pct": 15,
      "market_demand": "high",
      "relevance": "high",
      "locale_bonus": "India GCC market values AWS heavily",
      "recommendation": "Strongly recommended — high ROI for your career path",
      "prep_resources": ["..."]
    }
  ],
  "top_recommendation": "...",
  "locale_insights": "..."
}\
"""


class CertificationROIRankerAgent(BaseAgent):
    """Ranks certifications by ROI for the user's career context."""

    def __init__(self) -> None:
        super().__init__(
            name="certification_roi_ranker",
            task_type=TaskType.CERTIFICATION_ROI,
            system_prompt=CERTIFICATION_ROI_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = []

        role = state.get("role_title", "")
        if role:
            parts.append(f"Current role: {role}")

        skills = state.get("skills", [])
        if skills:
            parts.append(f"Current skills: {json.dumps(skills)}")

        goals = state.get("career_goals", "")
        if goals:
            parts.append(f"Career goals: {goals}")

        locale = state.get("locale", "")
        if locale:
            parts.append(f"Market/Region: {locale}")

        budget = state.get("budget", "")
        if budget:
            parts.append(f"Certification budget: {budget}")

        existing_certs = state.get("existing_certifications", [])
        if existing_certs:
            parts.append(f"Already certified in: {json.dumps(existing_certs)}")

        if not parts:
            parts.append("Rank top certifications for a software engineer.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        try:
            parsed = json.loads(extract_json(content))
            if isinstance(parsed, dict):
                return {
                    "certifications": parsed.get("certifications", []),
                    "top_recommendation": parsed.get("top_recommendation", ""),
                    "locale_insights": parsed.get("locale_insights", ""),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        logger.warning("certification_roi_parse_failed", raw_length=len(response.content))
        return {"certifications": [], "top_recommendation": "", "locale_insights": ""}


certification_roi_ranker_agent = CertificationROIRankerAgent()
