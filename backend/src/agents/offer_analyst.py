"""
OfferAnalystAgent — parses offer text into structured compensation components.

Takes raw offer text (pasted offer letter, CTC breakdown, or compensation
details) and produces a structured JSON breakdown with components, totals,
confidence levels, and suggestions for missing information.

Uses GPT-4o-mini with temp=0.0 for deterministic structured JSON output.
"""

import json
import re

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

logger = structlog.get_logger()


class OfferAnalystAgent(BaseAgent):
    """Parses offer text into structured compensation components."""

    def __init__(self) -> None:
        super().__init__(
            name="offer_analyst",
            task_type=TaskType.OFFER_ANALYSIS,
            system_prompt=(
                "You are a compensation analyst that parses job offer text into "
                "structured components. Given offer text, extract every compensation "
                "component and return a JSON object with this exact structure:\n\n"
                "{\n"
                '  "components": [\n'
                '    {"name": "component_name", "value": numeric_value, '
                '"currency": "INR|USD", "frequency": "annual|monthly|one_time", '
                '"is_guaranteed": true|false, "confidence": "high|medium|low"}\n'
                "  ],\n"
                '  "total_comp_annual": numeric_total,\n'
                '  "missing_fields": ["field1", "field2"],\n'
                '  "suggestions": ["What to ask employer for field1"]\n'
                "}\n\n"
                "Rules:\n"
                "- For India offers with CTC: decompose into basic, HRA, special "
                "allowance, PF, gratuity, variable pay, ESOPs, insurance\n"
                "- For US offers: extract base salary, RSU/stock options, annual bonus, "
                "signing bonus, 401k match, insurance value, PTO value\n"
                "- Mark components as is_guaranteed=false if they are variable/performance-based\n"
                "- Set confidence='low' for fields you had to estimate or couldn't find\n"
                "- List missing fields and suggest what to ask the employer\n"
                "- Return ONLY valid JSON, no markdown fences or extra text\n"
                "- All monetary values should be numbers, not strings"
            ),
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        """Build messages with offer text and locale context."""
        offer_text = state.get("offer_text", "")
        company_name = state.get("company_name", "")
        role_title = state.get("role_title", "")
        locale_market = state.get("locale_market", "")

        content = (
            f"Company: {company_name}\n"
            f"Role: {role_title}\n"
            f"Market/Locale: {locale_market}\n\n"
            f"Offer text:\n{offer_text}"
        )
        return [HumanMessage(content=content)]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        """Parse LLM JSON response into structured offer data."""
        raw = response.content.strip()

        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "offer_analyst_json_parse_failed",
                raw_length=len(raw),
            )
            return {
                "components": [],
                "total_comp_annual": 0.0,
                "missing_fields": [],
                "suggestions": ["Could not parse offer. Please try rephrasing."],
            }

        return {
            "components": data.get("components", []),
            "total_comp_annual": data.get("total_comp_annual", 0.0),
            "missing_fields": data.get("missing_fields", []),
            "suggestions": data.get("suggestions", []),
        }
