"""
Interview coach agent — conducts adaptive mock interviews with scoring.

Evaluates answers on 4 dimensions (relevance, structure, specificity,
confidence) on a 1-5 scale. Adjusts difficulty based on running score.
When STAR stories are available, coaches the candidate to weave them
into answers.

Uses Claude Sonnet (INTERVIEW_COACHING) for nuanced coaching feedback.
"""

import json

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

INTERVIEW_COACH_PROMPT = """\
You are an adaptive interview coach. You conduct mock interviews, evaluate \
answers on 4 dimensions (relevance, structure, specificity, confidence) on \
a 1-5 scale, and provide actionable feedback. Adjust difficulty based on \
the candidate's running score. When STAR stories are available, coach the \
candidate to weave them into answers. Output JSON with: score_relevance, \
score_structure, score_specificity, score_confidence, feedback, \
improvement_suggestion, next_difficulty.\
"""


class InterviewCoachAgent(BaseAgent):
    """Evaluates interview answers and provides adaptive coaching feedback."""

    def __init__(self) -> None:
        super().__init__(
            name="interview_coach",
            task_type=TaskType.INTERVIEW_COACHING,
            system_prompt=INTERVIEW_COACH_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        current_question = state.get("current_question", "")
        user_answer = state.get("user_answer", "")
        star_stories = state.get("star_stories", "")
        difficulty_level = state.get("difficulty_level", "medium")
        session_scores = state.get("session_scores", [])

        parts = [
            f"## Current Question\n{current_question}",
            f"\n\n## Candidate's Answer\n{user_answer}",
            f"\n\n## Difficulty Level: {difficulty_level}",
        ]

        if star_stories:
            parts.append(f"\n\n## Available STAR Stories\n{star_stories}")

        if session_scores:
            parts.append(f"\n\n## Session Scores So Far\n{session_scores}")

        round_type = state.get("round_type", "")
        company_pattern = state.get("company_pattern", "")

        if round_type == "gd":
            parts.append("\n\n## GD Coaching Mode")
            parts.append("\nEvaluate the candidate's group discussion performance:")
            parts.append("\n- Opening structure and clarity")
            parts.append("\n- Quality and relevance of arguments")
            parts.append("\n- Use of data points and examples")
            parts.append("\n- Balance of perspectives considered")
            parts.append("\n- Summarization and conclusion quality")
        elif round_type == "hr":
            locale = state.get("locale_context", "")
            parts.append("\n\n## HR Round Coaching (India Campus)")
            parts.append("\n- CTC negotiation framing (in-hand vs CTC vs benefits)")
            parts.append("\n- Notice period expectations and negotiation")
            parts.append("\n- Relocation readiness and preferences")
            parts.append("\n- 'Tell me about yourself' structuring")
            if locale:
                parts.append(f"\n\n## Locale Context\n{locale}")
        elif company_pattern:
            try:
                pattern = json.loads(company_pattern)
                criteria = pattern.get("evaluation_criteria", [])
                if criteria:
                    parts.append("\n\n## Company-Specific Evaluation Criteria")
                    for c in criteria:
                        parts.append(f"\n- {c}")
            except (json.JSONDecodeError, TypeError):
                pass

        parts.append(
            "\n\nEvaluate the answer and provide coaching feedback."
        )

        return [HumanMessage(content="".join(parts))]

    def process_response(self, response, state: dict) -> dict:
        return {"evaluation": response.content}
