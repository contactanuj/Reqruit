"""
PWA service — Progressive Web App configuration and feature access.

Provides PWA manifest generation, mobile feature capability detection,
and responsive feature flags for the frontend client.
"""

import structlog

from src.core.config import get_settings

logger = structlog.get_logger()


def get_pwa_manifest() -> dict:
    """
    Generate a PWA manifest for mobile installation.

    Returns a W3C Web App Manifest dict suitable for serving at /manifest.json.
    """
    settings = get_settings()
    return {
        "name": settings.app.name,
        "short_name": "Reqruit",
        "description": "AI-powered job hunting assistant",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1a73e8",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
        "categories": ["productivity", "business"],
    }


def get_mobile_features() -> dict:
    """
    Return feature flags and capabilities for mobile clients.

    Mobile clients use this to determine which features to show/hide
    based on available capabilities and screen constraints.
    """
    return {
        "features": {
            "job_discovery": True,
            "application_tracking": True,
            "interview_prep": True,
            "salary_negotiation": True,
            "push_notifications": True,
            "offline_resume_view": True,
            "camera_document_scan": False,
            "biometric_auth": False,
        },
        "ui_hints": {
            "compact_navigation": True,
            "bottom_tab_bar": True,
            "swipe_actions": True,
            "pull_to_refresh": True,
        },
    }
