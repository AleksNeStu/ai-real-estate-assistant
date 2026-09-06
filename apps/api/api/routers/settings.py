import logging
import os
from typing import Optional

from fastapi import APIRouter, Body, Header, HTTPException, Query, Request

import models.user_model_preferences as user_model_preferences
from api.models import (
    ModelCatalogItem,
    ModelPreferences,
    ModelPreferencesUpdate,
    ModelPricing,
    ModelProviderCatalog,
    ModelRuntimeTestResponse,
    NotificationPreviewRequest,
    NotificationPreviewResponse,
    NotificationSettings,
    NotificationSettingsUpdate,
)
from db.database import get_db_context
from db.repositories import NotificationPreferenceRepository, UserRepository
from models.provider_factory import ModelProviderFactory
from utils.sanitization import sanitize_for_logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Settings"])

# Simple in-memory store for demo mode preference (per-session)
_DEMO_MODE_SESSIONS: dict[str, bool] = {}


def _resolve_user_email(user_email: str | None, x_user_email: str | None) -> str:
    resolved = (user_email or x_user_email or "").strip()
    if not resolved:
        raise HTTPException(status_code=400, detail="Missing user email")
    return resolved


@router.get("/settings/notifications", response_model=NotificationSettings)
async def get_notification_settings(
    user_email: str | None = Query(default=None),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    """Get notification settings for the current user (Task #86)."""
    try:
        resolved_user_email = _resolve_user_email(user_email, x_user_email)

        async with get_db_context() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_email(resolved_user_email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            prefs_repo = NotificationPreferenceRepository(session)
            prefs = await prefs_repo.get_or_create(user.id)

            return NotificationSettings(
                price_alerts_enabled=prefs.price_alerts_enabled,
                new_listings_enabled=prefs.new_listings_enabled,
                saved_search_enabled=prefs.saved_search_enabled,
                market_updates_enabled=prefs.market_updates_enabled,
                alert_frequency=prefs.alert_frequency,
                email_enabled=prefs.email_enabled,
                push_enabled=prefs.push_enabled,
                in_app_enabled=prefs.in_app_enabled,
                quiet_hours_start=prefs.quiet_hours_start,
                quiet_hours_end=prefs.quiet_hours_end,
                price_drop_threshold=prefs.price_drop_threshold,
                daily_digest_time=prefs.daily_digest_time,
                weekly_digest_day=prefs.weekly_digest_day,
                expert_mode=prefs.expert_mode,
                marketing_emails=prefs.marketing_emails,
                unsubscribe_token=prefs.unsubscribe_token,
                unsubscribed_at=prefs.unsubscribed_at,
                unsubscribed_types=prefs.unsubscribed_types,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching settings: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/settings/notifications", response_model=NotificationSettings)
async def update_notification_settings(
    settings: NotificationSettingsUpdate,
    user_email: str | None = Query(default=None),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    """Update notification settings for the current user (Task #86)."""
    try:
        resolved_user_email = _resolve_user_email(user_email, x_user_email)

        async with get_db_context() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_email(resolved_user_email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            prefs_repo = NotificationPreferenceRepository(session)
            prefs = await prefs_repo.get_or_create(user.id)

            # Build update dict from non-None values
            update_data = settings.model_dump(exclude_unset=True)
            if update_data:
                await prefs_repo.update(prefs, **update_data)

            return NotificationSettings(
                price_alerts_enabled=prefs.price_alerts_enabled,
                new_listings_enabled=prefs.new_listings_enabled,
                saved_search_enabled=prefs.saved_search_enabled,
                market_updates_enabled=prefs.market_updates_enabled,
                alert_frequency=prefs.alert_frequency,
                email_enabled=prefs.email_enabled,
                push_enabled=prefs.push_enabled,
                in_app_enabled=prefs.in_app_enabled,
                quiet_hours_start=prefs.quiet_hours_start,
                quiet_hours_end=prefs.quiet_hours_end,
                price_drop_threshold=prefs.price_drop_threshold,
                daily_digest_time=prefs.daily_digest_time,
                weekly_digest_day=prefs.weekly_digest_day,
                expert_mode=prefs.expert_mode,
                marketing_emails=prefs.marketing_emails,
                unsubscribe_token=prefs.unsubscribe_token,
                unsubscribed_at=prefs.unsubscribed_at,
                unsubscribed_types=prefs.unsubscribed_types,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/settings/notifications/preview", response_model=NotificationPreviewResponse)
async def send_notification_preview(
    request: NotificationPreviewRequest,
    user_email: str | None = Query(default=None),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    """Send a test notification to verify settings (Task #86)."""
    try:
        resolved_user_email = _resolve_user_email(user_email, x_user_email)

        async with get_db_context() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_email(resolved_user_email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            prefs_repo = NotificationPreferenceRepository(session)
            prefs = await prefs_repo.get_or_create(user.id)

            # Check if the requested channel is enabled
            channel_enabled = {
                "email": prefs.email_enabled,
                "push": prefs.push_enabled,
                "in_app": prefs.in_app_enabled,
            }

            if not channel_enabled.get(request.channel, False):
                return NotificationPreviewResponse(
                    success=False,
                    message=f"{request.channel.title()} notifications are disabled in your settings",
                    channel=request.channel,
                    notification_type=request.notification_type,
                )

            # Simulate sending notification (in real implementation, would trigger actual notification)
            # For now, just log and return success
            logger.info(
                f"Preview notification: channel={sanitize_for_logging(request.channel)}, type={sanitize_for_logging(request.notification_type)}, user={sanitize_for_logging(user.email)}"
            )

            return NotificationPreviewResponse(
                success=True,
                message=f"Test {request.notification_type} sent via {request.channel}",
                channel=request.channel,
                notification_type=request.notification_type,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending preview notification: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/settings/notifications/unsubscribe/{token}")
async def unsubscribe_by_token(
    token: str,
    notification_type: Optional[str] = Query(
        default=None, description="Specific type to unsubscribe from, or all if omitted"
    ),
):
    """One-click unsubscribe from notifications via token (Task #86)."""
    try:
        async with get_db_context() as session:
            prefs_repo = NotificationPreferenceRepository(session)
            prefs = await prefs_repo.get_by_unsubscribe_token(token)

            if not prefs:
                raise HTTPException(status_code=404, detail="Invalid unsubscribe token")

            if notification_type:
                # Unsubscribe from specific type
                await prefs_repo.unsubscribe_type(prefs, notification_type)
                return {
                    "success": True,
                    "message": f"You have been unsubscribed from {notification_type} notifications",
                    "unsubscribed_type": notification_type,
                }
            else:
                # Unsubscribe from all
                await prefs_repo.unsubscribe_all(prefs)
                return {
                    "success": True,
                    "message": "You have been unsubscribed from all notifications",
                    "unsubscribed_all": True,
                }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing unsubscribe: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings/models", response_model=list[ModelProviderCatalog])
async def list_model_catalog():
    """List available model providers and their models."""
    try:
        providers: list[ModelProviderCatalog] = []
        for provider_name in ModelProviderFactory.list_providers():
            provider = ModelProviderFactory.get_provider(provider_name)
            models: list[ModelCatalogItem] = []
            runtime_available: bool | None = None
            available_models: list[str] | None = None
            runtime_error: str | None = None

            for model_info in provider.list_models():
                pricing = None
                if model_info.pricing:
                    pricing = ModelPricing(
                        input_price_per_1m=model_info.pricing.input_price_per_1m,
                        output_price_per_1m=model_info.pricing.output_price_per_1m,
                        currency=model_info.pricing.currency,
                    )

                models.append(
                    ModelCatalogItem(
                        id=model_info.id,
                        display_name=model_info.display_name,
                        provider_name=model_info.provider_name,
                        context_window=model_info.context_window,
                        pricing=pricing,
                        capabilities=[c.value for c in model_info.capabilities],
                        description=model_info.description,
                        recommended_for=model_info.recommended_for,
                    )
                )

            if provider.is_local:
                runtime_available, runtime_error = provider.validate_connection()
                if runtime_available and hasattr(provider, "list_available_models"):
                    maybe_models = provider.list_available_models()
                    available_models = list(maybe_models) if maybe_models else []
                else:
                    available_models = []

            providers.append(
                ModelProviderCatalog(
                    name=provider.name,
                    display_name=provider.display_name,
                    is_local=provider.is_local,
                    requires_api_key=provider.requires_api_key,
                    models=models,
                    runtime_available=runtime_available,
                    available_models=available_models,
                    runtime_error=runtime_error,
                )
            )
        return providers
    except Exception as e:
        logger.error(f"Error listing model catalog: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings/test-runtime", response_model=ModelRuntimeTestResponse)
async def test_runtime(provider: str = Query(...)):
    """
    Test connection/runtime status for a specific provider.
    """
    try:
        allowed_providers = set(ModelProviderFactory.list_providers())
        if provider not in allowed_providers:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

        p = ModelProviderFactory.get_provider(provider)
        if not p.is_local:
            raise HTTPException(
                status_code=400, detail=f"Provider '{provider}' is not a local runtime provider"
            )

        runtime_available, runtime_error = p.validate_connection()
        available_models = []
        if runtime_available and hasattr(p, "list_available_models"):
            maybe_models = p.list_available_models()
            available_models = list(maybe_models) if maybe_models else []

        return ModelRuntimeTestResponse(
            provider=provider,
            is_local=True,
            runtime_available=runtime_available,
            available_models=available_models,
            runtime_error=runtime_error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing runtime: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings/model-preferences", response_model=ModelPreferences)
async def get_model_preferences(
    user_email: str | None = Query(default=None),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    try:
        resolved_user_email = _resolve_user_email(user_email, x_user_email)
        prefs = user_model_preferences.MODEL_PREFS_MANAGER.get_preferences(resolved_user_email)
        return ModelPreferences(
            preferred_provider=prefs.preferred_provider,
            preferred_model=prefs.preferred_model,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error fetching model preferences: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/settings/model-preferences", response_model=ModelPreferences)
async def update_model_preferences(
    payload: ModelPreferencesUpdate,
    user_email: str | None = Query(default=None),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    try:
        resolved_user_email = _resolve_user_email(user_email, x_user_email)
        existing = user_model_preferences.MODEL_PREFS_MANAGER.get_preferences(resolved_user_email)

        incoming_provider = payload.preferred_provider
        incoming_model = payload.preferred_model

        next_provider = (
            incoming_provider if incoming_provider is not None else existing.preferred_provider
        )
        next_model = incoming_model if incoming_model is not None else existing.preferred_model

        if incoming_provider is not None and (incoming_provider.strip() == ""):
            next_provider = None
            if incoming_model is None:
                next_model = None

        if incoming_model is not None and (incoming_model.strip() == ""):
            next_model = None

        if next_model and not next_provider:
            raise HTTPException(
                status_code=400,
                detail="preferred_provider is required when setting preferred_model",
            )

        if next_provider:
            allowed_providers = set(ModelProviderFactory.list_providers())
            if next_provider not in allowed_providers:
                raise HTTPException(status_code=400, detail=f"Unknown provider: {next_provider}")

            provider = ModelProviderFactory.get_provider(next_provider)
            if next_model:
                allowed_models = {m.id for m in provider.list_models()}
                if next_model not in allowed_models:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown model for provider '{next_provider}': {next_model}",
                    )
            else:
                if incoming_provider is not None and existing.preferred_model:
                    allowed_models = {m.id for m in provider.list_models()}
                    if existing.preferred_model in allowed_models:
                        next_model = existing.preferred_model

        updated = user_model_preferences.MODEL_PREFS_MANAGER.update_preferences(
            resolved_user_email,
            preferred_provider=next_provider,
            preferred_model=next_model,
        )

        return ModelPreferences(
            preferred_provider=updated.preferred_provider,
            preferred_model=updated.preferred_model,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error updating model preferences: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/settings/demo")
async def set_demo_mode(
    request: Request,
    demo_mode: bool = Body(..., embed=True),
):
    """Set demo mode preference (stored in session for demo purposes).

    This endpoint allows toggling demo mode at runtime without requiring authentication.
    In a production environment, this would be a per-user setting stored in the database.
    For demo purposes, we use a simple in-memory session store.
    """
    try:
        # Get session ID from headers or generate one
        session_id = request.headers.get("X-Session-ID", "default")
        _DEMO_MODE_SESSIONS[session_id] = demo_mode
        logger.info(
            "Demo mode set to %s for session %s",
            sanitize_for_logging(demo_mode),
            sanitize_for_logging(session_id),
        )
        return {"demo_mode": demo_mode, "session_id": session_id}
    except Exception as e:
        logger.error(f"Error setting demo mode: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings/demo")
async def get_demo_mode(request: Request):
    """Get current demo mode preference."""
    try:
        session_id = request.headers.get("X-Session-ID", "default")
        # Check session store first, then fall back to env var
        is_demo = _DEMO_MODE_SESSIONS.get(
            session_id, os.getenv("DEMO_MODE", "false").lower() == "true"
        )
        return {"demo_mode": is_demo, "session_id": session_id}
    except Exception as e:
        logger.error(f"Error getting demo mode: {sanitize_for_logging(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
