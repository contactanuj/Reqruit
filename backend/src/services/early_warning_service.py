"""
Early warning service — detects career risk signals from vitals and market data.

Pure-Python deterministic service that evaluates career vitals against
configurable thresholds and generates early warning signals. No LLM calls.
"""

from pydantic import BaseModel

from src.db.documents.career_vitals import CareerVitals, DriftIndicator


class EarlyWarningSignal(BaseModel):
    """A career early warning signal with severity and action."""

    signal_type: str  # skill_decay, market_contraction, compensation_drift, stagnation
    severity: str  # low, medium, high, critical
    title: str
    description: str
    recommended_action: str


# Thresholds for signal generation
_THRESHOLDS = {
    "skill_relevance": {"warning": 60, "critical": 40},
    "market_demand": {"warning": 50, "critical": 30},
    "compensation_alignment": {"warning": 55, "critical": 35},
    "growth_trajectory": {"warning": 50, "critical": 30},
    "network_strength": {"warning": 45, "critical": 25},
    "job_satisfaction": {"warning": 40, "critical": 20},
}

_SIGNAL_MAP = {
    "skill_relevance": ("skill_decay", "Your skills may be falling behind market expectations"),
    "market_demand": ("market_contraction", "Demand for your role/industry is softening"),
    "compensation_alignment": ("compensation_drift", "Your compensation may be below market rate"),
    "growth_trajectory": ("stagnation", "Your career growth has slowed"),
    "network_strength": ("network_gap", "Your professional network needs strengthening"),
    "job_satisfaction": ("satisfaction_alert", "Your job satisfaction is declining"),
}

_ACTIONS = {
    "skill_decay": "Prioritize upskilling in high-demand areas — consider certifications or project work.",
    "market_contraction": "Diversify your skill set and explore adjacent roles or industries.",
    "compensation_drift": "Research current market rates and prepare for a compensation discussion.",
    "stagnation": "Seek stretch assignments, mentorship, or consider a role change.",
    "network_gap": "Attend industry events, engage on LinkedIn, and schedule informational interviews.",
    "satisfaction_alert": "Reflect on what's driving dissatisfaction — discuss with your manager or consider a change.",
}


def evaluate_vitals(vitals: CareerVitals) -> list[EarlyWarningSignal]:
    """Evaluate career vitals against thresholds and generate warning signals."""
    signals = []

    for metric in vitals.metrics:
        thresholds = _THRESHOLDS.get(metric.name)
        if not thresholds:
            continue

        signal_info = _SIGNAL_MAP.get(metric.name)
        if not signal_info:
            continue

        signal_type, description = signal_info

        if metric.score <= thresholds["critical"]:
            severity = "critical"
        elif metric.score <= thresholds["warning"]:
            severity = "warning" if metric.trend != "declining" else "high"
        elif metric.trend == "declining" and metric.score <= thresholds["warning"] + 15:
            severity = "low"
        else:
            continue

        action = _ACTIONS.get(signal_type, "Review and take action.")

        signals.append(EarlyWarningSignal(
            signal_type=signal_type,
            severity=severity,
            title=f"{metric.name.replace('_', ' ').title()} Alert",
            description=f"{description}. Current score: {metric.score}/100 (trend: {metric.trend}).",
            recommended_action=action,
        ))

    return signals


def evaluate_drift_indicators(indicators: list[DriftIndicator]) -> list[EarlyWarningSignal]:
    """Convert drift indicators into early warning signals."""
    signals = []
    for ind in indicators:
        signals.append(EarlyWarningSignal(
            signal_type=ind.category,
            severity=ind.severity,
            title=f"Drift: {ind.category.replace('_', ' ').title()}",
            description=ind.description,
            recommended_action=ind.recommended_action or _ACTIONS.get(ind.category, "Take action."),
        ))
    return signals


def generate_early_warnings(vitals: CareerVitals) -> list[EarlyWarningSignal]:
    """Generate all early warning signals from career vitals."""
    signals = evaluate_vitals(vitals)
    signals.extend(evaluate_drift_indicators(vitals.drift_indicators))

    # Sort by severity: critical > high > warning > low
    severity_order = {"critical": 0, "high": 1, "warning": 2, "low": 3}
    signals.sort(key=lambda s: severity_order.get(s.severity, 4))

    return signals
