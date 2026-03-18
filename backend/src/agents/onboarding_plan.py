"""
OnboardingPlanAgent — LLM-powered 30-60-90 day onboarding plan generation.

Uses Claude Sonnet (temp=0.5) to generate structured onboarding plans with
three phases, skill gap analysis, and quick wins for the first 14 days.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

logger = structlog.get_logger()

ONBOARDING_PLAN_PROMPT = """\
You are a career coach specializing in onboarding success. Generate a structured \
30-60-90 day onboarding plan for a new hire.

The plan MUST have three phases:
1. Days 1-30: "Learn & Listen" — understand codebase, meet team, complete onboarding tasks
2. Days 31-60: "Contribute" — ship first features, participate in design reviews, own small projects
3. Days 61-90: "Lead Initiatives" — drive projects, mentor others, propose improvements

Each phase must have 3-5 specific milestones with a target_day (1-90) and description.

MANDATORY: Include 3-5 "quick wins" in Days 1-14 — low-effort, high-visibility actions like:
- "Fix a small bug to ship code in week 1"
- "Volunteer for the next code review rotation"
- "Set up 1:1s with your skip-level"

If skill gaps are provided, include targeted learning actions to close those gaps within 90 days.

Also generate 5-8 RELATIONSHIP TARGETS — key people the new hire should meet:
Required roles (minimum 6): direct manager, skip-level manager, tech lead, product manager, \
peer (same level, same team), cross-functional partner (design, QA, data).
For each target, provide:
- role: the person's role/title
- description: why this relationship matters for onboarding success
- conversation_starters: 2-3 tailored opening questions or topics
- optimal_timing: "Week 1" for manager/peer, "Week 2-3" for skip-level/cross-functional

Return a JSON object:
{
  "milestones": [
    {"title": "...", "target_day": 1, "description": "..."},
    ...
  ],
  "quick_wins": [
    {"title": "...", "target_day": 3, "description": "..."},
    ...
  ],
  "skill_gap_actions": [
    {"title": "...", "target_day": 30, "description": "..."},
    ...
  ],
  "relationship_targets": [
    {"role": "Direct Manager", "description": "...", "conversation_starters": ["...", "..."], "optimal_timing": "Week 1"},
    ...
  ]
}

Be specific to the company and role. Use actual company name and role title in descriptions.\
"""


def _parse_relationship_targets(parsed: dict) -> list[dict]:
    """Extract and validate relationship targets from parsed LLM response."""
    raw_targets = parsed.get("relationship_targets", [])
    targets = []
    for t in raw_targets:
        if isinstance(t, dict) and "role" in t:
            targets.append({
                "role": t["role"],
                "description": t.get("description", ""),
                "conversation_starters": t.get("conversation_starters", []),
                "optimal_timing": t.get("optimal_timing", ""),
            })
    return targets


class OnboardingPlanAgent(BaseAgent):
    """LLM-powered onboarding plan generator."""

    def __init__(self) -> None:
        super().__init__(
            name="onboarding_plan",
            task_type=TaskType.ONBOARDING_PLANNING,
            system_prompt=ONBOARDING_PLAN_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = []

        company = state.get("company_name", "")
        role = state.get("role_title", "")
        if company:
            parts.append(f"Company: {company}")
        if role:
            parts.append(f"Role: {role}")

        skill_gaps = state.get("skill_gaps", [])
        if skill_gaps:
            parts.append(f"Skill gaps to address: {json.dumps(skill_gaps)}")

        jd_text = state.get("jd_text", "")
        if jd_text:
            parts.append(f"Job description:\n{jd_text}")

        feedback = state.get("feedback", "")
        if feedback:
            parts.append(f"User feedback on previous plan:\n{feedback}")

        if not parts:
            parts.append("Generate a general onboarding plan for a software engineering role.")

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
                milestones = parsed.get("milestones", [])
                quick_wins = parsed.get("quick_wins", [])
                skill_gap_actions = parsed.get("skill_gap_actions", [])

                all_milestones = milestones + quick_wins + skill_gap_actions
                # Ensure valid structure
                validated = []
                for m in all_milestones:
                    if isinstance(m, dict) and "title" in m:
                        validated.append({
                            "title": m["title"],
                            "target_day": min(max(int(m.get("target_day", 1)), 1), 90),
                            "description": m.get("description", ""),
                        })

                relationship_targets = _parse_relationship_targets(parsed)

                return {"milestones": validated, "relationship_targets": relationship_targets}
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        logger.warning("onboarding_plan_parse_failed", raw_length=len(response.content))
        return {
            "milestones": [
                {"title": "Meet your team and manager", "target_day": 1, "description": "Schedule introductions"},
                {"title": "Complete dev environment setup", "target_day": 3, "description": "Get your tools working"},
                {"title": "Ship your first code change", "target_day": 7, "description": "Fix a small bug or documentation issue"},
                {"title": "Own a small feature", "target_day": 45, "description": "Take ownership of a feature from design to delivery"},
                {"title": "Lead a team initiative", "target_day": 75, "description": "Propose and drive an improvement"},
            ],
            "relationship_targets": [],
        }


onboarding_plan_agent = OnboardingPlanAgent()
