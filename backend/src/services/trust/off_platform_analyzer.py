"""
OffPlatformAlertAnalyzer — rule-based communication risk analysis.

Flags recruiter behaviors that match known scam patterns and calculates
overall risk level from detected flags.
"""

from src.services.trust.models import CommunicationRiskFlag


_BEHAVIOR_RULES: dict[str, dict] = {
    "early_pii_request": {
        "severity": "HIGH",
        "explanation": "Legitimate employers don't request sensitive PII before offer stage",
        "recommended_action": "Do not share sensitive personal information until you have a written offer",
    },
    "pressure_tactics": {
        "severity": "HIGH",
        "explanation": "Pressure to decide quickly is a common scam indicator",
        "recommended_action": "Take your time — legitimate employers allow reasonable decision windows",
    },
    "off_platform_request": {
        "severity": "MEDIUM",
        "explanation": "Moving communication off the hiring platform reduces accountability",
        "recommended_action": "Request official company email communication before proceeding",
    },
    "secrecy_demand": {
        "severity": "HIGH",
        "explanation": "Requests for secrecy about the hiring process are a red flag",
        "recommended_action": "Legitimate hiring processes are transparent — verify with the company directly",
    },
    "upfront_payment": {
        "severity": "HIGH",
        "explanation": "Legitimate employers never require payment from candidates",
        "recommended_action": "Do not pay any fee — report this to the platform immediately",
    },
}


class OffPlatformAlertAnalyzer:
    """Analyzes recruiter communication behaviors for scam patterns."""

    def analyze(self, recruiter_behaviors: list[str]) -> list[CommunicationRiskFlag]:
        """Return risk flags for each recognized behavior."""
        flags: list[CommunicationRiskFlag] = []
        for behavior in recruiter_behaviors:
            rule = _BEHAVIOR_RULES.get(behavior)
            if rule is None:
                continue
            flags.append(CommunicationRiskFlag(
                behavior=behavior,
                severity=rule["severity"],
                explanation=rule["explanation"],
                recommended_action=rule["recommended_action"],
            ))
        return flags

    @staticmethod
    def calculate_overall_risk(flags: list[CommunicationRiskFlag]) -> str:
        """Determine overall risk level from individual flags."""
        if any(f.severity == "HIGH" for f in flags):
            return "HIGH"
        if any(f.severity == "MEDIUM" for f in flags):
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def generate_recommended_actions(flags: list[CommunicationRiskFlag]) -> list[str]:
        """Collect unique recommended actions from all flags."""
        seen: set[str] = set()
        actions: list[str] = []
        for f in flags:
            if f.recommended_action not in seen:
                seen.add(f.recommended_action)
                actions.append(f.recommended_action)
        if not actions:
            actions.append("No significant communication risks detected — standard due diligence recommended")
        return actions
