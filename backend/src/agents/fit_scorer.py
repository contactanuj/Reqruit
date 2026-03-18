"""
FitScorer agent — computes job-candidate fit score.

Compares the user's SkillsProfile against decoded job requirements to
produce a structured fit assessment with match percentages, skill gaps,
and a narrative explanation.

Routing: DATA_EXTRACTION -> GPT-4o-mini (temp=0.0) — deterministic
scoring with structured JSON output.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class FitScorer(BaseAgent):
    """Score candidate-job fit based on skills comparison."""

    def __init__(self) -> None:
        super().__init__(
            name="fit_scorer",
            task_type=TaskType.DATA_EXTRACTION,
            system_prompt=(
                "You are a job-candidate fit assessor. Compare the candidate's "
                "skills profile against the job requirements and produce a "
                "detailed fit score.\n\n"
                "Return JSON with:\n"
                "- overall: 0-100 composite fit score\n"
                "- skills_match: 0-100 skills alignment score\n"
                "- experience_match: 0-100 experience level match\n"
                "- matching_skills: array of skills the candidate has that "
                "the job requires\n"
                "- missing_skills: array of required skills the candidate lacks\n"
                "- bonus_skills: array of candidate skills not required but valuable\n"
                "- explanation: 2-3 sentence narrative explaining the score\n\n"
                "Be objective. A perfect score requires all required skills, "
                "matching experience level, and relevant domain knowledge."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        skills_profile = state.get("skills_profile", {})
        jd_analysis = state.get("jd_analysis", "")
        job_description = state.get("job_description", "")

        if not skills_profile and not jd_analysis:
            return [HumanMessage(content="No data provided for fit scoring.")]

        parts = []
        if skills_profile:
            if isinstance(skills_profile, dict):
                skills_profile = json.dumps(skills_profile, indent=2)
            parts.append(f"## Candidate Skills Profile\n{skills_profile}")
        if jd_analysis:
            if isinstance(jd_analysis, dict):
                jd_analysis = json.dumps(jd_analysis, indent=2)
            parts.append(f"## Job Requirements (decoded)\n{jd_analysis}")
        if job_description:
            parts.append(f"## Raw Job Description\n{job_description}")

        parts.append("\nScore the candidate-job fit and return the JSON assessment.")

        return [HumanMessage(content="\n\n".join(parts))]

    def process_response(self, response, state: dict) -> dict:
        return {"fit_assessment": response.content}
