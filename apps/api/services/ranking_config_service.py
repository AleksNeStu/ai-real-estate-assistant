"""
Service for managing ranking configurations.

This service provides runtime-configurable ranking weights for the
search result ranking system, supporting A/B testing and dynamic tuning.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import RankingConfig

logger = logging.getLogger(__name__)


# Default ranking weights (fallback when database unavailable)
DEFAULT_RANKING_CONFIG = {
    "alpha": 0.7,  # 70% vector, 30% keyword
    "boost_exact_match": 1.5,
    "boost_metadata_match": 1.3,
    "boost_quality_signals": 1.2,
    "diversity_penalty": 0.9,
    "weight_recency": 0.1,
    "weight_price_match": 0.15,
    "weight_location": 0.1,
    "personalization_enabled": False,
    "personalization_weight": 0.2,
}


class RankingConfigCreate(BaseModel):
    """Schema for creating a new ranking configuration."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

    # Hybrid search weights
    alpha: float = Field(default=0.7, ge=0.0, le=1.0)

    # Reranker boost factors
    boost_exact_match: float = Field(default=1.5, ge=0.0, le=5.0)
    boost_metadata_match: float = Field(default=1.3, ge=0.0, le=5.0)
    boost_quality_signals: float = Field(default=1.2, ge=0.0, le=5.0)
    diversity_penalty: float = Field(default=0.9, ge=0.0, le=1.0)

    # Additional ranking signals
    weight_recency: float = Field(default=0.1, ge=0.0, le=1.0)
    weight_price_match: float = Field(default=0.15, ge=0.0, le=1.0)
    weight_location: float = Field(default=0.1, ge=0.0, le=1.0)

    # Personalization
    personalization_enabled: bool = False
    personalization_weight: float = Field(default=0.2, ge=0.0, le=0.5)


class RankingConfigUpdate(BaseModel):
    """Schema for updating a ranking configuration."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

    alpha: Optional[float] = Field(None, ge=0.0, le=1.0)
    boost_exact_match: Optional[float] = Field(None, ge=0.0, le=5.0)
    boost_metadata_match: Optional[float] = Field(None, ge=0.0, le=5.0)
    boost_quality_signals: Optional[float] = Field(None, ge=0.0, le=5.0)
    diversity_penalty: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_recency: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_price_match: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_location: Optional[float] = Field(None, ge=0.0, le=1.0)
    personalization_enabled: Optional[bool] = None
    personalization_weight: Optional[float] = Field(None, ge=0.0, le=0.5)
    is_active: Optional[bool] = None


@dataclass
class RankingWeights:
    """Dataclass for passing ranking weights to search functions."""

    alpha: float = 0.7
    boost_exact_match: float = 1.5
    boost_metadata_match: float = 1.3
    boost_quality_signals: float = 1.2
    diversity_penalty: float = 0.9
    weight_recency: float = 0.1
    weight_price_match: float = 0.15
    weight_location: float = 0.1
    personalization_enabled: bool = False
    personalization_weight: float = 0.2

    config_id: Optional[str] = None
    config_name: Optional[str] = None

    @classmethod
    def from_model(cls, config: RankingConfig) -> "RankingWeights":
        """Create RankingWeights from a RankingConfig database model."""
        return cls(
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
            config_id=str(config.id),
            config_name=config.name,
        )

    @classmethod
    def default(cls) -> "RankingWeights":
        """Create default RankingWeights from hardcoded values."""
        return cls(
            alpha=DEFAULT_RANKING_CONFIG["alpha"],
            boost_exact_match=DEFAULT_RANKING_CONFIG["boost_exact_match"],
            boost_metadata_match=DEFAULT_RANKING_CONFIG["boost_metadata_match"],
            boost_quality_signals=DEFAULT_RANKING_CONFIG["boost_quality_signals"],
            diversity_penalty=DEFAULT_RANKING_CONFIG["diversity_penalty"],
            weight_recency=DEFAULT_RANKING_CONFIG["weight_recency"],
            weight_price_match=DEFAULT_RANKING_CONFIG["weight_price_match"],
            weight_location=DEFAULT_RANKING_CONFIG["weight_location"],
            personalization_enabled=bool(DEFAULT_RANKING_CONFIG["personalization_enabled"]),
            personalization_weight=DEFAULT_RANKING_CONFIG["personalization_weight"],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "alpha": self.alpha,
            "boost_exact_match": self.boost_exact_match,
            "boost_metadata_match": self.boost_metadata_match,
            "boost_quality_signals": self.boost_quality_signals,
            "diversity_penalty": self.diversity_penalty,
            "weight_recency": self.weight_recency,
            "weight_price_match": self.weight_price_match,
            "weight_location": self.weight_location,
            "personalization_enabled": self.personalization_enabled,
            "personalization_weight": self.personalization_weight,
        }


class RankingConfigService:
    """Service for managing ranking configurations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, RankingConfig] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Cache for 1 minute

    async def get_active_config(self) -> Optional[RankingConfig]:
        """
        Get the currently active ranking configuration model.

        Returns:
            The active RankingConfig or None if not found.
        """
        try:
            # Check cache first
            if self._is_cache_valid() and "active" in self._cache:
                return self._cache["active"]

            # Query database for active config
            stmt = select(RankingConfig).where(
                RankingConfig.is_active == True  # noqa: E712
            )
            result = await self.session.execute(stmt)
            config = result.scalar_one_or_none()

            if config:
                self._cache["active"] = config
                self._cache_time = datetime.now(UTC)

            return config

        except Exception as e:
            logger.error("Error fetching active ranking config: %s", sanitize_for_log(e))
            return None

    async def get_active_weights(self) -> dict[str, Any]:
        """
        Get the currently active ranking weights as a dictionary.

        Returns:
            Dictionary of weight values.
        """
        config = await self.get_active_config()
        if config:
            return RankingWeights.from_model(config).to_dict()
        return RankingWeights.default().to_dict()

    async def get_config_by_name(self, name: str) -> Optional[RankingConfig]:
        """
        Get a configuration by name.

        Args:
            name: The configuration name.

        Returns:
            The RankingConfig or None if not found.
        """
        try:
            # Check cache first
            cache_key = f"name:{name}"
            if self._is_cache_valid() and cache_key in self._cache:
                return self._cache[cache_key]

            stmt = select(RankingConfig).where(RankingConfig.name == name)
            result = await self.session.execute(stmt)
            config = result.scalar_one_or_none()

            if config:
                self._cache[cache_key] = config
                self._cache_time = datetime.now(UTC)

            return config

        except Exception as e:
            logger.error(
                "Error fetching ranking config '%s': %s",
                sanitize_for_log(name),
                sanitize_for_log(e),
            )
            return None

    async def get_config_by_id(self, config_id: str) -> Optional[RankingConfig]:
        """
        Get a configuration by ID.

        Args:
            config_id: The configuration ID.

        Returns:
            The RankingConfig or None if not found.
        """
        try:
            # Check cache first
            cache_key = f"id:{config_id}"
            if self._is_cache_valid() and cache_key in self._cache:
                return self._cache[cache_key]

            stmt = select(RankingConfig).where(RankingConfig.id == config_id)
            result = await self.session.execute(stmt)
            config = result.scalar_one_or_none()

            if config:
                self._cache[cache_key] = config
                self._cache_time = datetime.now(UTC)

            return config

        except Exception as e:
            logger.error(
                "Error fetching ranking config '%s': %s",
                sanitize_for_log(config_id),
                sanitize_for_log(e),
            )
            return None

    async def list_configs(self, include_inactive: bool = False) -> list[RankingConfig]:
        """
        List all ranking configurations.

        Args:
            include_inactive: Whether to include inactive configurations.

        Returns:
            List of RankingConfig objects.
        """
        try:
            stmt = select(RankingConfig).order_by(RankingConfig.created_at.desc())
            if not include_inactive:
                stmt = stmt.where(RankingConfig.is_active == True)  # noqa: E712

            result = await self.session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error("Error listing ranking configs: %s", sanitize_for_log(e))
            return []

    async def create_config(
        self,
        name: str,
        description: Optional[str] = None,
        alpha: float = 0.7,
        boost_exact_match: float = 1.5,
        boost_metadata_match: float = 1.3,
        boost_quality_signals: float = 1.2,
        diversity_penalty: float = 0.9,
        weight_recency: float = 0.1,
        weight_price_match: float = 0.15,
        weight_location: float = 0.1,
        personalization_enabled: bool = False,
        personalization_weight: float = 0.2,
        is_default: bool = False,
    ) -> RankingConfig:
        """
        Create a new ranking configuration.

        Returns:
            The created RankingConfig.

        Raises:
            ValueError: If a config with the same name exists.
        """
        # Check for duplicate name
        existing = await self.get_config_by_name(name)
        if existing:
            raise ValueError(f"Ranking config with name '{name}' already exists")

        config = RankingConfig(
            name=name,
            description=description,
            alpha=alpha,
            boost_exact_match=boost_exact_match,
            boost_metadata_match=boost_metadata_match,
            boost_quality_signals=boost_quality_signals,
            diversity_penalty=diversity_penalty,
            weight_recency=weight_recency,
            weight_price_match=weight_price_match,
            weight_location=weight_location,
            personalization_enabled=personalization_enabled,
            personalization_weight=personalization_weight,
            is_active=False,  # New configs start inactive
            is_default=is_default,
        )

        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)

        # Invalidate cache
        self._invalidate_cache()

        logger.info(
            "Created ranking config '%s' (id=%s)",
            sanitize_for_log(config.name),
            sanitize_for_log(config.id),
        )
        return config

    async def update_config(self, config_id: str, **updates: Any) -> Optional[RankingConfig]:
        """
        Update a ranking configuration.

        Args:
            config_id: The configuration ID.
            **updates: The fields to update.

        Returns:
            The updated RankingConfig or None if not found.
        """
        config = await self.get_config_by_id(config_id)
        if not config:
            return None

        # Apply updates
        for field, value in updates.items():
            if value is not None and hasattr(config, field):
                setattr(config, field, value)

        await self.session.commit()
        await self.session.refresh(config)

        # Invalidate cache
        self._invalidate_cache()

        logger.info(
            "Updated ranking config '%s' (id=%s)",
            sanitize_for_log(config.name),
            sanitize_for_log(config.id),
        )
        return config

    async def activate_config(self, config_id: str) -> Optional[RankingConfig]:
        """
        Activate a configuration (deactivates all others).

        Args:
            config_id: The configuration ID to activate.

        Returns:
            The activated RankingConfig or None if not found.
        """
        config = await self.get_config_by_id(config_id)
        if not config:
            return None

        # Deactivate all other configs
        await self.session.execute(
            update(RankingConfig).where(RankingConfig.id != config_id).values(is_active=False)
        )

        # Activate this config
        config.is_active = True
        await self.session.commit()
        await self.session.refresh(config)

        # Invalidate cache
        self._invalidate_cache()

        logger.info(
            "Activated ranking config '%s' (id=%s)",
            sanitize_for_log(config.name),
            sanitize_for_log(config.id),
        )
        return config

    async def delete_config(self, config_id: str) -> bool:
        """
        Delete a configuration.

        Args:
            config_id: The configuration ID.

        Returns:
            True if deleted, False if not found.

        Raises:
            ValueError: If trying to delete the active config.
        """
        config = await self.get_config_by_id(config_id)
        if not config:
            return False

        if config.is_active:
            raise ValueError("Cannot delete the active ranking configuration")

        await self.session.delete(config)
        await self.session.commit()

        # Invalidate cache
        self._invalidate_cache()

        logger.info(
            "Deleted ranking config '%s' (id=%s)",
            sanitize_for_log(config.name),
            sanitize_for_log(config.id),
        )
        return True

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if not self._cache_time:
            return False

        age = (datetime.now(UTC) - self._cache_time).total_seconds()
        return age < self._cache_ttl_seconds

    def _invalidate_cache(self) -> None:
        """Invalidate the entire cache."""
        self._cache.clear()
        self._cache_time = None


# Dependency injection helper
def get_ranking_config_service(
    session: AsyncSession = Depends(get_db),
) -> RankingConfigService:
    """Get a RankingConfigService instance."""
    return RankingConfigService(session)
