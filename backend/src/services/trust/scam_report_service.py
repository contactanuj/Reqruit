"""
ScamReportService — business logic for community scam reporting.

Handles duplicate detection, report creation, and automatic WARNING_BADGE
application when the 3-report threshold from distinct users is reached.
"""

import structlog
from beanie import PydanticObjectId

from src.core.exceptions import ConflictError, NotFoundError
from src.db.documents.scam_report import ScamReport
from src.repositories.scam_report_repository import ScamReportRepository
from src.services.trust.models import TrendingScamPattern

logger = structlog.get_logger()

_BADGE_THRESHOLD = 3  # distinct reporters needed for automatic badge


class ScamReportService:
    """Orchestrates scam report submission and badge management."""

    def __init__(self, repo: ScamReportRepository) -> None:
        self._repo = repo

    async def submit_report(
        self,
        reporter_user_id: PydanticObjectId,
        entity_type: str,
        entity_identifier: str,
        evidence_type: str,
        evidence_text: str,
        risk_category: str,
    ) -> ScamReport:
        """Submit a scam report. Raises ConflictError on duplicate."""
        is_duplicate = await self._repo.check_duplicate(
            reporter_user_id, entity_identifier
        )
        if is_duplicate:
            raise ConflictError(
                detail=f"You have already reported {entity_identifier}",
                error_code="ALREADY_REPORTED",
            )

        report = ScamReport(
            reporter_user_id=reporter_user_id,
            entity_type=entity_type,
            entity_identifier=entity_identifier,
            evidence_type=evidence_type,
            evidence_text=evidence_text,
            risk_category=risk_category,
        )
        created = await self._repo.create(report)

        badge_applied = await self._check_and_apply_badge(entity_identifier)

        logger.info(
            "scam_report_submitted",
            entity_type=entity_type,
            entity_identifier=entity_identifier,
            badge_applied=badge_applied,
        )

        return created

    async def _check_and_apply_badge(self, entity_identifier: str) -> bool:
        """Apply WARNING_BADGE if distinct reporter count >= threshold."""
        has_badge = await self._repo.has_warning_badge(entity_identifier)
        if has_badge:
            return False

        count = await self._repo.get_distinct_reporter_count(entity_identifier)
        if count >= _BADGE_THRESHOLD:
            await self._repo.apply_warning_badge(entity_identifier)
            logger.info(
                "warning_badge_applied",
                entity_identifier=entity_identifier,
                distinct_reporters=count,
            )
            return True
        return False

    async def get_entity_reports(self, entity_identifier: str) -> dict:
        """Return entity report summary with hashed reporter IDs."""
        return await self._repo.get_entity_summary(entity_identifier)

    async def admin_verify_report(
        self,
        report_id: PydanticObjectId,
        admin_notes: str,
    ) -> ScamReport:
        """Admin verifies a report — applies VERIFIED_SCAM badge."""
        report = await self._repo.verify_report(report_id, admin_notes)
        if report is None:
            raise NotFoundError("Scam report", str(report_id))

        # Apply VERIFIED_SCAM badge (permanent, distinct from WARNING_BADGE)
        await self._repo.apply_warning_badge(report.entity_identifier)

        logger.info(
            "admin_verified_report",
            report_id=str(report_id),
            entity_identifier=report.entity_identifier,
        )
        return report

    async def get_review_queue(
        self, skip: int = 0, limit: int = 50
    ) -> list[ScamReport]:
        """Return unverified reports for admin review."""
        return await self._repo.get_unverified_queue(skip=skip, limit=limit)

    async def get_trending_scams(
        self, region: str | None = None
    ) -> list[TrendingScamPattern]:
        """Aggregate trending scam patterns."""
        aggregated = await self._repo.get_trending_aggregation(region=region)
        if not aggregated:
            return []

        patterns = []
        for item in aggregated:
            if item["report_count"] < 2:
                continue
            entity_types = item.get("entity_types", [])
            pattern_type = entity_types[0] if entity_types else "unknown"
            patterns.append(TrendingScamPattern(
                pattern_type=pattern_type,
                region=region or "GLOBAL",
                affected_companies=[item["_id"]],
                report_count=item["report_count"],
                example_signals=item.get("risk_categories", []),
            ))

        return patterns

    async def submit_deepfake_report(
        self,
        reporter_user_id: PydanticObjectId,
        company_name: str | None,
        recruiter_name: str | None,
        interview_id: str | None,
        observed_anomalies: list[str],
        interview_platform: str | None,
    ) -> ScamReport:
        """Submit a deepfake interview concern as a ScamReport."""
        entity_identifier = company_name or interview_id or "unknown"
        anomaly_text = "; ".join(observed_anomalies)
        if interview_platform:
            anomaly_text += f" (platform: {interview_platform})"

        return await self.submit_report(
            reporter_user_id=reporter_user_id,
            entity_type="interview",
            entity_identifier=entity_identifier,
            evidence_type="deepfake_concern",
            evidence_text=anomaly_text,
            risk_category="SUSPICIOUS",
        )
