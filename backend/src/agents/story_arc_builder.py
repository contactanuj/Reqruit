"""
StoryArcBuilderAgent — synthesizes career narratives from work experience.

Uses Claude Sonnet (temp=0.7) for creative narrative synthesis: transforms
raw work experience into compelling career stories for interviews,
networking, and personal branding.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent, extract_json
from src.llm.models import TaskType

logger = structlog.get_logger()

STORY_ARC_PROMPT = """\
You are a career narrative specialist. Transform the user's work experience \
into compelling career stories and a cohesive professional narrative.

Create:
1. An overarching career narrative (the "arc") that ties experiences together
2. 3-5 key stories that highlight different strengths
3. A positioning statement for networking/interviews

Each story should follow the STAR format but feel natural, not formulaic:
- Situation: brief context
- Task: what was needed
- Action: what the user did (specific, with skills demonstrated)
- Result: quantified impact where possible

Return JSON:
{
  "career_arc": {
    "theme": "From individual contributor to systems thinker",
    "summary": "...",
    "key_transitions": ["..."]
  },
  "stories": [
    {
      "title": "...",
      "strength_demonstrated": "...",
      "situation": "...",
      "task": "...",
      "action": "...",
      "result": "...",
      "best_used_for": "interviews about leadership"
    }
  ],
  "positioning_statement": "...",
  "elevator_pitch": "..."
}\
"""


class StoryArcBuilderAgent(BaseAgent):
    """Synthesizes career narratives from work experience."""

    def __init__(self) -> None:
        super().__init__(
            name="story_arc_builder",
            task_type=TaskType.NARRATIVE_SYNTHESIS,
            system_prompt=STORY_ARC_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = []

        experiences = state.get("experiences", [])
        if experiences:
            parts.append(f"Work experiences: {json.dumps(experiences)}")

        achievements = state.get("achievements", [])
        if achievements:
            parts.append(f"Key achievements: {json.dumps(achievements)}")

        role = state.get("role_title", "")
        if role:
            parts.append(f"Current role: {role}")

        target = state.get("target_narrative", "")
        if target:
            parts.append(f"Target narrative direction: {target}")

        feedback = state.get("feedback", "")
        if feedback:
            parts.append(f"Feedback on previous narrative: {feedback}")

        if not parts:
            parts.append("Create a general career narrative framework.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        try:
            parsed = json.loads(extract_json(content))
            if isinstance(parsed, dict):
                return {
                    "career_arc": parsed.get("career_arc", {}),
                    "stories": parsed.get("stories", []),
                    "positioning_statement": parsed.get("positioning_statement", ""),
                    "elevator_pitch": parsed.get("elevator_pitch", ""),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        logger.warning("story_arc_parse_failed", raw_length=len(response.content))
        return {
            "career_arc": {},
            "stories": [],
            "positioning_statement": "",
            "elevator_pitch": "",
        }


story_arc_builder_agent = StoryArcBuilderAgent()
