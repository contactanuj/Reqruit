"""
State definition for the skills analysis workflow.

This workflow mines achievements from a user's resume, analyzes skills,
and produces a structured SkillsProfile. The human_review step lets the
user verify and edit the extracted data before it's saved.
"""

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class SkillsAnalysisState(TypedDict):
    """
    Full state for the skills analysis workflow.

    Attributes:
        messages: Append-only conversation history across all nodes.
        resume_text: The user's resume content (plain text).
        work_history: Additional work history details (optional).
        existing_achievements: Previously extracted achievements to avoid duplicates.
        mined_achievements: Raw achievement extraction from AchievementMiner.
        skills_analysis: Structured skills inventory from SkillsAnalyst.
        feedback: User feedback from the human review step.
        status: Workflow lifecycle stage. One of:
            - "pending": initial state
            - "mining": AchievementMiner is processing
            - "analyzing": SkillsAnalyst is processing
            - "reviewing": paused at human_review
            - "revision_requested": user asked for changes
            - "approved": user approved, workflow complete
    """

    messages: Annotated[list, add_messages]
    resume_text: str
    work_history: str
    existing_achievements: list
    mined_achievements: str
    skills_analysis: str
    feedback: str
    status: str
