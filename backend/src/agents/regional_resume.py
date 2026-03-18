"""
RegionalResumeAgent — market-specific resume formatting guidance.

This agent takes the user's resume content and a target market's resume
conventions (from MarketConfig) and provides specific guidance on how to
format the resume for that market. It covers layout, sections to include/
exclude, page length, photo requirements, and cultural expectations.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class RegionalResumeAgent(BaseAgent):
    """Provides market-specific resume formatting guidance."""

    def __init__(self) -> None:
        super().__init__(
            name="regional_resume",
            task_type=TaskType.REGIONAL_RESUME,
            system_prompt=(
                "You are a resume formatting expert with deep knowledge of regional "
                "hiring conventions. Given the user's resume content and a target market's "
                "resume conventions, provide specific, actionable guidance on:\n"
                "1. Sections to include or remove (photo, DOB, declaration, etc.)\n"
                "2. Optimal page length and layout for the market\n"
                "3. How to present compensation expectations if required\n"
                "4. Language and tone adjustments for the target culture\n"
                "5. Any market-specific formatting requirements\n\n"
                "Be specific to the target market. Reference the conventions data provided."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        """Build messages with resume content and market conventions."""
        resume_content = state.get("resume_content", "")
        resume_conventions = state.get("resume_conventions", {})
        target_market = state.get("target_market", "")
        cultural_context = state.get("cultural_context", {})

        context_parts = []
        if target_market:
            context_parts.append(f"Target Market: {target_market}")
        if resume_conventions:
            context_parts.append(f"Resume Conventions: {json.dumps(resume_conventions, default=str)}")
        if cultural_context:
            context_parts.append(f"Cultural Context: {json.dumps(cultural_context, default=str)}")
        if resume_content:
            context_parts.append(f"Resume Content:\n{resume_content}")

        content = "\n\n".join(context_parts) if context_parts else "No context provided."
        return [HumanMessage(content=content)]

    def process_response(self, response, state: dict) -> dict:
        """Return the formatting guidance."""
        return {"resume_guidance": response.content}
