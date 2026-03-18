"""
JDDecoder agent — extracts structured requirements from job descriptions.

Parses a raw job description into structured data: required skills,
preferred skills, experience level, responsibilities, and cultural signals.
Used as input for the FitScorer agent and for enriching Job documents.

Routing: DATA_EXTRACTION -> GPT-4o-mini (temp=0.0) — deterministic
structured extraction from unstructured text.
"""

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class JDDecoder(BaseAgent):
    """Extract structured requirements from a job description."""

    def __init__(self) -> None:
        super().__init__(
            name="jd_decoder",
            task_type=TaskType.DATA_EXTRACTION,
            system_prompt=(
                "You are a job description parser. Extract structured "
                "requirements from the raw job posting text.\n\n"
                "Return JSON with:\n"
                "- required_skills: array of must-have skills\n"
                "- preferred_skills: array of nice-to-have skills\n"
                "- experience_years: minimum years required (integer or null)\n"
                "- responsibilities: array of key responsibilities\n"
                "- education: required education level (string or null)\n"
                "- role_level: JUNIOR / MID / SENIOR / LEAD / PRINCIPAL\n"
                "- cultural_signals: array of culture/values keywords\n\n"
                "Be precise — only include skills explicitly mentioned. "
                "Do not infer skills from responsibilities."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        job_description = state.get("job_description", "")

        if not job_description:
            return [HumanMessage(content="No job description provided.")]

        return [HumanMessage(
            content=f"Parse this job description into structured requirements:\n\n{job_description}"
        )]

    def process_response(self, response, state: dict) -> dict:
        return {"jd_analysis": response.content}
