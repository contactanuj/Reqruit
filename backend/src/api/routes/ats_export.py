"""
ATS export routes — profile data export for auto-fill integrations.

Routes:
    GET /profile/export — Export ATS-compatible profile data
    GET /profile/export/{platform} — Export for a specific ATS platform
    GET /ats/platforms — List supported ATS platforms
"""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user
from src.db.documents.user import User
from src.repositories.profile_repository import ProfileRepository
from src.repositories.resume_repository import ResumeRepository
from src.services.ats_export_service import ATSExportService
from src.services.ats_mapping_service import get_supported_platforms, map_to_platform

router = APIRouter(tags=["ats-export"])


def _build_service() -> ATSExportService:
    return ATSExportService(
        profile_repo=ProfileRepository(),
        resume_repo=ResumeRepository(),
    )


@router.get("/profile/export")
async def export_profile(
    user: User = Depends(get_current_user),
):
    """Export user profile and resume data in ATS-compatible format."""
    service = _build_service()
    return await service.export_profile(user.id)


@router.get("/profile/export/{platform}")
async def export_for_platform(
    platform: str,
    user: User = Depends(get_current_user),
):
    """Export profile mapped to a specific ATS platform's field names."""
    service = _build_service()
    generic = await service.export_profile(user.id)
    return map_to_platform(generic, platform)


@router.get("/ats/platforms")
async def list_platforms():
    """List supported ATS platform names."""
    return {"platforms": get_supported_platforms()}
