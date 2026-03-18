"""
Push notification routes — subscription management and preferences.

Routes:
    POST /notifications/subscribe — Register a push subscription
    DELETE /notifications/subscribe — Unregister a push subscription
    GET /notifications/preferences — Get notification preferences
    PUT /notifications/preferences — Update notification preferences
    POST /notifications/test — Send a test notification to the current user
"""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user, get_push_notification_service
from src.db.documents.user import User
from src.services.push_notification_service import (
    NotificationPayload,
    PushNotificationService,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/subscribe")
async def subscribe(
    subscription: dict,
    user: User = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_notification_service),
):
    """Register a Web Push subscription for the current user."""
    return await service.register_subscription(user.id, subscription)


@router.delete("/subscribe")
async def unsubscribe(
    user: User = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_notification_service),
):
    """Remove the current user's push subscription."""
    return await service.unregister_subscription(user.id)


@router.get("/preferences")
async def get_preferences(
    user: User = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_notification_service),
):
    """Get the current user's notification preferences."""
    return await service.get_preferences(user.id)


@router.put("/preferences")
async def update_preferences(
    preferences: dict,
    user: User = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_notification_service),
):
    """Update the current user's notification preferences."""
    return await service.update_preferences(user.id, preferences)


@router.post("/test")
async def send_test(
    user: User = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_notification_service),
):
    """Send a test notification to the current user."""
    payload = NotificationPayload(
        title="Test Notification",
        body="Push notifications are working!",
        category="general",
    )
    return await service.send_notification(user.id, payload)
