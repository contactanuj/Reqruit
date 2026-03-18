"""
CulturalCoachAgent — culture-calibrated interview and workplace guidance.

This agent provides coaching on cultural norms relevant to job seeking,
interviewing, and workplace behavior in a target market. It draws on
MarketConfig's cultural context to give market-specific advice on formality,
communication style, decision-making patterns, and interview expectations.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class CulturalCoachAgent(BaseAgent):
    """Provides culture-calibrated career and interview coaching."""

    def __init__(self) -> None:
        super().__init__(
            name="cultural_coach",
            task_type=TaskType.CULTURAL_COACHING,
            system_prompt=(
                "You are a cross-cultural career coach specializing in helping "
                "professionals navigate hiring and workplace norms across different "
                "markets. Given the target market's cultural context and the user's "
                "background, provide coaching on:\n"
                "1. Interview etiquette and expectations for the target market\n"
                "2. Communication style (formality, directness, follow-up norms)\n"
                "3. Salary negotiation customs and expectations\n"
                "4. Workplace culture and team dynamics\n"
                "5. Common cultural missteps to avoid\n\n"
                "Be respectful of all cultures. Provide specific, actionable advice "
                "rather than stereotypes. Reference the cultural context data provided."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        """Build messages with cultural context."""
        target_market = state.get("target_market", "")
        cultural_context = state.get("cultural_context", {})
        hiring_process = state.get("hiring_process", {})
        user_background = state.get("user_background", "")
        specific_concerns = state.get("specific_concerns", "")

        context_parts = []
        if target_market:
            context_parts.append(f"Target Market: {target_market}")
        if cultural_context:
            context_parts.append(f"Cultural Context: {json.dumps(cultural_context, default=str)}")
        if hiring_process:
            context_parts.append(f"Hiring Process: {json.dumps(hiring_process, default=str)}")
        if user_background:
            context_parts.append(f"User Background: {user_background}")
        if specific_concerns:
            context_parts.append(f"Specific Concerns: {specific_concerns}")

        content = "\n\n".join(context_parts) if context_parts else "No context provided."
        return [HumanMessage(content=content)]

    def process_response(self, response, state: dict) -> dict:
        """Return the cultural coaching response."""
        return {"cultural_coaching": response.content}
