"""
API endpoints for ranking configuration management.

Provides endpoints for managing runtime-configurable ranking weights
for the search result ranking system.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_api_key
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import RankingConfig
from services.ranking_config_service import (
    RankingConfigService,
    get_ranking_config_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ranking", tags=["Ranking Configuration"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class RankingConfigBase(BaseModel):
    """Base schema for ranking configuration."""

    name: str = Field(..., description="Configuration name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Configuration description")

    # Hybrid search weights
    alpha: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for vector vs keyword (0.7 = 70% vector)",
    )

    # Reranker boost factors
    boost_exact_match: float = Field(default=1.5, ge=0.0, description="Boost for exact matches")
    boost_metadata_match: float = Field(default=1.3, ge=0.0, description="Boost for metadata match")
    boost_quality_signals: float = Field(
        default=1.2, ge=0.0, description="Boost for quality signals"
    )
    diversity_penalty: float = Field(default=0.9, ge=0.0, le=1.0, description="Diversity penalty")

    # Additional ranking signals
    weight_recency: float = Field(default=0.1, ge=0.0, le=1.0, description="Recency weight")
    weight_price_match: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Price match weight"
    )
    weight_location: float = Field(default=0.1, ge=0.0, le=1.0, description="Location weight")

    # Personalization
    personalization_enabled: bool = Field(default=False, description="Enable personalization")
    personalization_weight: float = Field(
        default=0.2, ge=0.0, le=0.5, description="Personalization weight (0-0.5)"
    )


class RankingConfigCreate(RankingConfigBase):
    """Schema for creating a ranking configuration."""

    is_default: bool = Field(default=False, description="Set as default configuration")


class RankingConfigUpdate(BaseModel):
    """Schema for updating a ranking configuration."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    alpha: Optional[float] = Field(None, ge=0.0, le=1.0)
    boost_exact_match: Optional[float] = Field(None, ge=0.0)
    boost_metadata_match: Optional[float] = Field(None, ge=0.0)
    boost_quality_signals: Optional[float] = Field(None, ge=0.0)
    diversity_penalty: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_recency: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_price_match: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_location: Optional[float] = Field(None, ge=0.0, le=1.0)
    personalization_enabled: Optional[bool] = None
    personalization_weight: Optional[float] = Field(None, ge=0.0, le=0.5)


class RankingConfigResponse(RankingConfigBase):
    """Schema for ranking configuration response."""

    id: str
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class RankingWeightsResponse(BaseModel):
    """Simplified response for just the weights."""

    alpha: float
    boost_exact_match: float
    boost_metadata_match: float
    boost_quality_signals: float
    diversity_penalty: float
    weight_recency: float
    weight_price_match: float
    weight_location: float
    personalization_enabled: bool
    personalization_weight: float


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/configs", response_model=List[RankingConfigResponse])
async def list_configs(
    _: None = Depends(get_api_key),
    session: AsyncSession = Depends(get_db),
) -> List[RankingConfigResponse]:
    """
    List all ranking configurations.

    Requires API key authentication.
    """
    result = await session.execute(select(RankingConfig).order_by(RankingConfig.name))
    configs = result.scalars().all()

    return [
        RankingConfigResponse(
            id=str(config.id),
            name=config.name,
            description=config.description,
            alpha=config.alpha,
            boost_exact_match=config.boost_exact_match,
            boost_metadata_match=config.boost_metadata_match,
            boost_quality_signals=config.boost_quality_signals,
            diversity_penalty=config.diversity_penalty,
            weight_recency=config.weight_recency,
            weight_price_match=config.weight_price_match,
            weight_location=config.weight_location,
            personalization_enabled=config.personalization_enabled,
            personalization_weight=config.personalization_weight,
            is_active=config.is_active,
            is_default=config.is_default,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )
        for config in configs
    ]


@router.get("/configs/active", response_model=RankingConfigResponse)
async def get_active_config(
    _: None = Depends(get_api_key),
    service: RankingConfigService = Depends(get_ranking_config_service),
) -> RankingConfigResponse:
    """
    Get the currently active ranking configuration.

    Returns the configuration marked as active, or the default if none active.
    """
    config = await service.get_active_config()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active ranking configuration found",
        )

    return RankingConfigResponse(
        id=str(config.id),
        name=config.name,
        description=config.description,
        alpha=config.alpha,
        boost_exact_match=config.boost_exact_match,
        boost_metadata_match=config.boost_metadata_match,
        boost_quality_signals=config.boost_quality_signals,
        diversity_penalty=config.diversity_penalty,
        weight_recency=config.weight_recency,
        weight_price_match=config.weight_price_match,
        weight_location=config.weight_location,
        personalization_enabled=config.personalization_enabled,
        personalization_weight=config.personalization_weight,
        is_active=config.is_active,
        is_default=config.is_default,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.get("/configs/weights", response_model=RankingWeightsResponse)
async def get_active_weights(
    service: RankingConfigService = Depends(get_ranking_config_service),
) -> RankingWeightsResponse:
    """
    Get the active ranking weights.

    This is a lightweight endpoint for internal use that returns
    just the weight values without full configuration details.
    """
    weights = await service.get_active_weights()

    return RankingWeightsResponse(**weights)


@router.get("/configs/{config_id}", response_model=RankingConfigResponse)
async def get_config(
    config_id: str,
    _: None = Depends(get_api_key),
    service: RankingConfigService = Depends(get_ranking_config_service),
) -> RankingConfigResponse:
    """
    Get a specific ranking configuration by ID.
    """
    config = await service.get_config_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ranking configuration '{config_id}' not found",
        )

    return RankingConfigResponse(
        id=str(config.id),
        name=config.name,
        description=config.description,
        alpha=config.alpha,
        boost_exact_match=config.boost_exact_match,
        boost_metadata_match=config.boost_metadata_match,
        boost_quality_signals=config.boost_quality_signals,
        diversity_penalty=config.diversity_penalty,
        weight_recency=config.weight_recency,
        weight_price_match=config.weight_price_match,
        weight_location=config.weight_location,
        personalization_enabled=config.personalization_enabled,
        personalization_weight=config.personalization_weight,
        is_active=config.is_active,
        is_default=config.is_default,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.post("/configs", response_model=RankingConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    request: RankingConfigCreate,
    _: None = Depends(get_api_key),
    service: RankingConfigService = Depends(get_ranking_config_service),
) -> RankingConfigResponse:
    """
    Create a new ranking configuration.

    Requires API key authentication.
    """
    try:
        config = await service.create_config(
            name=request.name,
            description=request.description,
            alpha=request.alpha,
            boost_exact_match=request.boost_exact_match,
            boost_metadata_match=request.boost_metadata_match,
            boost_quality_signals=request.boost_quality_signals,
            diversity_penalty=request.diversity_penalty,
            weight_recency=request.weight_recency,
            weight_price_match=request.weight_price_match,
            weight_location=request.weight_location,
            personalization_enabled=request.personalization_enabled,
            personalization_weight=request.personalization_weight,
            is_default=request.is_default,
        )

        logger.info(
            "Created ranking configuration '%s' (id=%s)",
            sanitize_for_log(config.name),
            sanitize_for_log(config.id),
        )

        return RankingConfigResponse(
            id=str(config.id),
            name=config.name,
            description=config.description,
            alpha=config.alpha,
            boost_exact_match=config.boost_exact_match,
            boost_metadata_match=config.boost_metadata_match,
            boost_quality_signals=config.boost_quality_signals,
            diversity_penalty=config.diversity_penalty,
            weight_recency=config.weight_recency,
            weight_price_match=config.weight_price_match,
            weight_location=config.weight_location,
            personalization_enabled=config.personalization_enabled,
            personalization_weight=config.personalization_weight,
            is_active=config.is_active,
            is_default=config.is_default,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch("/configs/{config_id}", response_model=RankingConfigResponse)
async def update_config(
    config_id: str,
    request: RankingConfigUpdate,
    _: None = Depends(get_api_key),
    service: RankingConfigService = Depends(get_ranking_config_service),
) -> RankingConfigResponse:
    """
    Update a ranking configuration.

    Only provided fields will be updated.
    Requires API key authentication.
    """
    # Filter out None values
    updates = request.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    try:
        config = await service.update_config(config_id, **updates)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ranking configuration '{config_id}' not found",
            )

        logger.info(
            "Updated ranking configuration '%s' (id=%s)",
            sanitize_for_log(config.name),
            sanitize_for_log(config.id),
        )

        return RankingConfigResponse(
            id=str(config.id),
            name=config.name,
            description=config.description,
            alpha=config.alpha,
            boost_exact_match=config.boost_exact_match,
            boost_metadata_match=config.boost_metadata_match,
            boost_quality_signals=config.boost_quality_signals,
            diversity_penalty=config.diversity_penalty,
            weight_recency=config.weight_recency,
            weight_price_match=config.weight_price_match,
            weight_location=config.weight_location,
            personalization_enabled=config.personalization_enabled,
            personalization_weight=config.personalization_weight,
            is_active=config.is_active,
            is_default=config.is_default,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/configs/{config_id}/activate", response_model=RankingConfigResponse)
async def activate_config(
    config_id: str,
    _: None = Depends(get_api_key),
    service: RankingConfigService = Depends(get_ranking_config_service),
) -> RankingConfigResponse:
    """
    Activate a ranking configuration.

    This will deactivate any currently active configuration.
    Requires API key authentication.
    """
    config = await service.activate_config(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ranking configuration '{config_id}' not found",
        )

    logger.info(
        "Activated ranking configuration '%s' (id=%s)",
        sanitize_for_log(config.name),
        sanitize_for_log(config.id),
    )

    return RankingConfigResponse(
        id=str(config.id),
        name=config.name,
        description=config.description,
        alpha=config.alpha,
        boost_exact_match=config.boost_exact_match,
        boost_metadata_match=config.boost_metadata_match,
        boost_quality_signals=config.boost_quality_signals,
        diversity_penalty=config.diversity_penalty,
        weight_recency=config.weight_recency,
        weight_price_match=config.weight_price_match,
        weight_location=config.weight_location,
        personalization_enabled=config.personalization_enabled,
        personalization_weight=config.personalization_weight,
        is_active=config.is_active,
        is_default=config.is_default,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    config_id: str,
    _: None = Depends(get_api_key),
    service: RankingConfigService = Depends(get_ranking_config_service),
) -> None:
    """
    Delete a ranking configuration.

    Cannot delete the active or default configuration.
    Requires API key authentication.
    """
    try:
        deleted = await service.delete_config(config_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ranking configuration '{config_id}' not found",
            )

        logger.info("Deleted ranking configuration (id=%s)", sanitize_for_log(config_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
