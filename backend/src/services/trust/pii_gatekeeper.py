"""
PIIGatekeeper — rule-based PII sharing boundaries by hiring stage and jurisdiction.

Pure lookup-table service (no LLM calls). Determines what personal information
is appropriate to share at each hiring stage for India and US markets.
"""

from src.services.trust.models import HiringStage, PIIAssessment


# PII items appropriate at each stage (cumulative — each stage includes previous)
_STAGE_RULES: dict[str, dict[str, list[str]]] = {
    "IN": {
        HiringStage.APPLICATION: ["name", "email", "phone", "city"],
        HiringStage.PHONE_SCREEN: ["current_ctc", "notice_period"],
        HiringStage.ONSITE: ["address", "education_certificates"],
        HiringStage.OFFER: ["pan", "current_salary_slips"],
        HiringStage.POST_OFFER: ["aadhaar", "bank_details", "relieving_letter"],
    },
    "US": {
        HiringStage.APPLICATION: ["name", "email", "phone", "city"],
        HiringStage.PHONE_SCREEN: ["work_authorization_status"],
        HiringStage.ONSITE: ["address", "references"],
        HiringStage.OFFER: ["salary_history"],
        HiringStage.POST_OFFER: ["ssn", "bank_details", "drivers_license"],
    },
}

_STAGE_ORDER = [
    HiringStage.APPLICATION,
    HiringStage.PHONE_SCREEN,
    HiringStage.ONSITE,
    HiringStage.OFFER,
    HiringStage.POST_OFFER,
]


class PIIGatekeeper:
    """Evaluates PII sharing appropriateness by hiring stage and jurisdiction."""

    def evaluate(
        self,
        hiring_stage: str,
        jurisdiction: str,
        pii_requested: list[str],
    ) -> PIIAssessment:
        """Return assessment of what PII is appropriate/inappropriate at this stage."""
        jurisdiction_upper = jurisdiction.upper()
        rules = _STAGE_RULES.get(jurisdiction_upper, _STAGE_RULES["US"])

        appropriate = self._get_cumulative_pii(rules, hiring_stage)
        all_pii = self._get_all_pii(rules)
        inappropriate = [p for p in all_pii if p not in appropriate]

        alerts: list[str] = []
        for pii in pii_requested:
            if pii in inappropriate:
                alerts.append(
                    f"'{pii}' is not appropriate to share at the {hiring_stage} stage"
                )

        return PIIAssessment(
            hiring_stage=hiring_stage,
            jurisdiction=jurisdiction_upper,
            appropriate_pii=appropriate,
            inappropriate_pii=inappropriate,
            alerts=alerts,
        )

    @staticmethod
    def _get_cumulative_pii(rules: dict[str, list[str]], target_stage: str) -> list[str]:
        """Collect PII items from application through the target stage."""
        result: list[str] = []
        for stage in _STAGE_ORDER:
            result.extend(rules.get(stage, []))
            if stage == target_stage:
                break
        return result

    @staticmethod
    def _get_all_pii(rules: dict[str, list[str]]) -> list[str]:
        """Collect all PII items across all stages."""
        result: list[str] = []
        for stage in _STAGE_ORDER:
            result.extend(rules.get(stage, []))
        return result
