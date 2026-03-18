"""
ServiceCompanyExitPlannerAgent — plans transitions from service to product companies.

Uses Claude Sonnet (temp=0.5) for strategic planning of service-to-product
company transitions, common in India's tech market. Addresses skill gaps,
interview preparation, resume positioning, and timeline planning.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent, extract_json
from src.llm.models import TaskType

logger = structlog.get_logger()

SERVICE_EXIT_PLANNER_PROMPT = """\
You are a career strategist specializing in service-to-product company transitions \
in the Indian tech market. Help the user plan their exit from a service/consulting \
company to a product company.

Address:
1. Current skill assessment vs product company expectations
2. Resume repositioning strategy (project-based → product-based framing)
3. Interview preparation focus areas (system design, DSA, product sense)
4. Timeline with milestones (typically 3-6 months of preparation)
5. Target company tiers (FAANG, unicorns, well-funded startups, established product cos)
6. Compensation expectations (service vs product pay gaps)
7. Notice period strategy (many Indian service companies have 60-90 day notice periods)

Return JSON:
{
  "readiness_score": 65,
  "skill_gaps": [
    {"skill": "System Design", "current": "basic", "required": "advanced", "action": "..."}
  ],
  "resume_strategy": {
    "key_changes": ["..."],
    "project_reframing": ["..."]
  },
  "interview_prep": {
    "focus_areas": ["..."],
    "estimated_prep_months": 4,
    "weekly_plan": "..."
  },
  "target_companies": {
    "tier_1": ["..."],
    "tier_2": ["..."],
    "tier_3": ["..."]
  },
  "timeline": [
    {"month": 1, "focus": "...", "milestones": ["..."]}
  ],
  "compensation_insights": {
    "current_range": "...",
    "expected_range": "...",
    "negotiation_tips": ["..."]
  },
  "notice_period_strategy": "..."
}\
"""


class ServiceCompanyExitPlannerAgent(BaseAgent):
    """Plans service-to-product company career transitions."""

    def __init__(self) -> None:
        super().__init__(
            name="service_exit_planner",
            task_type=TaskType.SERVICE_EXIT_PLANNING,
            system_prompt=SERVICE_EXIT_PLANNER_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = []

        company = state.get("current_company", "")
        if company:
            parts.append(f"Current company: {company}")

        company_type = state.get("company_type", "service")
        parts.append(f"Company type: {company_type}")

        role = state.get("role_title", "")
        if role:
            parts.append(f"Current role: {role}")

        years = state.get("years_experience", 0)
        if years:
            parts.append(f"Years of experience: {years}")

        skills = state.get("skills", [])
        if skills:
            parts.append(f"Current skills: {json.dumps(skills)}")

        target = state.get("target_companies", "")
        if target:
            parts.append(f"Target companies/type: {target}")

        notice_period = state.get("notice_period_days", 0)
        if notice_period:
            parts.append(f"Current notice period: {notice_period} days")

        current_ctc = state.get("current_ctc", "")
        if current_ctc:
            parts.append(f"Current CTC: {current_ctc}")

        if not parts:
            parts.append("Plan a service-to-product company transition for a mid-level engineer in India.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        try:
            parsed = json.loads(extract_json(content))
            if isinstance(parsed, dict):
                return {
                    "readiness_score": parsed.get("readiness_score", 0),
                    "skill_gaps": parsed.get("skill_gaps", []),
                    "resume_strategy": parsed.get("resume_strategy", {}),
                    "interview_prep": parsed.get("interview_prep", {}),
                    "target_companies": parsed.get("target_companies", {}),
                    "timeline": parsed.get("timeline", []),
                    "compensation_insights": parsed.get("compensation_insights", {}),
                    "notice_period_strategy": parsed.get("notice_period_strategy", ""),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        logger.warning("service_exit_planner_parse_failed", raw_length=len(response.content))
        return {
            "readiness_score": 0,
            "skill_gaps": [],
            "resume_strategy": {},
            "interview_prep": {},
            "target_companies": {},
            "timeline": [],
            "compensation_insights": {},
            "notice_period_strategy": "",
        }


service_exit_planner_agent = ServiceCompanyExitPlannerAgent()
