"""
PWA routes — Progressive Web App manifest and mobile feature detection.

Routes:
    GET /manifest.json — PWA web app manifest
    GET /mobile/features — Mobile feature flags and capabilities
"""

from fastapi import APIRouter

from src.services.pwa_service import get_mobile_features, get_pwa_manifest

router = APIRouter(tags=["pwa"])


@router.get("/manifest.json")
async def manifest():
    """Serve the PWA web app manifest."""
    return get_pwa_manifest()


@router.get("/mobile/features")
async def mobile_features():
    """Return mobile feature flags and UI capability hints."""
    return get_mobile_features()
