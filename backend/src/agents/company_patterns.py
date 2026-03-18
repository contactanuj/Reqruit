"""
Company interview patterns — structured data for company-specific coaching.

Known company patterns are hardcoded for MVP. Each pattern defines
question type weights, evaluation criteria, interview stages, and
culture signals. Patterns are serialized to JSON in graph state.
"""

from pydantic import BaseModel

CAMPUS_PLACEMENT_ROUNDS = ["aptitude", "gd", "technical", "hr"]


class CompanyInterviewPattern(BaseModel):
    """Interview pattern data for a known company."""

    company_name: str
    question_weights: dict[str, float]
    evaluation_criteria: list[str]
    interview_stages: list[str]
    culture_signals: str


COMPANY_PATTERNS: dict[str, CompanyInterviewPattern] = {
    "amazon": CompanyInterviewPattern(
        company_name="Amazon",
        question_weights={
            "behavioral": 0.5,
            "technical": 0.3,
            "system_design": 0.15,
            "situational": 0.05,
        },
        evaluation_criteria=[
            "Evaluate against Amazon Leadership Principles",
            "Check for Customer Obsession — does the answer put the customer first?",
            "Check for Ownership — does the candidate take responsibility?",
            "Check for Bias for Action — does the candidate show decisiveness?",
            "Check for Dive Deep — does the candidate show analytical depth?",
            "Check for Deliver Results — does the answer demonstrate measurable outcomes?",
        ],
        interview_stages=["phone_screen", "loop_behavioral", "loop_technical", "bar_raiser"],
        culture_signals="Data-driven, customer-centric, frugal, high ownership culture",
    ),
    "google": CompanyInterviewPattern(
        company_name="Google",
        question_weights={
            "technical": 0.4,
            "system_design": 0.25,
            "behavioral": 0.2,
            "situational": 0.15,
        },
        evaluation_criteria=[
            "Evaluate problem-solving approach and algorithmic thinking",
            "Check for Googleyness — intellectual humility, collaborative spirit",
            "Assess system design scalability and tradeoff analysis",
            "Look for structured problem decomposition",
        ],
        interview_stages=["phone_screen", "onsite_coding", "onsite_system_design", "onsite_behavioral"],
        culture_signals="Innovation-driven, data-informed, collaborative, intellectually curious",
    ),
    "microsoft": CompanyInterviewPattern(
        company_name="Microsoft",
        question_weights={
            "behavioral": 0.35,
            "technical": 0.35,
            "system_design": 0.2,
            "situational": 0.1,
        },
        evaluation_criteria=[
            "Evaluate for Growth Mindset — learning from failure, curiosity",
            "Check for collaboration and inclusive behavior",
            "Assess technical depth with practical application",
            "Look for customer empathy and impact orientation",
        ],
        interview_stages=["phone_screen", "onsite_technical", "onsite_behavioral", "hiring_manager"],
        culture_signals="Growth mindset, inclusive, customer-focused, learn-it-all culture",
    ),
    "tcs": CompanyInterviewPattern(
        company_name="TCS",
        question_weights={
            "aptitude": 0.25,
            "technical": 0.35,
            "behavioral": 0.25,
            "situational": 0.15,
        },
        evaluation_criteria=[
            "Evaluate communication clarity and confidence",
            "Check technical fundamentals relevant to the role",
            "Assess teamwork and adaptability",
            "Look for willingness to learn and relocate",
        ],
        interview_stages=["aptitude", "gd", "technical", "hr"],
        culture_signals="Service-oriented, global delivery, structured campus hiring pipeline",
    ),
    "infosys": CompanyInterviewPattern(
        company_name="Infosys",
        question_weights={
            "aptitude": 0.25,
            "technical": 0.35,
            "behavioral": 0.25,
            "situational": 0.15,
        },
        evaluation_criteria=[
            "Evaluate logical reasoning and problem-solving aptitude",
            "Check programming fundamentals and CS concepts",
            "Assess communication skills and team orientation",
            "Look for alignment with Infosys values",
        ],
        interview_stages=["aptitude", "gd", "technical", "hr"],
        culture_signals="Innovation, learning culture, structured campus hiring",
    ),
}

_DEFAULT_PATTERN = CompanyInterviewPattern(
    company_name="Generic",
    question_weights={
        "behavioral": 0.3,
        "technical": 0.3,
        "situational": 0.2,
        "system_design": 0.2,
    },
    evaluation_criteria=[
        "Evaluate answer relevance to the question asked",
        "Check for STAR structure (Situation, Task, Action, Result)",
        "Assess specificity — concrete examples over generalizations",
        "Evaluate confidence and communication clarity",
    ],
    interview_stages=["behavioral", "technical"],
    culture_signals="",
)


def get_company_pattern(company_name: str) -> CompanyInterviewPattern | None:
    """Look up a company interview pattern by name (case-insensitive)."""
    key = company_name.strip().lower()
    if key in COMPANY_PATTERNS:
        return COMPANY_PATTERNS[key]
    for k, v in COMPANY_PATTERNS.items():
        if k.startswith(key) or key.startswith(k):
            return v
    return None


def get_default_pattern() -> CompanyInterviewPattern:
    """Return the generic fallback pattern."""
    return _DEFAULT_PATTERN
