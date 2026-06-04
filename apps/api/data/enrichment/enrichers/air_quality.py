"""
Air Quality Enricher (Task #78).

This module provides an enrichment hook for air quality data,
integrating with the existing AirQualityAdapter.
"""

import logging
import os
from typing import Any, Dict, Optional

from core.security_utils import sanitize_for_log
from data.adapters.air_quality_adapter import AirQualityAdapter
from data.enrichment.hooks import (
    EnrichmentConfig,
    EnrichmentContext,
    EnrichmentPriority,
    EnrichmentResult,
    PropertyEnrichmentHook,
)
from data.enrichment.registry import register_enricher

logger = logging.getLogger(__name__)


@register_enricher
class AirQualityEnricher(PropertyEnrichmentHook[Optional[int]]):
    """
    Enrichment provider for air quality index data.

    Uses the existing AirQualityAdapter to fetch AQI scores from WAQI API
    or fallback to city averages.
    """

    name = "air_quality"
    display_name = "Air Quality Index"
    description = "Fetches air quality index (AQI) data from WAQI API"
    field = "air_quality_index"
    requires_api_key = True
    api_key_env_var = "WAQI_API_KEY"
    default_timeout = 10.0
    default_ttl = 3600  # 1 hour
    priority = EnrichmentPriority.NORMAL

    def __init__(self, config: Optional[EnrichmentConfig] = None) -> None:
        """Initialize air quality enricher."""
        super().__init__(config)
        self._adapter: Optional[AirQualityAdapter] = None

    def _create_adapter(self) -> AirQualityAdapter:
        """Create air quality adapter instance."""
        api_key = os.getenv(self.api_key_env_var)
        return AirQualityAdapter(
            api_key=api_key,
            cache_ttl=self._config.ttl_seconds,
        )

    async def connect(self) -> bool:
        """Initialize adapter connection."""
        try:
            self._adapter = self._create_adapter()
            self._connected = True
            return True
        except Exception as e:
            logger.error("Failed to initialize AirQualityAdapter: %s", sanitize_for_log(e))
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Clean up adapter."""
        self._adapter = None
        self._connected = False

    async def enrich(self, context: EnrichmentContext) -> EnrichmentResult[Optional[int]]:
        """
        Fetch air quality data for a property.

        Args:
            context: Property context with location data

        Returns:
            EnrichmentResult with AQI value
        """
        if not self._adapter:
            self._adapter = self._create_adapter()

        # Check required location data
        if not context.city:
            return EnrichmentResult.skipped_result(
                source=self.name,
                enrichment_field=self.field,
                reason="Missing location data (need city or lat/lon)",
            )

        # Use adapter to fetch AQI (handles both lat/lon and city-only)
        try:
            result = self._adapter.get_aqi_score(
                lat=context.latitude or 0.0,
                lon=context.longitude or 0.0,
                city=context.city or "Unknown",
            )

            if result and result.aqi_value is not None:
                return EnrichmentResult.success_result(
                    source=self.name,
                    enrichment_field=self.field,
                    value=result.aqi_value,
                    ttl_seconds=self._config.ttl_seconds,
                )
            else:
                return EnrichmentResult.error_result(
                    source=self.name,
                    enrichment_field=self.field,
                    error="No AQI data available",
                )
        except Exception as e:
            logger.error("Air quality enrichment failed: %s", sanitize_for_log(e))
            return EnrichmentResult.error_result(
                source=self.name,
                enrichment_field=self.field,
                error=str(e),
            )

    async def health_check(self) -> bool:
        """
        Check if WAQI API is accessible.

        Returns:
            True if healthy
        """
        if not self._adapter:
            self._adapter = self._create_adapter()

        try:
            # Try fetching for a known location
            result = self._adapter.get_aqi_score(
                lat=52.5200,  # Berlin
                lon=13.4050,
                city="Berlin",
            )
            return result is not None
        except Exception as e:
            logger.warning("Air quality health check failed: %s", sanitize_for_log(e))
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get enricher status."""
        status = super().get_status()
        status["has_api_key"] = bool(os.getenv(self.api_key_env_var))
        return status
