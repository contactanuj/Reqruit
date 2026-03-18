"""
Market signal service — classifies and scores market intelligence signals.

Pure-Python deterministic service for signal classification, confidence
scoring, and relevance filtering. No LLM calls.
"""

from pydantic import BaseModel, Field


class SignalClassification(BaseModel):
    """Classification result for a market signal."""

    signal_type: str
    severity: str
    confidence: float
    relevance_score: float  # 0-100 relevance to user's context
    summary: str


class CompanyTrajectory(BaseModel):
    """Predicted trajectory for a company based on market signals."""

    company_name: str
    trajectory: str  # growing, stable, declining, restructuring
    confidence: float
    signals: list[str] = Field(default_factory=list)
    recommendation: str = ""


class DisruptionIndicator(BaseModel):
    """An industry disruption signal."""

    industry: str
    disruption_type: str  # technology, regulation, market_shift, consolidation
    impact_level: str  # low, medium, high
    description: str
    affected_roles: list[str] = Field(default_factory=list)
    timeline: str = ""  # near_term, medium_term, long_term


# Signal type weights for relevance scoring
_TYPE_WEIGHTS = {
    "hiring_trend": 1.0,
    "layoff_alert": 1.5,
    "skill_demand": 1.2,
    "compensation_shift": 1.0,
    "disruption": 1.3,
}

# Severity multipliers
_SEVERITY_MULTIPLIERS = {
    "info": 0.5,
    "warning": 1.0,
    "critical": 1.5,
}


def classify_signal(
    title: str,
    description: str,
    industry: str = "",
    region: str = "",
) -> SignalClassification:
    """Classify a market signal based on content analysis."""
    title_lower = title.lower()
    desc_lower = description.lower()
    combined = f"{title_lower} {desc_lower}"

    # Determine signal type
    if any(w in combined for w in ("layoff", "restructur", "downsiz", "rif", "job cut")):
        signal_type = "layoff_alert"
        severity = "critical"
    elif any(w in combined for w in ("hiring", "recruit", "talent", "openings", "growth")):
        signal_type = "hiring_trend"
        severity = "info"
    elif any(w in combined for w in ("salary", "compensation", "pay raise", "pay cut")):
        signal_type = "compensation_shift"
        severity = "warning"
    elif any(w in combined for w in ("skill", "demand", "trending", "emerging")):
        signal_type = "skill_demand"
        severity = "info"
    elif any(w in combined for w in ("disruption", "ai replac", "automat", "transform")):
        signal_type = "disruption"
        severity = "warning"
    else:
        signal_type = "hiring_trend"
        severity = "info"

    # Calculate confidence based on specificity
    confidence = 0.5
    if industry:
        confidence += 0.2
    if region:
        confidence += 0.1
    if len(description) > 100:
        confidence += 0.1
    confidence = min(confidence, 1.0)

    return SignalClassification(
        signal_type=signal_type,
        severity=severity,
        confidence=confidence,
        relevance_score=confidence * 100,
        summary=title[:200],
    )


def score_signal_relevance(
    signal_industry: str,
    signal_region: str,
    user_industry: str,
    user_region: str,
    signal_type: str,
) -> float:
    """Score how relevant a signal is to a specific user's context (0-100)."""
    score = 30.0  # base relevance

    if signal_industry and user_industry:
        if signal_industry.lower() == user_industry.lower():
            score += 40.0
        elif _industries_related(signal_industry, user_industry):
            score += 20.0

    if signal_region and user_region:
        if signal_region.lower() == user_region.lower():
            score += 20.0

    weight = _TYPE_WEIGHTS.get(signal_type, 1.0)
    score *= weight

    return min(score, 100.0)


def predict_company_trajectory(
    company_name: str,
    signals: list[dict],
) -> CompanyTrajectory:
    """Predict company trajectory from accumulated signals."""
    if not signals:
        return CompanyTrajectory(
            company_name=company_name,
            trajectory="stable",
            confidence=0.3,
            recommendation="Insufficient data for prediction.",
        )

    positive = 0
    negative = 0
    signal_summaries = []

    for s in signals:
        stype = s.get("signal_type", "")
        severity = s.get("severity", "info")

        signal_summaries.append(s.get("title", stype))
        mult = _SEVERITY_MULTIPLIERS.get(severity, 1.0)

        if stype in ("hiring_trend", "skill_demand"):
            positive += mult
        elif stype in ("layoff_alert",):
            negative += 2 * mult
        elif stype == "disruption":
            negative += mult
        elif stype == "compensation_shift":
            if severity == "critical":
                negative += mult
            else:
                positive += 0.5 * mult

    total = positive + negative
    if total == 0:
        trajectory = "stable"
        confidence = 0.3
    elif positive > negative * 1.5:
        trajectory = "growing"
        confidence = min(0.4 + positive / (total + 1) * 0.5, 0.9)
    elif negative > positive * 1.5:
        trajectory = "declining"
        confidence = min(0.4 + negative / (total + 1) * 0.5, 0.9)
    else:
        trajectory = "stable"
        confidence = 0.5

    recommendations = {
        "growing": f"{company_name} shows positive trajectory — good time to apply or negotiate.",
        "stable": f"{company_name} appears stable — standard risk profile.",
        "declining": f"{company_name} shows concerning signals — proceed with caution.",
    }

    return CompanyTrajectory(
        company_name=company_name,
        trajectory=trajectory,
        confidence=confidence,
        signals=signal_summaries[:5],
        recommendation=recommendations.get(trajectory, ""),
    )


def detect_disruptions(
    industry: str,
    signals: list[dict],
) -> list[DisruptionIndicator]:
    """Detect industry disruption patterns from signals."""
    disruptions = []

    disruption_signals = [
        s for s in signals
        if s.get("signal_type") == "disruption"
        or "disrupt" in s.get("description", "").lower()
        or "transform" in s.get("description", "").lower()
    ]

    if not disruption_signals:
        return disruptions

    # Group by disruption type keywords
    tech_signals = [s for s in disruption_signals if any(
        w in s.get("description", "").lower()
        for w in ("ai", "automat", "machine learning", "robot")
    )]
    regulation_signals = [s for s in disruption_signals if any(
        w in s.get("description", "").lower()
        for w in ("regulat", "compliance", "law", "policy")
    )]

    if tech_signals:
        disruptions.append(DisruptionIndicator(
            industry=industry,
            disruption_type="technology",
            impact_level="high" if len(tech_signals) >= 3 else "medium",
            description=f"Technology disruption signals detected in {industry}.",
            affected_roles=["roles involving repetitive tasks", "manual data processing"],
            timeline="medium_term",
        ))

    if regulation_signals:
        disruptions.append(DisruptionIndicator(
            industry=industry,
            disruption_type="regulation",
            impact_level="medium",
            description=f"Regulatory changes may affect {industry}.",
            affected_roles=["compliance", "legal", "operations"],
            timeline="near_term",
        ))

    return disruptions


def _industries_related(a: str, b: str) -> bool:
    """Check if two industries are related."""
    related_groups = [
        {"technology", "software", "it", "saas", "tech"},
        {"finance", "banking", "fintech", "insurance"},
        {"healthcare", "pharma", "biotech", "medical"},
        {"retail", "ecommerce", "e-commerce", "consumer"},
        {"manufacturing", "automotive", "industrial"},
    ]
    a_lower = a.lower()
    b_lower = b.lower()
    for group in related_groups:
        if any(k in a_lower for k in group) and any(k in b_lower for k in group):
            return True
    return False
