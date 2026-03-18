"""
Naukri keyword optimizer — checks JD keywords for presence in tailored resume.

Pure Python string matching. No LLM calls. Used for Indian market
(Naukri.com) keyword optimization post-processing.
"""

import json
import re
from dataclasses import dataclass, field


@dataclass
class KeywordReport:
    """Result of keyword presence analysis."""

    present_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    coverage_pct: float = 0.0
    suggestions: list[str] = field(default_factory=list)


def extract_jd_keywords(jd_analysis: str) -> list[str]:
    """Extract top keywords from decoded JD analysis JSON."""
    try:
        parsed = json.loads(jd_analysis)
        required = parsed.get("required_skills", [])
        preferred = parsed.get("preferred_skills", [])
        return required + preferred
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []


def optimize_for_naukri(jd_keywords: list[str], tailored_resume: str) -> KeywordReport:
    """Check top 10 JD keywords for presence in the tailored resume."""
    top_keywords = jd_keywords[:10]

    if not top_keywords:
        return KeywordReport()

    resume_lower = tailored_resume.lower()

    present = []
    missing = []
    for kw in top_keywords:
        if re.search(re.escape(kw.lower()), resume_lower):
            present.append(kw)
        else:
            missing.append(kw)

    coverage = round(len(present) / len(top_keywords) * 100, 1)
    suggestions = [f"Consider adding '{kw}' to your resume" for kw in missing]

    return KeywordReport(
        present_keywords=present,
        missing_keywords=missing,
        coverage_pct=coverage,
        suggestions=suggestions,
    )
