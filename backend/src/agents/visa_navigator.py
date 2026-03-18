"""
VisaNavigatorAgent — visa eligibility comparison and guidance.

This agent provides detailed visa eligibility analysis based on the user's
nationality, target market, qualifications, and the market's visa requirements
from MarketConfig. It explains visa types, eligibility criteria, timelines,
and practical considerations.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class VisaNavigatorAgent(BaseAgent):
    """Provides visa eligibility analysis and guidance."""

    def __init__(self) -> None:
        super().__init__(
            name="visa_navigator",
            task_type=TaskType.VISA_NAVIGATION,
            system_prompt=(
                "You are an immigration and visa specialist. Given a user's nationality, "
                "target work market, qualifications, and the market's visa requirements, "
                "provide a detailed analysis covering:\n"
                "1. Applicable visa categories and their eligibility criteria\n"
                "2. Estimated processing timelines and costs\n"
                "3. Key requirements (education, experience, employer sponsorship)\n"
                "4. Common pitfalls and how to avoid them\n"
                "5. Alternative pathways if primary visa isn't feasible\n\n"
                "Be factual and precise. Clearly note when information may be outdated "
                "and recommend consulting an immigration attorney for specific cases."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        """Build messages with visa context."""
        nationality = state.get("nationality", "")
        target_market = state.get("target_market", "")
        visa_requirements = state.get("visa_requirements", [])
        qualifications = state.get("qualifications", [])
        years_experience = state.get("years_experience", 0)

        context_parts = []
        if nationality:
            context_parts.append(f"Nationality: {nationality}")
        if target_market:
            context_parts.append(f"Target Market: {target_market}")
        if visa_requirements:
            context_parts.append(f"Visa Requirements: {json.dumps(visa_requirements, default=str)}")
        if qualifications:
            context_parts.append(f"Qualifications: {', '.join(qualifications)}")
        if years_experience:
            context_parts.append(f"Years of Experience: {years_experience}")

        content = "\n".join(context_parts) if context_parts else "No context provided."
        return [HumanMessage(content=content)]

    def process_response(self, response, state: dict) -> dict:
        """Return the visa analysis."""
        return {"visa_analysis": response.content}
