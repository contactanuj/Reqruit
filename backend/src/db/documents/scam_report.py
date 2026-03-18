"""
ScamReport document — community scam reports for companies, recruiters, and postings.

Reports are submitted by authenticated users. When 3+ distinct users report
the same entity, an automatic WARNING_BADGE is applied.
"""

from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel

from src.db.base_document import TimestampedDocument


class ScamReport(TimestampedDocument):
    """
    A user-submitted scam report for a company, recruiter, or posting.

    Fields:
        reporter_user_id: The user who submitted the report.
        entity_type: What is being reported — company, recruiter, or posting.
        entity_identifier: Identifier for the entity (company name, email, URL).
        evidence_type: Type of evidence — screenshot, url, or description.
        evidence_text: The evidence content.
        risk_category: User-assessed risk level.
        verified: Whether an admin has verified this report.
        admin_notes: Admin review notes.
        warning_badge_applied: Whether the automatic WARNING_BADGE has been applied.
    """

    reporter_user_id: PydanticObjectId
    entity_type: str  # company, recruiter, posting
    entity_identifier: Indexed(str)
    evidence_type: str = "description"  # screenshot, url, description
    evidence_text: str = ""
    risk_category: str = ""
    verified: bool = False
    admin_notes: str = ""
    warning_badge_applied: bool = False

    class Settings:
        name = "scam_reports"
        indexes = [
            IndexModel(
                [("reporter_user_id", 1), ("entity_identifier", 1)],
                unique=True,
            ),
        ]
