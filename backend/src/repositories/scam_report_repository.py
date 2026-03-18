"""
ScamReport repository — data access for community scam reports.

Provides entity-level queries, duplicate detection, and badge management.
"""

import hashlib

from beanie import PydanticObjectId

from src.db.documents.scam_report import ScamReport
from src.repositories.base import BaseRepository


class ScamReportRepository(BaseRepository[ScamReport]):
    """Data access methods for scam reports."""

    def __init__(self) -> None:
        super().__init__(ScamReport)

    async def get_by_entity(self, entity_identifier: str) -> list[ScamReport]:
        """Return all reports for an entity."""
        return await self.find_many(
            {"entity_identifier": entity_identifier}, limit=1000
        )

    async def get_distinct_reporter_count(self, entity_identifier: str) -> int:
        """Count distinct users who reported this entity."""
        pipeline = [
            {"$match": {"entity_identifier": entity_identifier}},
            {"$group": {"_id": "$reporter_user_id"}},
            {"$count": "total"},
        ]
        result = await ScamReport.aggregate(pipeline).to_list()
        return result[0]["total"] if result else 0

    async def check_duplicate(
        self, reporter_user_id: PydanticObjectId, entity_identifier: str
    ) -> bool:
        """Return True if this user already reported this entity."""
        existing = await self.find_one({
            "reporter_user_id": reporter_user_id,
            "entity_identifier": entity_identifier,
        })
        return existing is not None

    async def apply_warning_badge(self, entity_identifier: str) -> None:
        """Set warning_badge_applied=True on all reports for this entity."""
        await ScamReport.find(
            {"entity_identifier": entity_identifier}
        ).update_many({"$set": {"warning_badge_applied": True}})

    async def has_warning_badge(self, entity_identifier: str) -> bool:
        """Check if any report for this entity has the warning badge."""
        report = await self.find_one({
            "entity_identifier": entity_identifier,
            "warning_badge_applied": True,
        })
        return report is not None

    async def get_entity_summary(self, entity_identifier: str) -> dict:
        """Return report count, risk categories, badge status with hashed reporter IDs."""
        reports = await self.get_by_entity(entity_identifier)
        if not reports:
            return {
                "entity_identifier": entity_identifier,
                "report_count": 0,
                "risk_categories": [],
                "warning_badge": False,
                "reporters": [],
            }

        risk_categories = list({r.risk_category for r in reports if r.risk_category})
        badge = any(r.warning_badge_applied for r in reports)
        hashed_reporters = [
            hashlib.sha256(str(r.reporter_user_id).encode()).hexdigest()[:12]
            for r in reports
        ]

        return {
            "entity_identifier": entity_identifier,
            "report_count": len(reports),
            "risk_categories": risk_categories,
            "warning_badge": badge,
            "reporters": hashed_reporters,
        }

    async def get_unverified_queue(
        self, skip: int = 0, limit: int = 50
    ) -> list[ScamReport]:
        """Return unverified reports sorted by created_at ascending."""
        return await self.find_many(
            {"verified": False},
            skip=skip,
            limit=limit,
            sort="created_at",
        )

    async def verify_report(
        self, report_id: PydanticObjectId, admin_notes: str
    ) -> ScamReport | None:
        """Mark a report as verified with admin notes."""
        return await self.update(report_id, {
            "verified": True,
            "admin_notes": admin_notes,
        })

    async def get_verified_scam_entity_ids(self) -> list[str]:
        """Return entity_identifiers with at least one verified report."""
        pipeline = [
            {"$match": {"verified": True}},
            {"$group": {"_id": "$entity_identifier"}},
        ]
        result = await ScamReport.aggregate(pipeline).to_list()
        return [r["_id"] for r in result]

    async def get_trending_aggregation(
        self, region: str | None = None
    ) -> list[dict]:
        """Aggregate reports by entity for trending scams."""
        match_stage: dict = {}
        if region:
            match_stage["risk_category"] = {"$exists": True}

        pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {"$group": {
                "_id": "$entity_identifier",
                "report_count": {"$sum": 1},
                "risk_categories": {"$addToSet": "$risk_category"},
                "entity_types": {"$addToSet": "$entity_type"},
            }},
            {"$sort": {"report_count": -1}},
            {"$limit": 20},
        ]
        return await ScamReport.aggregate(pipeline).to_list()
