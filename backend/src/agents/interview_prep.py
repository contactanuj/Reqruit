"""
Interview preparation agents.

- BehavioralQuestionGenerator: generates tailored behavioral questions
- MockInterviewer: evaluates a user's answer to a behavioral question
- MockInterviewSummarizer: summarizes an entire mock session into feedback
"""

import re

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

BEHAVIORAL_QUESTION_PROMPT = """\
You are an expert behavioral interview coach. Given a job description and role \
title, generate 5-8 behavioral interview questions that are highly relevant to \
the role.

For each question, provide a suggested STAR story angle — a brief description \
of the type of experience that would make a strong answer.

Format your response exactly like this:

1. Question: [The behavioral question]
   Angle: [Suggested STAR story angle]

2. Question: [The behavioral question]
   Angle: [Suggested STAR story angle]

Focus on questions that:
- Target the key competencies described in the job description
- Cover a mix of technical, leadership, collaboration, and problem-solving themes
- Use the standard "Tell me about a time when..." or "Describe a situation where..." format
- Are specific enough to elicit detailed STAR responses\
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class BehavioralQuestionGenerator(BaseAgent):
    """
    Generates behavioral interview questions tailored to a job description.

    Reads role_title and job_description from state. Returns a list of
    generated questions, each with a question and suggested_angle field.
    """

    def __init__(self) -> None:
        super().__init__(
            name="behavioral_question_generator",
            task_type=TaskType.INTERVIEW_PREP,
            system_prompt=BEHAVIORAL_QUESTION_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        role_title = state.get("role_title", "")
        job_description = state.get("job_description", "")
        return [
            HumanMessage(
                content=(
                    f"Role: {role_title}\n\n"
                    f"Job Description:\n{job_description}"
                )
            )
        ]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        questions = parse_questions(response.content)
        return {"generated_questions": questions}


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_questions(text: str) -> list[dict]:
    """
    Parse structured question/angle pairs from LLM output.

    Expected format:
        1. Question: Tell me about a time...
           Angle: Leadership under pressure

    Falls back to treating unparsed lines as questions with a generic angle.
    """
    questions = []
    pattern = re.compile(
        r"(?:^|\n)\s*\d+\.\s*Question:\s*(.+?)(?:\n\s*Angle:\s*(.+?))?(?=\n\s*\d+\.|$)",
        re.DOTALL,
    )

    for match in pattern.finditer(text):
        question = match.group(1).strip()
        angle = match.group(2).strip() if match.group(2) else "General behavioral competency"
        if question:
            questions.append({"question": question, "suggested_angle": angle})

    # Fallback: if parsing found nothing, treat non-empty lines as questions
    if not questions:
        for line in text.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("Angle:"):
                # Remove leading numbers like "1. " or "- "
                cleaned = re.sub(r"^\d+\.\s*|^-\s*", "", line).strip()
                if cleaned:
                    questions.append(
                        {"question": cleaned, "suggested_angle": "General behavioral competency"}
                    )

    return questions


# ---------------------------------------------------------------------------
# Mock Interviewer — per-question feedback
# ---------------------------------------------------------------------------

MOCK_INTERVIEWER_PROMPT = """\
You are an experienced hiring manager conducting a behavioral interview. \
You have just asked the candidate a question and they have provided their answer.

Evaluate the answer using the STAR method (Situation, Task, Action, Result). \
Provide constructive feedback and a score from 1 to 10.

Format your response exactly like this:

Score: [1-10]
Feedback: [Your detailed feedback covering strengths, areas for improvement, \
and suggestions for a stronger answer]\
"""


class MockInterviewer(BaseAgent):
    """
    Evaluates a user's answer to a behavioral interview question.

    Reads question and user_answer from state. Returns feedback and score.
    """

    def __init__(self) -> None:
        super().__init__(
            name="mock_interviewer",
            task_type=TaskType.MOCK_INTERVIEW,
            system_prompt=MOCK_INTERVIEWER_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        question = state.get("question", "")
        user_answer = state.get("user_answer", "")
        return [
            HumanMessage(
                content=(
                    f"Question: {question}\n\n"
                    f"Candidate's Answer:\n{user_answer}"
                )
            )
        ]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        return parse_interviewer_feedback(response.content)


def parse_interviewer_feedback(text: str) -> dict:
    """
    Parse score and feedback from MockInterviewer output.

    Expected format:
        Score: 7
        Feedback: Good use of the STAR method...
    """
    score = None
    feedback = text.strip()

    score_match = re.search(r"Score:\s*(\d+)", text)
    if score_match:
        score = min(10, max(1, int(score_match.group(1))))

    feedback_match = re.search(r"Feedback:\s*(.+)", text, re.DOTALL)
    if feedback_match:
        feedback = feedback_match.group(1).strip()

    return {"score": score, "feedback": feedback}


# ---------------------------------------------------------------------------
# Mock Interview Summarizer — overall session feedback
# ---------------------------------------------------------------------------

MOCK_SUMMARIZER_PROMPT = """\
You are an interview coach reviewing a completed mock interview session. \
You will receive a list of questions, the candidate's answers, and per-question \
feedback with scores.

Provide an overall assessment including:
1. Key strengths demonstrated across all answers
2. Common areas for improvement
3. Specific recommendations for the next interview
4. An overall score from 0 to 100

Format your response exactly like this:

Overall Score: [0-100]
Summary: [Your comprehensive assessment]\
"""


class MockInterviewSummarizer(BaseAgent):
    """
    Summarizes a completed mock interview session.

    Reads session_transcript from state. Returns overall_feedback and overall_score.
    """

    def __init__(self) -> None:
        super().__init__(
            name="mock_interview_summarizer",
            task_type=TaskType.MOCK_INTERVIEW,
            system_prompt=MOCK_SUMMARIZER_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        transcript = state.get("session_transcript", "")
        return [
            HumanMessage(content=f"Mock Interview Transcript:\n\n{transcript}")
        ]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        return parse_summary_feedback(response.content)


def parse_summary_feedback(text: str) -> dict:
    """
    Parse overall score and summary from MockInterviewSummarizer output.

    Expected format:
        Overall Score: 72
        Summary: The candidate showed strong...
    """
    overall_score = None
    overall_feedback = text.strip()

    score_match = re.search(r"Overall Score:\s*(\d+)", text)
    if score_match:
        overall_score = min(100, max(0, int(score_match.group(1))))

    summary_match = re.search(r"Summary:\s*(.+)", text, re.DOTALL)
    if summary_match:
        overall_feedback = summary_match.group(1).strip()

    return {"overall_score": overall_score, "overall_feedback": overall_feedback}
