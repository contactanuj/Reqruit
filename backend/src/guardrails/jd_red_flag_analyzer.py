"""
JDRedFlagAnalyzer — rule-based red flag detection for job descriptions.

Uses regex and keyword matching to detect universal and India-specific scam
patterns. Not an LLM agent — deterministic, instant, free.
"""

import re

import structlog

from src.services.trust.models import RedFlag

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

_FEE_PATTERNS = [
    r"registration\s+fee", r"processing\s+fee", r"training\s+fee",
    r"security\s+deposit", r"advance\s+payment", r"pay\s+to\s+apply",
    r"payment\s+required", r"registration\s+charge", r"refundable\s+deposit",
    r"pay\s+upfront",
]

_TELEGRAM_ONLY_PATTERNS = [
    r"(?:contact|reach|message|apply)\s+(?:us\s+)?(?:on|via|through)\s+telegram",
    r"telegram\s+only",
]

_VAGUE_WFH_PATTERNS = [
    r"work\s+from\s+home.*(?:no\s+experience|earn|unlimited)",
    r"(?:no\s+experience).*(?:high\s+(?:salary|pay|income))",
    r"simple\s+task.*high\s+pay",
    r"data\s+entry.*unlimited.*earning",
    r"part.?time.*\$?\d{4,}.*per.*week",
]

_URGENCY_PATTERNS = [
    r"immediate\s+(?:start|joining|joiner)",
    r"join\s+(?:today|tomorrow|immediately)",
    r"(?:last\s+date|deadline)\s+(?:is\s+)?today",
    r"limited\s+(?:spots|seats|vacancies)",
    r"act\s+now",
    r"don'?t\s+miss",
]

# India-specific
_PLACEMENT_FEE_PATTERNS = [
    r"placement\s+fee", r"consultancy\s+(?:fee|charge)",
    r"(?:pay|deposit).*(?:before|for)\s+(?:placement|joining)",
    r"service\s+charge.*candidate",
]

_WHATSAPP_ONLY_PATTERNS = [
    r"(?:contact|reach|apply|send\s+(?:your\s+)?(?:resume|cv))\s+(?:us\s+)?(?:on|via|through)\s+whatsapp",
    r"whatsapp\s+only",
]


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class JDRedFlagAnalyzer:
    """Rule-based job description red flag detection."""

    def analyze(self, jd_text: str, locale: str = "US") -> list[RedFlag]:
        """Analyze a JD for universal red flags, plus India-specific if locale is IN."""
        text = jd_text.lower()
        flags: list[RedFlag] = []

        flags.extend(self._check_fee_demands(text))
        flags.extend(self._check_telegram_only(text))
        flags.extend(self._check_vague_wfh(text))
        flags.extend(self._check_urgency_pressure(text))
        flags.extend(self._check_above_market_salary(text))

        if locale.upper() == "IN":
            flags.extend(self._analyze_india_specific(text))

        logger.debug(
            "jd_red_flag_analysis",
            flag_count=len(flags),
            locale=locale,
        )
        return flags

    def _check_fee_demands(self, text: str) -> list[RedFlag]:
        for pattern in _FEE_PATTERNS:
            if re.search(pattern, text):
                return [RedFlag(
                    category="UPFRONT_FEE",
                    severity="HIGH_RISK",
                    explanation="Job posting demands upfront payment or fees — a strong scam indicator",
                )]
        return []

    def _check_telegram_only(self, text: str) -> list[RedFlag]:
        for pattern in _TELEGRAM_ONLY_PATTERNS:
            if re.search(pattern, text):
                return [RedFlag(
                    category="TELEGRAM_ONLY",
                    severity="MEDIUM_RISK",
                    explanation="Communication restricted to Telegram — unusual for legitimate employers",
                )]
        return []

    def _check_vague_wfh(self, text: str) -> list[RedFlag]:
        for pattern in _VAGUE_WFH_PATTERNS:
            if re.search(pattern, text):
                return [RedFlag(
                    category="VAGUE_WFH",
                    severity="HIGH_RISK",
                    explanation="Vague 'work from home' posting with unrealistic promises — common scam pattern",
                )]
        return []

    def _check_urgency_pressure(self, text: str) -> list[RedFlag]:
        for pattern in _URGENCY_PATTERNS:
            if re.search(pattern, text):
                return [RedFlag(
                    category="URGENCY_PRESSURE",
                    severity="MEDIUM_RISK",
                    explanation="Posting uses high-pressure urgency tactics to rush applicants",
                )]
        return []

    def _check_above_market_salary(self, text: str) -> list[RedFlag]:
        # Detect salary claims that look too good to be true
        match = re.search(r"(?:\$|₹|rs\.?|inr)\s*([\d,]+)\s*(?:per|/)\s*(?:month|hr|hour)", text)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                amount = int(amount_str)
                # Flag hourly > $500/hr or monthly > $50,000 or ₹10,00,000
                if ("$" in text[:match.start() + 5] and amount > 500 and "hour" in text[match.start():match.end() + 10]) or \
                   ("$" in text[:match.start() + 5] and amount > 50000 and "month" in text[match.start():match.end() + 10]) or \
                   (any(c in text[:match.start() + 5] for c in ("₹", "rs", "inr")) and amount > 1000000):
                    return [RedFlag(
                        category="ABOVE_MARKET_SALARY",
                        severity="MEDIUM_RISK",
                        explanation=f"Advertised compensation ({amount_str}) appears significantly above market rates",
                    )]
            except ValueError:
                pass
        return []

    def _analyze_india_specific(self, text: str) -> list[RedFlag]:
        """India-specific scam patterns."""
        flags: list[RedFlag] = []

        # Placement agency fee (illegal in India)
        for pattern in _PLACEMENT_FEE_PATTERNS:
            if re.search(pattern, text):
                flags.append(RedFlag(
                    category="PLACEMENT_FEE_ILLEGAL",
                    severity="HIGH_RISK",
                    explanation="Placement agency charging candidates is illegal under Indian law",
                ))
                break

        # WhatsApp-only recruitment
        for pattern in _WHATSAPP_ONLY_PATTERNS:
            if re.search(pattern, text):
                flags.append(RedFlag(
                    category="WHATSAPP_ONLY",
                    severity="MEDIUM_RISK",
                    explanation="Recruitment conducted exclusively via WhatsApp — unusual for legitimate companies in India",
                ))
                break

        return flags
