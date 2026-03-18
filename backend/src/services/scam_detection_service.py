"""
Scam detection service — rule-based job posting analysis.

Provides deterministic red-flag detection for job postings before (optionally)
passing to the ScamDetectorAgent for LLM-powered contextual analysis. The
rule-based layer catches obvious patterns instantly without LLM cost.

Design decisions
----------------
Why rule-based first (not LLM-only):
    Common scam patterns are well-known and deterministic: upfront fees,
    personal email domains, unrealistic salaries. Detecting these with rules
    is instant, free, and 100% reliable. The LLM adds value for nuanced
    analysis (e.g., "this description sounds vague but could be legitimate
    for a stealth startup") that rules can't capture.

Why a scoring system:
    A single risk_score (0-100) with thresholds for LOW/MEDIUM/HIGH/CRITICAL
    is easier for the UI to consume than a bag of boolean flags. Each rule
    contributes a weighted score, and the weights reflect severity.
"""

import re

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Red flag definitions with weights
# ---------------------------------------------------------------------------

_PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "protonmail.com", "mail.com", "yandex.com",
    "rediffmail.com", "live.com",
}

_PAYMENT_KEYWORDS = [
    "registration fee", "processing fee", "training fee",
    "security deposit", "advance payment", "pay to apply",
    "bank details", "wire transfer", "western union",
    "money order", "pay upfront", "refundable deposit",
]

_URGENCY_KEYWORDS = [
    "act now", "limited spots", "apply immediately",
    "urgent hiring", "last date today", "closing soon",
    "don't miss", "once in a lifetime", "guaranteed placement",
]

_VAGUE_ROLE_PATTERNS = [
    r"work from home.*earn",
    r"no experience.*required.*high.*salary",
    r"data entry.*unlimited.*earning",
    r"simple.*task.*high.*pay",
    r"part.?time.*\$?\d{4,}.*per.*week",
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ScamDetectionService:
    """Rule-based scam detection for job postings."""

    def analyze(self, job_data: dict) -> dict:
        """
        Analyze a job posting for scam red flags.

        Args:
            job_data: Dict with keys like title, description, company_name,
                      company_email, salary_min, salary_max, contact_method, etc.

        Returns:
            {
                "risk_score": 0-100,
                "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
                "flags": [{"rule": str, "severity": int, "detail": str}, ...],
                "recommendation": str,
            }
        """
        flags = []

        # Check each rule category
        flags.extend(self._check_email(job_data))
        flags.extend(self._check_payment_keywords(job_data))
        flags.extend(self._check_urgency(job_data))
        flags.extend(self._check_vague_role(job_data))
        flags.extend(self._check_salary_anomaly(job_data))
        flags.extend(self._check_contact_method(job_data))
        flags.extend(self._check_company_info(job_data))

        risk_score = min(100, sum(f["severity"] for f in flags))
        risk_level = self._score_to_level(risk_score)

        recommendation = self._get_recommendation(risk_level, flags)

        logger.info(
            "scam_analysis_complete",
            risk_score=risk_score,
            risk_level=risk_level,
            flag_count=len(flags),
        )

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "flags": flags,
            "recommendation": recommendation,
        }

    def _check_email(self, data: dict) -> list[dict]:
        flags = []
        email = data.get("company_email", "").lower()
        if email:
            domain = email.split("@")[-1] if "@" in email else ""
            if domain in _PERSONAL_EMAIL_DOMAINS:
                flags.append({
                    "rule": "PERSONAL_EMAIL",
                    "severity": 20,
                    "detail": f"Company uses personal email domain: {domain}",
                })
        return flags

    def _check_payment_keywords(self, data: dict) -> list[dict]:
        flags = []
        text = f"{data.get('title', '')} {data.get('description', '')}".lower()
        for keyword in _PAYMENT_KEYWORDS:
            if keyword in text:
                flags.append({
                    "rule": "PAYMENT_REQUEST",
                    "severity": 30,
                    "detail": f"Job mentions payment-related term: '{keyword}'",
                })
                break  # One flag per category is enough
        return flags

    def _check_urgency(self, data: dict) -> list[dict]:
        flags = []
        text = f"{data.get('title', '')} {data.get('description', '')}".lower()
        matches = [kw for kw in _URGENCY_KEYWORDS if kw in text]
        if matches:
            flags.append({
                "rule": "URGENCY_PRESSURE",
                "severity": 15,
                "detail": f"Uses urgency language: {', '.join(matches[:3])}",
            })
        return flags

    def _check_vague_role(self, data: dict) -> list[dict]:
        flags = []
        text = f"{data.get('title', '')} {data.get('description', '')}".lower()
        for pattern in _VAGUE_ROLE_PATTERNS:
            if re.search(pattern, text):
                flags.append({
                    "rule": "VAGUE_ROLE",
                    "severity": 20,
                    "detail": "Job description matches vague/too-good-to-be-true pattern",
                })
                break
        return flags

    def _check_salary_anomaly(self, data: dict) -> list[dict]:
        flags = []
        salary_max = data.get("salary_max", 0)
        salary_min = data.get("salary_min", 0)

        if salary_max > 0 and salary_min > 0:
            ratio = salary_max / salary_min if salary_min > 0 else 0
            if ratio > 5:
                flags.append({
                    "rule": "SALARY_RANGE_EXTREME",
                    "severity": 15,
                    "detail": f"Salary range is suspiciously wide: {salary_min}-{salary_max} (ratio {ratio:.1f}x)",
                })

        return flags

    def _check_contact_method(self, data: dict) -> list[dict]:
        flags = []
        contact = data.get("contact_method", "").lower()
        if contact in ("whatsapp", "telegram", "sms"):
            flags.append({
                "rule": "INFORMAL_CONTACT",
                "severity": 15,
                "detail": f"Primary contact method is {contact} (unusual for legitimate employers)",
            })
        return flags

    def _check_company_info(self, data: dict) -> list[dict]:
        flags = []
        company_name = data.get("company_name", "").strip()
        if not company_name:
            flags.append({
                "rule": "MISSING_COMPANY",
                "severity": 20,
                "detail": "No company name provided",
            })
        elif len(company_name) <= 2:
            flags.append({
                "rule": "SUSPICIOUS_COMPANY_NAME",
                "severity": 10,
                "detail": f"Company name is suspiciously short: '{company_name}'",
            })
        return flags

    @staticmethod
    def _score_to_level(score: int) -> str:
        if score >= 60:
            return "CRITICAL"
        elif score >= 40:
            return "HIGH"
        elif score >= 20:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _get_recommendation(level: str, flags: list[dict]) -> str:
        if level == "CRITICAL":
            return "This posting shows multiple strong scam indicators. We strongly recommend avoiding it."
        elif level == "HIGH":
            return "This posting has concerning red flags. Research the company thoroughly before proceeding."
        elif level == "MEDIUM":
            return "Some caution flags detected. Verify the company and role details before engaging."
        return "No significant red flags detected. Standard due diligence recommended."
