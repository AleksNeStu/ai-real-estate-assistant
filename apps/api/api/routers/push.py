"""Push notification endpoints (Task #63).

Provides API endpoints for:
- Getting VAPID public key for browser subscription
- Subscribing to push notifications
- Unsubscribing from push notifications
- Listing user's subscriptions
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from config.settings import get_settings
from db import get_db
from db.models import User
from db.repositories import PushSubscriptionRepository
from db.schemas import (
    PushSubscriptionCreate,
    PushSubscriptionListResponse,
    PushSubscriptionResponse,
    VapidPublicKeyResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/push", tags=["Push Notifications"])

settings = get_settings()


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key() -> VapidPublicKeyResponse:
    """Get VAPID public key for browser push subscription.

    This endpoint is public (no auth required) as the key is needed
    before the user can subscribe to push notifications.

    Returns:
        VAPID public key (base64url encoded) and enabled status
    """
    return VapidPublicKeyResponse(
        public_key=settings.vapid_public_key or "",
        enabled=settings.push_enabled and bool(settings.vapid_public_key),
    )


@router.post(
    "/subscribe", response_model=PushSubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def subscribe_to_push(
    body: PushSubscriptionCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_name: Annotated[str | None, Query(max_length=100)] = None,
) -> PushSubscriptionResponse:
    """Register a push subscription for the current user.

    Args:
        body: Push subscription data from the browser
        user: Current authenticated user
        db: Database session
        device_name: Optional friendly name for the device

    Returns:
        Created subscription details

    Raises:
        HTTPException 409: If endpoint already registered to another user
    """
    if not settings.push_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not enabled",
        )

    repo = PushSubscriptionRepository(db)

    # Extract keys from the subscription data
    keys = body.keys
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not p256dh or not auth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required keys (p256dh, auth) in subscription data",
        )

    # Check if subscription already exists
    existing = await repo.get_by_endpoint(body.endpoint)
    if existing:
        if existing.user_id != user.id:
            logger.warning(
                "Push endpoint conflict: user %s tried to register endpoint owned by user %s",
                user.id,
                existing.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This endpoint is already registered to another user",
            )
        # Re-activate if previously unsubscribed
        if not existing.is_active:
            existing = await repo.update(existing, is_active=True, device_name=device_name)
            logger.info("Re-activated push subscription %s for user %s", existing.id, user.id)
        return PushSubscriptionResponse.model_validate(existing)

    # Create new subscription
    subscription = await repo.create(
        user_id=user.id,
        endpoint=body.endpoint,
        p256dh=p256dh,
        auth=auth,
        device_name=device_name,
    )
    await db.commit()

    logger.info("Created push subscription %s for user %s", subscription.id, user.id)
    return PushSubscriptionResponse.model_validate(subscription)


@router.delete("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_push(
    endpoint: Annotated[str, Query(max_length=500)],
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a push subscription.

    Args:
        endpoint: The push subscription endpoint URL to unsubscribe
        user: Current authenticated user
        db: Database session
    """
    repo = PushSubscriptionRepository(db)
    subscription = await repo.get_by_endpoint(endpoint)

    if subscription and subscription.user_id == user.id:
        await repo.delete(subscription)
        await db.commit()
        logger.info("Deleted push subscription %s for user %s", subscription.id, user.id)

    # Return 204 even if not found (idempotent)


@router.get("/subscriptions", response_model=PushSubscriptionListResponse)
async def list_push_subscriptions(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_inactive: bool = False,
) -> PushSubscriptionListResponse:
    """List all push subscriptions for the current user.

    Args:
        user: Current authenticated user
        db: Database session
        include_inactive: Whether to include inactive subscriptions

    Returns:
        List of subscriptions
    """
    repo = PushSubscriptionRepository(db)
    subscriptions = await repo.get_by_user(user.id, active_only=not include_inactive)

    return PushSubscriptionListResponse(
        items=[PushSubscriptionResponse.model_validate(s) for s in subscriptions],
        total=len(subscriptions),
    )


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_push_subscription(
    subscription_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a specific push subscription by ID.

    Args:
        subscription_id: ID of the subscription to delete
        user: Current authenticated user
        db: Database session

    Raises:
        HTTPException 404: If subscription not found or not owned by user
    """
    repo = PushSubscriptionRepository(db)
    subscription = await repo.get_by_id(subscription_id)

    if not subscription or subscription.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    await repo.delete(subscription)
    await db.commit()
    logger.info("Deleted push subscription %s for user %s", subscription.id, user.id)
