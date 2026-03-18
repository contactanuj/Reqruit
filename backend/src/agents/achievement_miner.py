"""
AchievementMiner agent — extracts quantified achievements from work history.

Uses a guided interview-style prompt to mine achievements in CAR format
(Context, Action, Result) from resume text and work descriptions. The
extracted achievements feed into the SkillsProfile and power STAR story
generation, cover letter personalization, and interview prep.

Routing: ACHIEVEMENT_MINING -> Claude Sonnet (temp=0.7) — creative extraction
requires strong reasoning and natural language generation.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class AchievementMiner(BaseAgent):
    """Extract professional achievements from resume and work history."""

    def __init__(self) -> None:
        super().__init__(
            name="achievement_miner",
            task_type=TaskType.ACHIEVEMENT_MINING,
            system_prompt=(
                "You are an expert career coach specialized in extracting "
                "quantified professional achievements from work history.\n\n"
                "For each achievement, extract:\n"
                "- title: A concise achievement headline\n"
                "- description: What was done in detail\n"
                "- impact: Quantified result (metrics, percentages, dollar amounts)\n"
                "- skills_demonstrated: Technical and soft skills used\n"
                "- context: Role and company where this happened\n\n"
                "Return a JSON array of achievement objects. Focus on measurable "
                "impact — numbers, percentages, and business outcomes. If no "
                "metrics are stated, infer reasonable estimates and mark them "
                "as approximate."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        resume_text = state.get("resume_text", "")
        work_history = state.get("work_history", "")
        existing_achievements = state.get("existing_achievements", [])

        if not resume_text and not work_history:
            return [HumanMessage(content="No work history provided. Please provide resume text or work history to mine achievements from.")]

        parts = []
        if resume_text:
            parts.append(f"## Resume\n{resume_text}")
        if work_history:
            parts.append(f"## Work History\n{work_history}")
        if existing_achievements:
            parts.append(f"## Already Extracted (avoid duplicates)\n{json.dumps(existing_achievements, indent=2)}")

        parts.append(
            "\nExtract all quantified achievements from the above. "
            "Return a JSON array of objects with keys: "
            "title, description, impact, skills_demonstrated, context."
        )

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response, state: dict) -> dict:
        return {"mined_achievements": response.content}
