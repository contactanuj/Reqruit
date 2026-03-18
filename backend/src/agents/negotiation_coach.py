"""
NegotiationCoachAgent — multi-turn negotiation simulation with recruiter persona.

Plays a realistic recruiter role with locale-specific framing (India: CTC-hike-anchored,
US: market-rate-anchored) while providing coaching feedback on the user's negotiation tactics.

Uses Claude Sonnet with temp=0.7 for creative, realistic dialogue.
"""

import json
import re

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

logger = structlog.get_logger()

_SYSTEM_PROMPT = """\
You are a negotiation simulation engine that plays TWO roles simultaneously:

1. **RECRUITER**: You play a realistic HR recruiter/hiring manager who is negotiating \
a job offer. Stay in character with realistic pushback, concessions, and tactics \
appropriate to the company size, role level, and market conditions provided.

2. **COACH**: After each recruiter response, you provide coaching feedback evaluating \
the user's negotiation tactic and suggesting improvements.

LOCALE-SPECIFIC RULES:
- For India (IN): Use CTC-hike-anchored framing ("We've already offered a 30% hike \
over your current CTC"), negotiate before-offer-stage where appropriate, reference \
Indian negotiation norms (notice period buyout, joining bonus, variable pay structure).
- For US: Use market-rate-anchored framing ("This is competitive for the Bay Area \
market"), negotiate post-offer, focus on total comp package (base, RSU, signing bonus, \
401k match).

RESPONSE FORMAT (return valid JSON only):
{
  "recruiter_response": "What the recruiter says next",
  "coaching_feedback": "Analysis of the user's tactic and suggestions",
  "tactic_detected": "Name of the negotiation tactic the user employed",
  "turn_number": <integer>,
  "simulation_complete": false
}

Rules:
- Maintain consistent recruiter persona across all turns
- Provide specific, actionable coaching feedback
- Detect tactics: anchoring, framing, silence, competing offers, value-based, emotional
- Set simulation_complete=true only when a natural conclusion is reached (agreement, \
walkaway, or 10+ turns)
- Return ONLY valid JSON, no markdown fences or extra text
"""


class NegotiationCoachAgent(BaseAgent):
    """Multi-turn negotiation simulation with coaching feedback."""

    def __init__(self) -> None:
        super().__init__(
            name="negotiation_coach",
            task_type=TaskType.NEGOTIATION_COACHING,
            system_prompt=_SYSTEM_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        """Build conversation messages for the negotiation turn."""
        messages = []

        # Include offer context in first turn
        offer_details = state.get("offer_details", {})
        market_data = state.get("market_data", {})
        competing = state.get("competing_offers", [])
        priorities = state.get("user_priorities", {})
        locale = offer_details.get("locale_market", "")

        context = (
            f"OFFER CONTEXT:\n"
            f"Company: {offer_details.get('company_name', 'Unknown')}\n"
            f"Role: {offer_details.get('role_title', 'Unknown')}\n"
            f"Current Offer: {offer_details.get('total_comp_annual', 0)} "
            f"{offer_details.get('currency', 'INR')}\n"
            f"Locale: {locale}\n"
        )

        if competing:
            context += f"Competing offers: {len(competing)}\n"
        if priorities:
            context += f"User priorities: {json.dumps(priorities)}\n"
        if market_data:
            context += f"Market data: {json.dumps(market_data)}\n"

        # Include conversation history from transcript
        transcript = state.get("simulation_transcript", [])
        if not transcript:
            # First turn — set up the scenario
            context += "\nThis is the START of the negotiation. The recruiter should open."
            messages.append(HumanMessage(content=context))
        else:
            messages.append(HumanMessage(content=context))
            # Add previous turns as conversation
            for turn in transcript:
                if turn.get("role") == "recruiter":
                    messages.append(
                        HumanMessage(content=f"[Previous recruiter]: {turn['content']}")
                    )
                elif turn.get("role") == "user":
                    messages.append(
                        HumanMessage(content=f"[User response]: {turn['content']}")
                    )

            # Add the latest user response
            user_response = state.get("user_response", "")
            if user_response:
                messages.append(
                    HumanMessage(
                        content=f"The user responds: {user_response}\n\n"
                        f"Provide the recruiter's next response and coaching feedback."
                    )
                )

        return messages

    def process_response(self, response: AIMessage, state: dict) -> dict:
        """Parse recruiter response and coaching feedback from LLM output."""
        raw = response.content.strip()

        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            logger.warning("negotiation_coach_json_parse_failed", raw_length=len(raw))
            return {
                "recruiter_response": raw,
                "coaching_feedback": "",
                "tactic_detected": "",
                "turn_number": len(state.get("simulation_transcript", [])) + 1,
                "simulation_complete": False,
            }

        return {
            "recruiter_response": data.get("recruiter_response", ""),
            "coaching_feedback": data.get("coaching_feedback", ""),
            "tactic_detected": data.get("tactic_detected", ""),
            "turn_number": data.get("turn_number", 1),
            "simulation_complete": data.get("simulation_complete", False),
        }
