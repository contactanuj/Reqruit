"""
ScamDetectorAgent — LLM-powered trust verification for companies and recruiters.

Uses GPT-4o-mini (temp=0.0) for deterministic multi-signal verification:
company domain analysis, recruiter email-domain matching, LinkedIn consistency,
and MCA CIN format validation (India).

Phase 4 replaces Phase 0's SCAM_INTELLIGENCE-based version with structured
TrustScore output for the trust verification pipeline.
"""

import json

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

logger = structlog.get_logger()

SCAM_DETECTOR_PROMPT = """\
You are a trust verification analyst for job postings. Analyze the provided \
company and recruiter information for legitimacy signals.

Perform multi-signal verification:
1. Company domain analysis — is the company name consistent with common \
   legitimate companies? Does the registration number (if provided) follow \
   valid MCA CIN format (India: 21 alphanumeric characters)?
2. Recruiter email-domain match — does the email domain match the company? \
   Personal email domains (gmail, yahoo, hotmail, etc.) are a risk signal.
3. LinkedIn consistency — if a LinkedIn URL is provided, does it appear to \
   belong to someone at the stated company?
4. Job URL analysis — does the job URL domain look legitimate?

Return a JSON object with these exact keys:
{
  "company_verification_score": <float 0-100>,
  "recruiter_verification_score": <float 0-100>,
  "posting_freshness_score": <float 0-100>,
  "red_flag_count": <int>,
  "overall_trust_score": <float 0-100>,
  "risk_category": "VERIFIED" | "LIKELY_SAFE" | "UNCERTAIN" | "SUSPICIOUS" | "SCAM_LIKELY",
  "risk_signals": [
    {"signal_type": "<type>", "description": "<detail>", "severity": "low"|"medium"|"high"}
  ]
}

Be precise and deterministic. When information is missing, lower the score \
and note the gap as a risk signal. Never fabricate external lookups.\
"""


class ScamDetectorAgent(BaseAgent):
    """LLM-powered trust verification for companies and recruiters."""

    def __init__(self) -> None:
        super().__init__(
            name="scam_detector",
            task_type=TaskType.SCAM_DETECTION,
            system_prompt=SCAM_DETECTOR_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        parts = [f"Company name: {state.get('company_name', 'Not provided')}"]

        if reg := state.get("company_registration_number"):
            parts.append(f"Company registration number: {reg}")

        if email := state.get("recruiter_email"):
            parts.append(f"Recruiter email: {email}")

        if linkedin := state.get("recruiter_linkedin_url"):
            parts.append(f"Recruiter LinkedIn: {linkedin}")

        if job_url := state.get("job_url"):
            parts.append(f"Job URL: {job_url}")

        return [HumanMessage(content="\n".join(parts))]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content

        # Strip markdown fences if present
        if "```json" in content:
            content = content.split("```json", 1)[1]
            if "```" in content:
                content = content.split("```", 1)[0]
        elif "```" in content:
            content = content.split("```", 1)[1]
            if "```" in content:
                content = content.split("```", 1)[0]

        try:
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict):
                return {
                    "company_verification_score": float(parsed.get("company_verification_score", 0)),
                    "recruiter_verification_score": float(parsed.get("recruiter_verification_score", 0)),
                    "posting_freshness_score": float(parsed.get("posting_freshness_score", 0)),
                    "red_flag_count": int(parsed.get("red_flag_count", 0)),
                    "overall_trust_score": float(parsed.get("overall_trust_score", 50)),
                    "risk_category": parsed.get("risk_category", "UNCERTAIN"),
                    "risk_signals": parsed.get("risk_signals", []),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Fallback: return UNCERTAIN with raw content as signal
        logger.warning("scam_detector_parse_failed", raw_length=len(response.content))
        return {
            "company_verification_score": 0.0,
            "recruiter_verification_score": 0.0,
            "posting_freshness_score": 0.0,
            "red_flag_count": 0,
            "overall_trust_score": 50.0,
            "risk_category": "UNCERTAIN",
            "risk_signals": [
                {"signal_type": "PARSE_FAILURE", "description": "Could not parse LLM response", "severity": "medium"}
            ],
        }


scam_detector_agent = ScamDetectorAgent()
