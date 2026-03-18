"""
CareerPathSimulatorAgent — generates career path scenarios with probability estimates.

Uses Claude Sonnet (temp=0.3) for analytical scenario generation: best case,
most likely, and worst case career trajectories over 1-5 years, with
India-specific insights when locale is provided.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent, extract_json
from src.llm.models import TaskType

logger = structlog.get_logger()

CAREER_PATH_SIMULATOR_PROMPT = """\
You are a career strategist who simulates career path scenarios. Given a user's \
current position, skills, and goals, generate three scenarios for the next 1-5 years.

For each scenario provide:
- name: "best_case", "most_likely", or "worst_case"
- probability: estimated likelihood (0.0-1.0, must sum to 1.0)
- timeline_years: how many years this path takes
- milestones: key career milestones along the way
- salary_trajectory: estimated salary progression
- risks: what could go wrong
- actions_required: what the user must do to achieve this path

If the user is in the India market, include India-specific insights:
- Service-to-product company transition paths
- GCC (Global Capability Center) opportunities
- Startup ecosystem considerations
- Notice period and compensation structure differences

Return JSON:
{
  "scenarios": [
    {
      "name": "best_case",
      "probability": 0.2,
      "timeline_years": 3,
      "title_progression": ["Current -> Senior -> Lead"],
      "milestones": ["..."],
      "salary_trajectory": {"year_1": "...", "year_3": "..."},
      "risks": ["..."],
      "actions_required": ["..."]
    },
    ...
  ],
  "india_insights": {
    "service_to_product_viability": "...",
    "gcc_opportunities": "...",
    "key_considerations": ["..."]
  }
}\
"""


class CareerPathSimulatorAgent(BaseAgent):
    """Generates career path scenarios with probability estimates."""

    def __init__(self) -> None:
        super().__init__(
            name="career_path_simulator",
            task_type=TaskType.CAREER_ANALYSIS,
            system_prompt=CAREER_PATH_SIMULATOR_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = []

        role = state.get("role_title", "")
        if role:
            parts.append(f"Current role: {role}")

        industry = state.get("industry", "")
        if industry:
            parts.append(f"Industry: {industry}")

        years = state.get("years_experience", 0)
        if years:
            parts.append(f"Years of experience: {years}")

        skills = state.get("skills", [])
        if skills:
            parts.append(f"Key skills: {json.dumps(skills)}")

        goals = state.get("career_goals", "")
        if goals:
            parts.append(f"Career goals: {goals}")

        locale = state.get("locale", "")
        if locale:
            parts.append(f"Market/Region: {locale}")

        current_salary = state.get("current_salary", "")
        if current_salary:
            parts.append(f"Current compensation: {current_salary}")

        if not parts:
            parts.append("Simulate career paths for a mid-level software engineer.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        try:
            parsed = json.loads(extract_json(content))
            if isinstance(parsed, dict):
                return {
                    "scenarios": parsed.get("scenarios", []),
                    "india_insights": parsed.get("india_insights", {}),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        logger.warning("career_path_simulator_parse_failed", raw_length=len(response.content))
        return {"scenarios": [], "india_insights": {}}


career_path_simulator_agent = CareerPathSimulatorAgent()
