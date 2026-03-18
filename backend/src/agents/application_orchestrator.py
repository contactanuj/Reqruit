"""
Application orchestrator agent — decides optimal application strategy.

Given a JD analysis, fit assessment, and the candidate's skills profile,
the orchestrator determines which resume sections to highlight, what tone
for the cover letter, and key differentiators. For Indian market applications,
includes Naukri keyword optimization and expected salary positioning.

Uses Claude Sonnet (APPLICATION_ORCHESTRATION) for creative strategy decisions.
"""

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

APPLICATION_ORCHESTRATOR_PROMPT = """\
You are an expert application strategist. Given a job description analysis \
and the candidate's skills profile, you decide the optimal application \
strategy: which resume sections to highlight, what tone for the cover letter, \
and key differentiators. For Indian market applications, include Naukri \
keyword optimization and expected salary positioning.

Output structured JSON with: recommended_resume_blocks, cover_letter_tone, \
key_differentiators, platform_specific_notes, micro_pitch (2-3 sentence \
elevator pitch).\
"""


class ApplicationOrchestratorAgent(BaseAgent):
    """Decides the optimal application strategy for a given job."""

    def __init__(self) -> None:
        super().__init__(
            name="application_orchestrator",
            task_type=TaskType.APPLICATION_ORCHESTRATION,
            system_prompt=APPLICATION_ORCHESTRATOR_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        jd_analysis = state.get("jd_analysis", "")
        fit_analysis = state.get("fit_analysis", "")
        skills_summary = state.get("skills_summary", "")
        locale_context = state.get("locale_context", "")
        resume_blocks = state.get("relevant_resume_blocks", "")

        parts = [
            "## JD Analysis\n", jd_analysis,
            "\n\n## Fit Analysis\n", fit_analysis,
            "\n\n## Skills Summary\n", skills_summary,
        ]

        if locale_context:
            parts.extend(["\n\n## Locale Context\n", locale_context])

        if resume_blocks:
            parts.extend(["\n\n## Available Resume Blocks\n", resume_blocks])

        parts.append(
            "\n\nDecide the optimal application strategy for this candidate."
        )

        return [HumanMessage(content="".join(parts))]

    def process_response(self, response, state: dict) -> dict:
        return {"application_strategy": response.content}
