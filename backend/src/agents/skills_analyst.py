"""
SkillsAnalyst agent — maps and assesses skills from achievements and resume.

Takes mined achievements and resume text, then produces a structured skills
inventory with proficiency levels, categories, and years of experience.
Deterministic extraction — uses GPT-4o-mini at temperature 0.0.

Routing: SKILLS_ANALYSIS -> GPT-4o-mini (temp=0.0) — structured extraction
benefits from deterministic, JSON-focused model.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class SkillsAnalyst(BaseAgent):
    """Analyze and categorize skills from achievements and resume."""

    def __init__(self) -> None:
        super().__init__(
            name="skills_analyst",
            task_type=TaskType.SKILLS_ANALYSIS,
            system_prompt=(
                "You are a technical skills analyst. Given a resume and list of "
                "achievements, produce a comprehensive skills inventory.\n\n"
                "For each skill, determine:\n"
                "- name: The skill name (standardized, e.g., 'Python' not 'python3')\n"
                "- category: One of: Programming Language, Framework, Database, "
                "Cloud, DevOps, Soft Skill, Domain Knowledge, Tool, Methodology\n"
                "- proficiency: BEGINNER / INTERMEDIATE / ADVANCED / EXPERT\n"
                "- years_experience: Estimated years based on career timeline\n"
                "- confidence: 0.0-1.0 confidence in your assessment\n\n"
                "Also produce a 2-3 sentence summary of the person's overall "
                "skill profile.\n\n"
                "Return JSON with keys: skills (array), summary (string)."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        resume_text = state.get("resume_text", "")
        achievements = state.get("mined_achievements", "")

        if not resume_text and not achievements:
            return [HumanMessage(content="No data provided for skills analysis.")]

        parts = []
        if resume_text:
            parts.append(f"## Resume\n{resume_text}")
        if achievements:
            if isinstance(achievements, list):
                achievements = json.dumps(achievements, indent=2)
            parts.append(f"## Achievements\n{achievements}")

        parts.append(
            "\nAnalyze the above and return a JSON object with:\n"
            "- skills: array of skill objects (name, category, proficiency, "
            "years_experience, confidence)\n"
            "- summary: 2-3 sentence profile summary"
        )

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response, state: dict) -> dict:
        return {"skills_analysis": response.content}
