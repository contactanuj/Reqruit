"""
Question predictor agent — predicts likely interview questions for a role.

Considers role requirements, company culture signals, industry norms,
and interview stage. For Indian campus placements, includes aptitude
and group discussion topics.

Uses GPT-4o-mini (QUESTION_PREDICTION) for deterministic extraction.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

QUESTION_PREDICTOR_PROMPT = """\
You predict the 10 most likely interview questions for a specific role at \
a specific company. Consider: role requirements from JD, company culture \
signals, industry norms, and interview stage. For Indian campus placements, \
include aptitude and group discussion topics. Output JSON array with: \
question_text, question_type (behavioral/technical/situational/system_design/aptitude), \
difficulty (easy/medium/hard), confidence (high/medium/low), suggested_preparation.\
"""


class QuestionPredictorAgent(BaseAgent):
    """Predicts likely interview questions for a specific role and company."""

    def __init__(self) -> None:
        super().__init__(
            name="question_predictor",
            task_type=TaskType.QUESTION_PREDICTION,
            system_prompt=QUESTION_PREDICTOR_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        company_name = state.get("company_name", "")
        role_title = state.get("role_title", "")
        jd_analysis = state.get("jd_analysis", "")
        company_research = state.get("company_research", "")
        locale_context = state.get("locale_context", "")

        parts = [
            f"## Company: {company_name}\n",
            f"## Role: {role_title}\n",
            f"\n## JD Analysis\n{jd_analysis}",
        ]

        if company_research:
            parts.append(f"\n\n## Company Research\n{company_research}")

        if locale_context:
            parts.append(f"\n\n## Locale Context\n{locale_context}")

        company_pattern = state.get("company_pattern", "")
        if company_pattern:
            try:
                pattern = json.loads(company_pattern)
                weights = pattern.get("question_weights", {})
                criteria = pattern.get("evaluation_criteria", [])
                parts.append("\n\n## Company Interview Pattern")
                parts.append(f"\nQuestion type weights: {json.dumps(weights)}")
                parts.append(f"\nEvaluation criteria: {json.dumps(criteria)}")
                culture = pattern.get("culture_signals", "")
                if culture:
                    parts.append(f"\nCulture: {culture}")
            except (json.JSONDecodeError, TypeError):
                pass

        round_type = state.get("round_type", "")
        if round_type and round_type not in ("behavioral", ""):
            parts.append(f"\n\n## Round Type: {round_type}")
            parts.append(f"\nGenerate questions appropriate for the {round_type} round.")

        parts.append(
            "\n\nPredict the 10 most likely interview questions for this role."
        )

        return [HumanMessage(content="".join(parts))]

    def process_response(self, response, state: dict) -> dict:
        content = response.content
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return {"predicted_questions": json.dumps(parsed)}
        except (json.JSONDecodeError, TypeError):
            pass
        return {"predicted_questions": content}
