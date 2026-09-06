"""
Base adapter interface for external property data sources.

This module defines the abstract interface that all portal adapters
must implement, ensuring consistent behavior across different data sources.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

import backoff
import pandas as pd

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar("T")

# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_WAIT = 1  # seconds
RETRY_MAX_WAIT = 30  # seconds

# Exceptions that trigger retry
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,  # Includes socket errors
)


def with_retry(
    max_tries: int = MAX_RETRIES,
    max_time: int = RETRY_MAX_WAIT,
    on_retry: Optional[Callable[[int, float, Exception], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retry with exponential backoff.

    Args:
        max_tries: Maximum number of retry attempts
        max_time: Maximum total time to wait in seconds
        on_retry: Optional callback for retry events (attempt, wait_time, exception)

    Returns:
        Decorated function with retry logic

    Usage:
        @with_retry(max_tries=3)
        def fetch_data():
            return requests.get("https://api.example.com")
    """

    def _on_retry_handler(details: Any) -> None:
        """Handle retry event logging."""
        wait_time = getattr(details, "wait", 0)
        exception = getattr(details, "exception", None)
        attempt = getattr(details, "tries", 0)

        logger.warning(
            "Retry attempt %s/%s after %.1fs. Exception: %s: %s",
            sanitize_for_log(attempt),
            sanitize_for_log(max_tries),
            wait_time,
            sanitize_for_log(type(exception).__name__ if exception else "Unknown"),
            sanitize_for_log(exception),
        )

        if on_retry:
            if exception:
                on_retry(attempt, wait_time, exception)
            else:
                # Exception might be stored differently in backoff's details dict
                # Try accessing as dict instead of using getattr
                if isinstance(details, dict):
                    exception = details.get("exception")
                    if exception:
                        on_retry(attempt, wait_time, exception)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @backoff.on_exception(
            backoff.expo,
            RETRYABLE_EXCEPTIONS,
            max_tries=max_tries,
            max_time=max_time,
            jitter=backoff.full_jitter,
            on_backoff=_on_retry_handler,
        )
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        return wrapper

    return decorator


def with_retry_async(
    max_tries: int = MAX_RETRIES,
    max_time: int = RETRY_MAX_WAIT,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Async decorator for retry with exponential backoff.

    Args:
        max_tries: Maximum number of retry attempts
        max_time: Maximum total time to wait in seconds

    Returns:
        Decorated async function with retry logic
    """

    def _on_retry_handler_async(details: Any) -> None:
        """Handle retry event logging for async functions."""
        wait_time = getattr(details, "wait", 0)
        exception = getattr(details, "exception", None)
        attempt = getattr(details, "tries", 0)

        logger.warning(
            "Async retry attempt %s/%s after %.1fs. Exception: %s: %s",
            sanitize_for_log(attempt),
            sanitize_for_log(max_tries),
            wait_time,
            sanitize_for_log(type(exception).__name__ if exception else "Unknown"),
            sanitize_for_log(exception),
        )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @backoff.on_exception(
            backoff.expo,
            RETRYABLE_EXCEPTIONS,
            max_tries=max_tries,
            max_time=max_time,
            jitter=backoff.full_jitter,
            on_backoff=_on_retry_handler_async,
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)  # type: ignore[misc,return-value,no-any-return]

        return wrapper  # type: ignore[return-value]

    return decorator


@dataclass
class PortalFilter:
    """
    Filters for portal property queries.

    Attributes:
        city: City to search in
        min_price: Minimum price filter
        max_price: Maximum price filter
        min_rooms: Minimum number of rooms
        max_rooms: Maximum number of rooms
        property_type: Property type filter (apartment, house, etc.)
        listing_type: Listing type (rent, sale)
        limit: Maximum number of results to fetch
    """

    city: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rooms: Optional[float] = None
    max_rooms: Optional[float] = None
    property_type: Optional[str] = None
    listing_type: Optional[str] = "rent"
    limit: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary for API requests."""
        return {
            k: v
            for k, v in [
                ("city", self.city),
                ("min_price", self.min_price),
                ("max_price", self.max_price),
                ("min_rooms", self.min_rooms),
                ("max_rooms", self.max_rooms),
                ("property_type", self.property_type),
                ("listing_type", self.listing_type),
                ("limit", self.limit),
            ]
            if v is not None
        }

    def __str__(self) -> str:
        """Return string representation of filters."""
        parts = []
        if self.city:
            parts.append(f"city={self.city}")
        if self.min_price is not None or self.max_price is not None:
            parts.append(f"price={self.min_price or 0}-{self.max_price or 'unlimited'}")
        if self.min_rooms is not None or self.max_rooms is not None:
            parts.append(f"rooms={self.min_rooms or 0}-{self.max_rooms or 'unlimited'}")
        if self.property_type:
            parts.append(f"type={self.property_type}")
        if self.listing_type:
            parts.append(f"listing={self.listing_type}")
        return ", ".join(parts) if parts else "no filters"


@dataclass
class PortalFetchResult:
    """
    Result of a portal data fetch operation.

    Attributes:
        success: Whether the fetch was successful
        properties: List of property dictionaries
        count: Number of properties fetched
        source: Source identifier (e.g., 'otodom', 'idealista')
        source_type: Source type for tracking (always 'portal')
        fetched_at: Timestamp of fetch
        filters: Filters used for the fetch
        errors: List of error messages if any
        metadata: Additional metadata from the portal
    """

    success: bool
    properties: List[Dict[str, Any]] = field(default_factory=list)
    count: int = 0
    source: str = ""
    source_type: str = "portal"
    fetched_at: datetime = field(default_factory=datetime.now)
    filters: Optional[PortalFilter] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert properties to pandas DataFrame."""
        if not self.properties:
            return pd.DataFrame()
        return pd.DataFrame(self.properties)

    def add_error(self, error: str) -> None:
        """Add an error message to the result."""
        self.errors.append(error)
        logger.error("[%s] %s", sanitize_for_log(self.source), sanitize_for_log(error))


class ExternalSourceAdapter(ABC):
    """
    Abstract base class for external portal adapters.

    All portal adapters must inherit from this class and implement the
    required methods to fetch and normalize property data.

    Attributes:
        name: Unique identifier for the adapter (e.g., 'otodom', 'idealista')
        display_name: Human-readable name for display in UI
        requires_api_key: Whether this adapter requires an API key
        api_key_env_var: Environment variable name for the API key
        rate_limit_requests: Maximum requests per time window
        rate_limit_window: Time window in seconds for rate limiting
    """

    name: str = ""
    display_name: str = ""
    requires_api_key: bool = False
    api_key_env_var: str = ""
    rate_limit_requests: int = 60
    rate_limit_window: int = 60

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the adapter.

        Args:
            api_key: Optional API key for the portal
        """
        self._api_key = api_key
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """
        Validate adapter configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if self.requires_api_key and not self._api_key:
            raise ValueError(
                f"Adapter '{self.name}' requires API key. "
                f"Set environment variable '{self.api_key_env_var}'"
            )

    @abstractmethod
    def fetch(self, filters: PortalFilter) -> PortalFetchResult:
        """
        Fetch properties from the portal.

        Args:
            filters: Search filters to apply

        Returns:
            PortalFetchResult with fetched properties or errors
        """
        pass

    @abstractmethod
    def normalize_property(self, raw_property: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a raw property from the portal to internal schema.

        Maps portal-specific fields to the canonical property schema:
        - city, neighborhood, address
        - price, currency
        - rooms, bathrooms, area_sqm
        - property_type, listing_type
        - amenities (has_parking, has_garden, etc.)
        - source_url, source_platform

        Args:
            raw_property: Raw property data from portal

        Returns:
            Normalized property dictionary matching Property schema
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Get adapter status information.

        Returns:
            Dictionary with status information including:
            - name: Adapter name
            - configured: Whether adapter is properly configured
            - has_api_key: Whether API key is available
            - rate_limit: Rate limit information
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "configured": not self.requires_api_key or bool(self._api_key),
            "has_api_key": bool(self._api_key),
            "rate_limit": {
                "requests": self.rate_limit_requests,
                "window_seconds": self.rate_limit_window,
            },
        }

    def _build_source_url(self, property_id: str, path: Optional[str] = None) -> str:
        """
        Build source URL for a property.

        Args:
            property_id: Property ID from the portal
            path: Optional path override

        Returns:
            Full URL to the property on the portal
        """
        base_url = self._get_base_url()
        if path:
            return f"{base_url}{path}"
        return f"{base_url}/property/{property_id}"

    @abstractmethod
    def _get_base_url(self) -> str:
        """
        Get base URL for the portal.

        Returns:
            Base URL (e.g., 'https://www.otodom.pl')
        """
        pass


class RateLimiter:
    """
    Simple rate limiter for API requests.

    Implements a token bucket algorithm for rate limiting.
    """

    def __init__(self, requests: int, window: int):
        """
        Initialize rate limiter.

        Args:
            requests: Maximum number of requests allowed
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        self._tokens = requests
        self._last_update = datetime.now().timestamp()

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Acquire a token, blocking if necessary.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if token acquired, False if timeout exceeded
        """
        import time

        deadline = datetime.now().timestamp() + timeout

        while datetime.now().timestamp() < deadline:
            now = datetime.now().timestamp()
            elapsed = now - self._last_update

            # Refill tokens based on elapsed time
            self._tokens = min(
                self.requests, self._tokens + int(elapsed * self.requests / self.window)
            )
            self._last_update = now

            if self._tokens >= 1:
                self._tokens -= 1
                return True

            # Wait a bit before retrying
            time.sleep(0.1)

        logger.warning("Rate limiter timeout after %ss", sanitize_for_log(timeout))
        return False

    def reset(self) -> None:
        """Reset the rate limiter (for testing)."""
        self._tokens = self.requests
        self._last_update = datetime.now().timestamp()
