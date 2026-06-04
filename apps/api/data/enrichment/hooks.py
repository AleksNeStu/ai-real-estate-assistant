"""
Property Enrichment Hook Interface (Task #78).

This module defines the abstract interface that all property enrichment
providers must implement, ensuring consistent behavior across different
enrichment sources.

The interface follows the MCPConnector pattern from Task #64 with lifecycle
methods (connect, health_check) and extends the existing DataEnrichmentService
protocol.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EnrichmentStatus(str, Enum):
    """Status of an enrichment operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class EnrichmentPriority(int, Enum):
    """Priority level for enrichment execution order."""

    CRITICAL = 10  # Must run first (e.g., required data)
    HIGH = 20  # Important but not critical
    NORMAL = 30  # Standard priority
    LOW = 40  # Nice to have
    BACKGROUND = 50  # Can run asynchronously


@dataclass
class EnrichmentConfig:
    """Configuration for an enrichment provider."""

    enabled: bool = True
    ttl_seconds: int = 3600  # 1 hour default
    timeout_seconds: float = 30.0
    fallback_value: Any = None
    required: bool = False  # If True, failure raises exception
    priority: EnrichmentPriority = EnrichmentPriority.NORMAL
    cache_enabled: bool = True
    retry_count: int = 3
    retry_delay_seconds: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "enabled": self.enabled,
            "ttl_seconds": self.ttl_seconds,
            "timeout_seconds": self.timeout_seconds,
            "fallback_value": str(self.fallback_value) if self.fallback_value else None,
            "required": self.required,
            "priority": self.priority.value,
            "cache_enabled": self.cache_enabled,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
        }


@dataclass
class EnrichmentContext:
    """Context passed to enrichment hooks containing property data."""

    property_id: str
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_property(cls, property_data: Dict[str, Any]) -> "EnrichmentContext":
        """Create context from property data dictionary."""
        return cls(
            property_id=str(property_data.get("id", "")),
            address=property_data.get("address"),
            city=property_data.get("city"),
            latitude=property_data.get("latitude"),
            longitude=property_data.get("longitude"),
            postal_code=property_data.get("postal_code"),
            country=property_data.get("country"),
            extra={
                k: v
                for k, v in property_data.items()
                if k
                not in {"id", "address", "city", "latitude", "longitude", "postal_code", "country"}
            },
        )


@dataclass
class EnrichmentResult(Generic[T]):
    """Result of an enrichment operation."""

    source: str
    enrichment_field: str
    value: Optional[T] = None
    status: EnrichmentStatus = EnrichmentStatus.PENDING
    cached: bool = False
    error: Optional[str] = None
    ttl_seconds: int = 3600
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if enrichment was successful."""
        return self.status in {EnrichmentStatus.COMPLETED, EnrichmentStatus.CACHED}

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "source": self.source,
            "field": self.enrichment_field,
            "value": self.value,
            "status": self.status.value,
            "cached": self.cached,
            "error": self.error,
            "ttl_seconds": self.ttl_seconds,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }

    @classmethod
    def success_result(
        cls,
        source: str,
        enrichment_field: str,
        value: T,
        ttl_seconds: int = 3600,
        cached: bool = False,
        execution_time_ms: float = 0.0,
    ) -> "EnrichmentResult[T]":
        """Create a successful result."""
        return cls(
            source=source,
            enrichment_field=enrichment_field,
            value=value,
            status=EnrichmentStatus.CACHED if cached else EnrichmentStatus.COMPLETED,
            cached=cached,
            ttl_seconds=ttl_seconds,
            execution_time_ms=execution_time_ms,
        )

    @classmethod
    def error_result(
        cls,
        source: str,
        enrichment_field: str,
        error: str,
        execution_time_ms: float = 0.0,
    ) -> "EnrichmentResult[T]":
        """Create an error result."""
        return cls(
            source=source,
            enrichment_field=enrichment_field,
            status=EnrichmentStatus.FAILED,
            error=error,
            execution_time_ms=execution_time_ms,
        )

    @classmethod
    def cached_result(
        cls,
        source: str,
        enrichment_field: str,
        value: T,
        ttl_seconds: int = 3600,
    ) -> "EnrichmentResult[T]":
        """Create a cached result."""
        return cls(
            source=source,
            enrichment_field=enrichment_field,
            value=value,
            status=EnrichmentStatus.CACHED,
            cached=True,
            ttl_seconds=ttl_seconds,
        )

    @classmethod
    def skipped_result(
        cls,
        source: str,
        enrichment_field: str,
        reason: str = "",
    ) -> "EnrichmentResult[T]":
        """Create a skipped result."""
        return cls(
            source=source,
            enrichment_field=enrichment_field,
            status=EnrichmentStatus.SKIPPED,
            metadata={"reason": reason},
        )


class PropertyEnrichmentHook(ABC, Generic[T]):
    """
    Abstract base class for property data enrichment.

    All enrichment providers must inherit from this class and implement the
    required methods. This follows the MCPConnector pattern from Task #64
    with lifecycle methods and standardized results.

    Generic type T represents the enrichment value type.

    Class Attributes:
        name: Unique identifier for the enricher (must be set by subclass)
        display_name: Human-readable name for display in UI
        description: Brief description of what this enricher provides
        field: Property field name to enrich
        requires_api_key: Whether this enricher requires an API key
        api_key_env_var: Environment variable name for the API key
        default_timeout: Default request timeout in seconds
        default_ttl: Default cache TTL in seconds
        priority: Execution priority (higher = run later)
    """

    name: str = ""
    display_name: str = ""
    description: str = ""
    field: str = ""
    requires_api_key: bool = False
    api_key_env_var: str = ""
    default_timeout: float = 30.0
    default_ttl: int = 3600
    priority: EnrichmentPriority = EnrichmentPriority.NORMAL

    def __init__(self, config: Optional[EnrichmentConfig] = None) -> None:
        """
        Initialize the enricher.

        Args:
            config: Optional configuration (falls back to defaults)
        """
        self._config = config or self._create_default_config()
        self._connected = False
        self._validate_configuration()
        logger.info("Initialized enrichment hook: %s", sanitize_for_log(self.name))

    def _create_default_config(self) -> EnrichmentConfig:
        """Create default configuration from class attributes."""
        return EnrichmentConfig(
            enabled=True,
            ttl_seconds=self.default_ttl,
            timeout_seconds=self.default_timeout,
            priority=self.priority,
        )

    def _validate_configuration(self) -> None:
        """
        Validate enricher configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.name:
            raise ValueError("Enricher must have a 'name' attribute")
        if not self.field:
            raise ValueError(f"Enricher '{self.name}' must have a 'field' attribute")

    def get_cache_key(self, property_id: str) -> str:
        """
        Generate cache key for a property.

        Args:
            property_id: Property identifier

        Returns:
            Cache key string
        """
        return f"enrichment:{self.name}:{property_id}:{self.field}"

    def get_config(self) -> EnrichmentConfig:
        """Get current enricher configuration."""
        return self._config

    def is_enabled(self) -> bool:
        """Check if enricher is enabled."""
        return self._config.enabled

    @abstractmethod
    async def enrich(self, context: EnrichmentContext) -> EnrichmentResult[T]:
        """
        Fetch enrichment data for a property.

        Args:
            context: Property context with location and identification data

        Returns:
            EnrichmentResult with enrichment data
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if enrichment source is available.

        Returns:
            True if source is healthy and available
        """
        pass

    async def connect(self) -> bool:
        """
        Establish connection to the enrichment source.

        Override this method if your enricher needs to establish
        connections or initialize resources.

        Returns:
            True if connection successful
        """
        self._connected = True
        return True

    async def disconnect(self) -> None:
        """
        Close connection to the enrichment source.

        Override this method if your enricher needs to clean up
        resources.
        """
        self._connected = False

    def is_connected(self) -> bool:
        """Check if enricher is currently connected."""
        return self._connected

    def get_status(self) -> Dict[str, Any]:
        """
        Get enricher status information.

        Returns:
            Dictionary with status information
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "field": self.field,
            "connected": self._connected,
            "enabled": self._config.enabled,
            "config": self._config.to_dict(),
            "requires_api_key": self.requires_api_key,
        }

    async def enrich_with_timing(self, context: EnrichmentContext) -> EnrichmentResult[T]:
        """
        Execute enrichment with automatic timing measurement.

        Args:
            context: Property context

        Returns:
            EnrichmentResult with timing metadata
        """
        start_time = time.perf_counter()
        try:
            result = await self.enrich(context)
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            result.execution_time_ms = execution_time_ms
            return result
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Enrichment failed for %s: %s", sanitize_for_log(self.name), sanitize_for_log(e)
            )
            return EnrichmentResult.error_result(
                source=self.name,
                enrichment_field=self.field,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

    async def __aenter__(self) -> "PropertyEnrichmentHook[T]":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
