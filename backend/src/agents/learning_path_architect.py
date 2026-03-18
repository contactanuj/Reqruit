"""
LearningPathArchitectAgent — generates personalized learning paths for skill gaps.

Uses Claude Sonnet (temp=0.5) to create structured learning paths with
curated resources, time estimates, and milestone checkpoints.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent, extract_json
from src.llm.models import TaskType

logger = structlog.get_logger()

LEARNING_PATH_PROMPT = """\
You are a learning path architect. Given a user's current skills and target skills, \
create a structured learning plan with curated resources and milestones.

For each skill gap, provide:
- skill: the skill to learn
- current_level: beginner/intermediate/advanced
- target_level: the desired proficiency
- estimated_hours: total hours to reach target
- resources: list of learning resources (courses, books, projects)
- milestones: checkpoints to measure progress
- priority: high/medium/low based on career impact

Each resource should have:
- title: resource name
- type: course, book, project, tutorial, certification
- url: link (use well-known platforms: Coursera, Udemy, O'Reilly, etc.)
- estimated_hours: time to complete
- cost: free, paid, or specific amount

Return JSON:
{
  "learning_paths": [
    {
      "skill": "System Design",
      "current_level": "beginner",
      "target_level": "advanced",
      "estimated_hours": 120,
      "priority": "high",
      "resources": [
        {"title": "...", "type": "course", "url": "...", "estimated_hours": 40, "cost": "free"}
      ],
      "milestones": [
        {"title": "Complete basics", "target_week": 4, "criteria": "..."}
      ]
    }
  ],
  "total_estimated_hours": 200,
  "recommended_schedule": "10 hours/week for 20 weeks"
}\
"""


class LearningPathArchitectAgent(BaseAgent):
    """Creates personalized learning paths for skill gap closure."""

    def __init__(self) -> None:
        super().__init__(
            name="learning_path_architect",
            task_type=TaskType.LEARNING_PATH,
            system_prompt=LEARNING_PATH_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = []

        current_skills = state.get("current_skills", [])
        if current_skills:
            parts.append(f"Current skills: {json.dumps(current_skills)}")

        target_skills = state.get("target_skills", [])
        if target_skills:
            parts.append(f"Target skills to learn: {json.dumps(target_skills)}")

        role = state.get("role_title", "")
        if role:
            parts.append(f"Target role: {role}")

        hours_per_week = state.get("hours_per_week", 10)
        parts.append(f"Available learning time: {hours_per_week} hours/week")

        budget = state.get("budget", "")
        if budget:
            parts.append(f"Learning budget: {budget}")

        if not parts:
            parts.append("Create a general software engineering learning path.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        try:
            parsed = json.loads(extract_json(content))
            if isinstance(parsed, dict):
                return {
                    "learning_paths": parsed.get("learning_paths", []),
                    "total_estimated_hours": parsed.get("total_estimated_hours", 0),
                    "recommended_schedule": parsed.get("recommended_schedule", ""),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        logger.warning("learning_path_parse_failed", raw_length=len(response.content))
        return {"learning_paths": [], "total_estimated_hours": 0, "recommended_schedule": ""}


learning_path_architect_agent = LearningPathArchitectAgent()
