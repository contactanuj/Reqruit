"""
Admin trust routes — review queue and report verification.
"""

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.dependencies import get_current_admin_user, get_scam_report_repository
from src.core.exceptions import NotFoundError
from src.db.documents.user import User
from src.repositories.scam_report_repository import ScamReportRepository
from src.services.trust.scam_report_service import ScamReportService

logger = structlog.get_logger()
router = APIRouter(prefix="/admin/trust", tags=["admin-trust"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AdminReviewRequest(BaseModel):
    verified: bool
    admin_notes: str = ""


class ReviewQueueItemResponse(BaseModel):
    id: str
    entity_type: str
    entity_identifier: str
    evidence_type: str
    evidence_text: str
    risk_category: str
    verified: bool
    warning_badge_applied: bool


class AdminVerifyResponse(BaseModel):
    id: str
    entity_identifier: str
    verified: bool
    admin_notes: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/review-queue", response_model=list[ReviewQueueItemResponse])
async def get_review_queue(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_current_admin_user),
    repo: ScamReportRepository = Depends(get_scam_report_repository),
) -> list[ReviewQueueItemResponse]:
    """Return unverified scam reports for admin review."""
    service = ScamReportService(repo)
    reports = await service.get_review_queue(skip=skip, limit=limit)
    return [
        ReviewQueueItemResponse(
            id=str(r.id),
            entity_type=r.entity_type,
            entity_identifier=r.entity_identifier,
            evidence_type=r.evidence_type,
            evidence_text=r.evidence_text,
            risk_category=r.risk_category,
            verified=r.verified,
            warning_badge_applied=r.warning_badge_applied,
        )
        for r in reports
    ]


@router.patch("/reports/{report_id}", response_model=AdminVerifyResponse)
async def verify_report(
    report_id: str,
    request: AdminReviewRequest,
    admin: User = Depends(get_current_admin_user),
    repo: ScamReportRepository = Depends(get_scam_report_repository),
) -> AdminVerifyResponse:
    """Admin verifies a scam report — applies VERIFIED_SCAM badge."""
    service = ScamReportService(repo)
    report = await service.admin_verify_report(
        report_id=PydanticObjectId(report_id),
        admin_notes=request.admin_notes,
    )
    return AdminVerifyResponse(
        id=str(report.id),
        entity_identifier=report.entity_identifier,
        verified=report.verified,
        admin_notes=report.admin_notes,
    )
