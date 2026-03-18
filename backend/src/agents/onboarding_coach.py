"""
OnboardingCoachAgent — confidential coaching for tricky first-90-days situations.

Uses Claude Sonnet (temp=0.7) to provide situation-specific, confidential
coaching: organizational context, concrete actions, conversation scripts,
and escalation guidance.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

logger = structlog.get_logger()

ONBOARDING_COACH_PROMPT = """\
You are a confidential onboarding coach for new hires. This is a private coaching \
session — you will never judge or share what is discussed here.

When a new hire describes a tricky situation, provide structured coaching in EXACTLY \
this JSON format:
{
  "whats_happening": "Organizational context — what's likely going on behind the scenes",
  "how_to_respond": "Concrete, actionable steps the new hire should take",
  "conversation_scripts": ["Exact phrase or script 1", "Exact phrase or script 2"],
  "when_to_escalate": "Red flags that warrant HR or skip-level involvement vs normal friction"
}

Guidelines:
- Be empathetic but practical — new hires need actionable advice, not platitudes.
- Provide 2-4 conversation scripts with exact phrases they can use.
- Distinguish between normal new-hire friction and genuine red flags.
- Consider the company culture and role context when available.
- Never suggest the new hire is at fault without evidence — assume good intent on all sides.\
"""


class OnboardingCoachAgent(BaseAgent):
    """Confidential onboarding coach providing situation-specific guidance."""

    def __init__(self) -> None:
        super().__init__(
            name="onboarding_coach",
            task_type=TaskType.ONBOARDING_PLANNING,
            system_prompt=ONBOARDING_COACH_PROMPT,
        )
        # Override temperature to 0.7 (routing table default is 0.5)
        self._temperature_override = 0.7

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = []

        situation = state.get("coaching_query", "")
        if situation:
            parts.append(f"Situation: {situation}")

        company = state.get("company_name", "")
        if company:
            parts.append(f"Company: {company}")

        role = state.get("role_title", "")
        if role:
            parts.append(f"Role: {role}")

        plan = state.get("plan", {})
        if plan:
            milestones = plan.get("milestones", [])
            completed = sum(1 for m in milestones if isinstance(m, dict) and m.get("completed"))
            total = len(milestones)
            if total:
                parts.append(f"Progress: {completed}/{total} milestones completed")

        if not parts:
            parts.append("The new hire needs general onboarding guidance.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        # Strip markdown fences
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
                    "coaching_response": json.dumps({
                        "whats_happening": parsed.get("whats_happening", ""),
                        "how_to_respond": parsed.get("how_to_respond", ""),
                        "conversation_scripts": parsed.get("conversation_scripts", []),
                        "when_to_escalate": parsed.get("when_to_escalate", ""),
                    }),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        logger.warning("onboarding_coach_parse_failed", raw_length=len(response.content))
        return {
            "coaching_response": json.dumps({
                "whats_happening": response.content,
                "how_to_respond": "",
                "conversation_scripts": [],
                "when_to_escalate": "",
            }),
        }


onboarding_coach_agent = OnboardingCoachAgent()
