"""
MCP Connector Rate Limiter.

Provides per-connector rate limiting for MCP connectors.
This is part of Task #71: MCP Registry API.

Features:
- Per-connector configurable rate limits
- In-memory sliding window implementation
- Async-safe for FastAPI integration
- Rate limit headers in responses
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for a connector's rate limit."""

    requests_per_minute: int = 60
    burst_size: int = 10  # Allow short bursts above limit
    enabled: bool = True


@dataclass
class ConnectorRateLimitStatus:
    """Status of a connector's rate limit."""

    connector_name: str
    requests_per_minute: int
    enabled: bool
    current_requests: int
    remaining: int
    reset_at: float  # Unix timestamp


class MCPConnectorRateLimiter:
    """
    Rate limiter for MCP connectors.

    Implements sliding window rate limiting per connector.
    Thread-safe using asyncio locks.
    """

    def __init__(self, default_rpm: int = 60, default_burst: int = 10):
        """
        Initialize the rate limiter.

        Args:
            default_rpm: Default requests per minute
            default_burst: Default burst size
        """
        self._default_config = RateLimitConfig(
            requests_per_minute=default_rpm, burst_size=default_burst
        )
        self._connector_configs: Dict[str, RateLimitConfig] = {}
        self._request_times: Dict[str, deque] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def configure_connector(
        self,
        connector_name: str,
        requests_per_minute: Optional[int] = None,
        burst_size: Optional[int] = None,
        enabled: bool = True,
    ) -> None:
        """
        Configure rate limit for a specific connector.

        Args:
            connector_name: Name of the connector
            requests_per_minute: Max requests per minute (uses default if None)
            burst_size: Max burst size (uses default if None)
            enabled: Whether rate limiting is enabled
        """
        config = RateLimitConfig(
            requests_per_minute=requests_per_minute or self._default_config.requests_per_minute,
            burst_size=burst_size or self._default_config.burst_size,
            enabled=enabled,
        )
        self._connector_configs[connector_name] = config
        logger.info(
            "Configured rate limit for connector '%s': %s rpm, burst=%s, enabled=%s",
            sanitize_for_log(connector_name),
            sanitize_for_log(config.requests_per_minute),
            sanitize_for_log(config.burst_size),
            sanitize_for_log(config.enabled),
        )

    def remove_connector(self, connector_name: str) -> None:
        """
        Remove rate limit configuration for a connector.

        Args:
            connector_name: Name of the connector
        """
        self._connector_configs.pop(connector_name, None)
        self._request_times.pop(connector_name, None)
        self._locks.pop(connector_name, None)
        logger.info(
            "Removed rate limit configuration for connector '%s'", sanitize_for_log(connector_name)
        )

    def get_config(self, connector_name: str) -> RateLimitConfig:
        """
        Get rate limit configuration for a connector.

        Args:
            connector_name: Name of the connector

        Returns:
            RateLimitConfig for the connector (or default)
        """
        return self._connector_configs.get(connector_name, self._default_config)

    async def check_rate_limit(self, connector_name: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed under rate limiting.

        Args:
            connector_name: Name of the connector

        Returns:
            Tuple of (is_allowed, headers_dict)
            headers_dict contains X-RateLimit-* headers
        """
        config = self.get_config(connector_name)

        # If rate limiting is disabled, always allow
        if not config.enabled:
            return True, {
                "X-RateLimit-Limit": config.requests_per_minute,
                "X-RateLimit-Remaining": -1,  # Unlimited
                "X-RateLimit-Reset": 0,
            }

        # Get or create lock for this connector
        async with self._global_lock:
            if connector_name not in self._locks:
                self._locks[connector_name] = asyncio.Lock()

        lock = self._locks[connector_name]

        async with lock:
            now = time.time()
            window_start = now - 60  # 1 minute window

            # Get or create request times deque
            if connector_name not in self._request_times:
                self._request_times[connector_name] = deque()

            request_times = self._request_times[connector_name]

            # Remove old requests outside the window
            while request_times and request_times[0] < window_start:
                request_times.popleft()

            current_count = len(request_times)
            remaining = max(0, config.requests_per_minute - current_count)

            # Calculate reset time (when oldest request expires)
            reset_at = int(request_times[0] + 60 - now) if request_times else 60

            headers = {
                "X-RateLimit-Limit": config.requests_per_minute,
                "X-RateLimit-Remaining": remaining,
                "X-RateLimit-Reset": reset_at,
            }

            # Check if under limit or within burst
            if current_count < config.requests_per_minute:
                request_times.append(now)
                return True, headers

            # Check burst allowance
            burst_used = current_count - config.requests_per_minute
            if burst_used < config.burst_size:
                request_times.append(now)
                headers["X-RateLimit-Remaining"] = 0
                return True, headers

            # Rate limit exceeded
            headers["X-RateLimit-Remaining"] = 0
            headers["Retry-After"] = reset_at
            return False, headers

    def get_status(self, connector_name: str) -> Optional[Dict[str, Any]]:
        """
        Get rate limit status for a connector.

        Args:
            connector_name: Name of the connector

        Returns:
            Dictionary with rate limit status or None if not configured
        """
        config = self.get_config(connector_name)
        request_times = self._request_times.get(connector_name, deque())

        now = time.time()
        window_start = now - 60

        # Count requests in current window
        current_requests = sum(1 for t in request_times if t >= window_start)

        return {
            "connector_name": connector_name,
            "requests_per_minute": config.requests_per_minute,
            "burst_size": config.burst_size,
            "enabled": config.enabled,
            "current_requests": current_requests,
            "remaining": max(0, config.requests_per_minute - current_requests),
            "reset_at": int(list(request_times)[0] + 60 - now) if request_times else 60,
        }

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get rate limit status for all configured connectors.

        Returns:
            Dictionary mapping connector names to their status
        """
        result = {}
        for connector_name in self._connector_configs:
            status = self.get_status(connector_name)
            if status:
                result[connector_name] = status
        return result

    def clear(self) -> None:
        """Clear all rate limit state (for testing)."""
        self._connector_configs.clear()
        self._request_times.clear()
        self._locks.clear()


# Global rate limiter instance
_rate_limiter: Optional[MCPConnectorRateLimiter] = None


def get_connector_rate_limiter() -> MCPConnectorRateLimiter:
    """
    Get the global connector rate limiter instance.

    Returns:
        MCPConnectorRateLimiter singleton
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = MCPConnectorRateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Reset the global rate limiter (for testing)."""
    global _rate_limiter
    if _rate_limiter:
        _rate_limiter.clear()
    _rate_limiter = None
