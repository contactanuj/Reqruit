"""
State definition for the onboarding workflow.

Tracks plan generation, coaching sessions, and progress across
the 30-60-90 day onboarding graph nodes.
"""

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class OnboardingState(TypedDict):
    """
    Full state for the onboarding workflow.

    Attributes:
        messages: Append-only conversation history for LangGraph.
        company_name: Target company.
        role_title: Role being onboarded into.
        skill_gaps: Identified skill gaps from SkillsProfile.
        plan: Generated onboarding plan data (milestones dict).
        jd_text: Raw job description text.
        coaching_query: User's coaching question.
        coaching_response: Agent's coaching response.
        feedback: User feedback for plan revision.
        status: Workflow lifecycle stage.
    """

    messages: Annotated[list, add_messages]
    company_name: str
    role_title: str
    skill_gaps: list[dict]
    plan: dict
    jd_text: str
    coaching_query: str
    coaching_response: str
    feedback: str
    locale: str
    status: str
