"""
CareerDriftDetectorAgent — assesses career health across six core metrics.

Uses Claude Sonnet (temp=0.3) for analytical career health scoring:
skill relevance, market demand, compensation alignment, growth trajectory,
network strength, and job satisfaction.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent, extract_json
from src.llm.models import TaskType

logger = structlog.get_logger()

CAREER_DRIFT_PROMPT = """\
You are a career health analyst. Assess the user's career vitals across six \
dimensions and detect any drift from their goals.

Score each metric 0-100 and classify the trend as "improving", "stable", or "declining".

The six metrics:
1. skill_relevance — How current are the user's skills for their target market?
2. market_demand — How strong is hiring demand for their role/industry?
3. compensation_alignment — Is their compensation competitive for their level?
4. growth_trajectory — Are they progressing at an appropriate pace?
5. network_strength — How well-connected are they professionally?
6. job_satisfaction — How aligned is their current role with their goals?

Also identify any drift indicators — signs the career is veering off course. \
Classify each as skill_gap, market_shift, compensation, or stagnation with \
severity low/medium/high.

Return JSON:
{
  "overall_score": 75.0,
  "career_stage": "mid",
  "metrics": [
    {"name": "skill_relevance", "score": 80, "trend": "stable", "explanation": "..."},
    ...
  ],
  "drift_indicators": [
    {"category": "skill_gap", "severity": "medium", "description": "...", "recommended_action": "..."},
    ...
  ]
}\
"""


class CareerDriftDetectorAgent(BaseAgent):
    """Analyzes career health metrics and detects drift from goals."""

    def __init__(self) -> None:
        super().__init__(
            name="career_drift_detector",
            task_type=TaskType.CAREER_ANALYSIS,
            system_prompt=CAREER_DRIFT_PROMPT,
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
            parts.append(f"Current skills: {json.dumps(skills)}")

        locale = state.get("locale", "")
        if locale:
            parts.append(f"Location/Market: {locale}")

        goals = state.get("career_goals", "")
        if goals:
            parts.append(f"Career goals: {goals}")

        if not parts:
            parts.append("Provide a general career health assessment.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        try:
            parsed = json.loads(extract_json(content))
            if isinstance(parsed, dict):
                return {
                    "overall_score": parsed.get("overall_score", 0.0),
                    "career_stage": parsed.get("career_stage", ""),
                    "metrics": parsed.get("metrics", []),
                    "drift_indicators": parsed.get("drift_indicators", []),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        logger.warning("career_drift_parse_failed", raw_length=len(response.content))
        return {
            "overall_score": 50.0,
            "career_stage": "unknown",
            "metrics": [],
            "drift_indicators": [],
        }


career_drift_detector_agent = CareerDriftDetectorAgent()
