"""
State definition for the application assembly workflow.

Tracks the full pipeline from JD decoding through fit analysis, resume block
selection, tailoring, cover letter/micro-pitch generation, and human review.
"""

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ApplicationAssemblyState(TypedDict):
    """
    Full state for the application assembly workflow.

    Attributes:
        messages: Append-only conversation history.
        job_id: The target job's document ID.
        job_url: URL of the job posting (optional, alternative to jd_text).
        jd_text: Raw job description text.
        resume_text: The user's resume content (plain text).
        job_description: Alias/copy of jd_text for agent compatibility.
        decoded_jd: Structured output from JDDecoder (required_skills, etc.).
        fit_analysis: Output from FitScorer (scores 0-100).
        skills_summary: From SkillsProfile.
        locale_context: From MarketConfig.
        selected_resume_blocks: Resume blocks selected for tailoring.
        application_strategy: Output from ApplicationOrchestrator.
        tailored_resume: Selected/reordered resume blocks.
        cover_letter: Generated cover letter.
        micro_pitch: 2-3 sentence elevator pitch.
        feedback: Human review feedback.
        status: Workflow lifecycle stage.
        application_id: The Application document ID.
        thread_id: LangGraph thread ID for checkpoint recovery.
    """

    messages: Annotated[list, add_messages]
    job_id: str
    job_url: str
    jd_text: str
    resume_text: str
    job_description: str
    decoded_jd: str
    fit_analysis: str
    skills_summary: str
    locale_context: str
    selected_resume_blocks: str
    application_strategy: str
    tailored_resume: str
    cover_letter: str
    micro_pitch: str
    feedback: str
    status: str
    resume_block_fallback: bool
    star_stories_available: bool
    locale_defaulted: bool
    keyword_optimization: str
    application_id: str
    thread_id: str
