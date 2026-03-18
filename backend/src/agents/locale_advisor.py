"""
LocaleAdvisorAgent — routes queries with market-aware context injection.

This agent enriches user queries with relevant market data, helping
downstream agents produce locale-appropriate output. It selects the
most relevant portions of MarketConfig for the specific query context.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType


class LocaleAdvisorAgent(BaseAgent):
    """Market-aware career advisor that provides locale context."""

    def __init__(self) -> None:
        super().__init__(
            name="locale_advisor",
            task_type=TaskType.LOCALE_ADVISORY,
            system_prompt=(
                "You are a market-aware career advisor. Given the user's market "
                "context (primary market, target markets, locale profile) and their "
                "query, provide advice that is specifically calibrated to the relevant "
                "markets. Reference specific market norms, compensation structures, "
                "hiring practices, and cultural expectations. Be concise and actionable."
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        """Build messages with market context and user query."""
        market_config = state.get("market_config", {})
        locale_profile = state.get("user_locale_profile", {})
        query = state.get("query", "")

        context_parts = []
        if market_config:
            context_parts.append(f"Market Config: {json.dumps(market_config, default=str)}")
        if locale_profile:
            context_parts.append(f"User Locale Profile: {json.dumps(locale_profile, default=str)}")

        content = "\n".join(context_parts) + f"\n\nUser Query: {query}"
        return [HumanMessage(content=content)]

    def process_response(self, response, state: dict) -> dict:
        """Return the advisor's response."""
        return {"advisor_response": response.content}
