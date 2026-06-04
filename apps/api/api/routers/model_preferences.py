"""Model Preferences API endpoints (Task #87).

This module provides endpoints for:
- Per-task model preference management
- System default model configurations
- Available providers and models listing
- Cost estimation for model usage
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import User
from db.schemas import (
    ModelCostEstimate,
    SystemDefaultModelPreference,
    SystemDefaultsResponse,
    TaskModelPreferenceCreate,
    TaskModelPreferenceListResponse,
    TaskModelPreferenceResponse,
    TaskModelPreferenceUpdate,
)
from services.model_preference_service import ModelPreferenceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/model-preferences", tags=["Model Preferences"])


# =============================================================================
# User Model Preferences Endpoints
# =============================================================================


@router.get(
    "",
    response_model=TaskModelPreferenceListResponse,
    summary="List user model preferences",
    description="Get all model preferences for the current user.",
)
async def list_user_preferences(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TaskModelPreferenceListResponse:
    """List all model preferences for the current user."""
    service = ModelPreferenceService(session)
    preferences = await service.get_user_preferences(user.id)

    return TaskModelPreferenceListResponse(
        items=[
            TaskModelPreferenceResponse(
                id=p.id,
                user_id=p.user_id,
                task_type=p.task_type,
                provider=p.provider,
                model_name=p.model_name,
                fallback_chain=p.fallback_chain,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in preferences
        ],
        total=len(preferences),
    )


@router.get(
    "/{task_type}",
    response_model=TaskModelPreferenceResponse,
    summary="Get preference for task type",
    description="Get model preference for a specific task type (chat, search, tools, analysis, embedding).",
)
async def get_task_preference(
    task_type: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TaskModelPreferenceResponse:
    """Get model preference for a specific task type."""
    service = ModelPreferenceService(session)

    try:
        preference = await service.get_or_create_preference(user.id, task_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return TaskModelPreferenceResponse(
        id=preference.id,
        user_id=preference.user_id,
        task_type=preference.task_type,
        provider=preference.provider,
        model_name=preference.model_name,
        fallback_chain=preference.fallback_chain,
        is_active=preference.is_active,
        created_at=preference.created_at,
        updated_at=preference.updated_at,
    )


@router.post(
    "",
    response_model=TaskModelPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create model preference",
    description="Create a new model preference for a task type.",
)
async def create_preference(
    data: TaskModelPreferenceCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TaskModelPreferenceResponse:
    """Create a new model preference."""
    service = ModelPreferenceService(session)

    try:
        preference = await service.create_preference(
            user_id=user.id,
            task_type=data.task_type,
            provider=data.provider,
            model_name=data.model_name,
            fallback_chain=[f.model_dump() for f in data.fallback_chain]
            if data.fallback_chain
            else None,
            is_active=data.is_active,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    logger.info(
        "User %s created model preference for task %s: %s/%s",
        sanitize_for_log(user.id[:8]),
        sanitize_for_log(data.task_type),
        sanitize_for_log(data.provider),
        sanitize_for_log(data.model_name),
    )

    return TaskModelPreferenceResponse(
        id=preference.id,
        user_id=preference.user_id,
        task_type=preference.task_type,
        provider=preference.provider,
        model_name=preference.model_name,
        fallback_chain=preference.fallback_chain,
        is_active=preference.is_active,
        created_at=preference.created_at,
        updated_at=preference.updated_at,
    )


@router.put(
    "/{preference_id}",
    response_model=TaskModelPreferenceResponse,
    summary="Update model preference",
    description="Update an existing model preference.",
)
async def update_preference(
    preference_id: str,
    data: TaskModelPreferenceUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TaskModelPreferenceResponse:
    """Update an existing model preference."""
    service = ModelPreferenceService(session)

    try:
        preference = await service.update_preference(
            user_id=user.id,
            preference_id=preference_id,
            provider=data.provider,
            model_name=data.model_name,
            fallback_chain=[f.model_dump() for f in data.fallback_chain]
            if data.fallback_chain
            else None,
            is_active=data.is_active,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model preference not found",
        )

    logger.info(
        "User %s updated model preference %s",
        sanitize_for_log(user.id[:8]),
        sanitize_for_log(preference_id[:8]),
    )

    return TaskModelPreferenceResponse(
        id=preference.id,
        user_id=preference.user_id,
        task_type=preference.task_type,
        provider=preference.provider,
        model_name=preference.model_name,
        fallback_chain=preference.fallback_chain,
        is_active=preference.is_active,
        created_at=preference.created_at,
        updated_at=preference.updated_at,
    )


@router.delete(
    "/{preference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete model preference",
    description="Delete a model preference. Will use system default after deletion.",
)
async def delete_preference(
    preference_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a model preference."""
    service = ModelPreferenceService(session)

    deleted = await service.delete_preference(user.id, preference_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model preference not found",
        )

    logger.info(
        "User %s deleted model preference %s",
        sanitize_for_log(user.id[:8]),
        sanitize_for_log(preference_id[:8]),
    )


# =============================================================================
# System Defaults Endpoints
# =============================================================================


@router.get(
    "/system/defaults",
    response_model=SystemDefaultsResponse,
    summary="Get system default preferences",
    description="Get system default model preferences for all task types.",
)
async def get_system_defaults(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SystemDefaultsResponse:
    """Get system default model preferences."""
    service = ModelPreferenceService(session)

    defaults = service.get_system_defaults()
    providers = service.get_available_providers()
    models = service.get_available_models()

    return SystemDefaultsResponse(
        defaults=[
            SystemDefaultModelPreference(
                task_type=d["task_type"],
                provider=d["provider"],
                model_name=d["model_name"],
                description=d.get("description"),
                cost_per_1m_input_tokens=d.get("cost_per_1m_input_tokens"),
                cost_per_1m_output_tokens=d.get("cost_per_1m_output_tokens"),
            )
            for d in defaults
        ],
        available_providers=providers,
        available_models=models,
    )


@router.get(
    "/system/cost-estimate",
    response_model=ModelCostEstimate,
    summary="Get cost estimate for model",
    description="Get estimated cost for using a specific model.",
)
async def get_cost_estimate(
    provider: str = Query(..., description="Provider name"),
    model_name: str = Query(..., description="Model identifier"),
    estimated_tokens: int = Query(
        1000, ge=1, le=1_000_000, description="Estimated tokens per request"
    ),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ModelCostEstimate:
    """Get cost estimate for a model."""
    service = ModelPreferenceService(session)

    estimate = service.get_cost_estimate(provider, model_name, estimated_tokens)

    return ModelCostEstimate(
        provider=estimate.provider,
        model_name=estimate.model_name,
        input_cost_per_1m=estimate.input_cost_per_1m,
        output_cost_per_1m=estimate.output_cost_per_1m,
        estimated_tokens_per_request=estimate.estimated_tokens_per_request,
        estimated_cost_per_request=estimate.estimated_cost_per_request,
    )
