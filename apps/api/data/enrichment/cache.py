"""
Enrichment Cache (Task #78).

This module provides TTL-based caching for enrichment results,
following the ResponseCache pattern from apps/api/utils/response_cache.py.

Features:
- Redis-backed with in-memory fallback
- Per-enrichment TTL configuration
- Stale-while-revalidate support
- Thread-safe operations
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached enrichment entry."""

    value: Any
    source: str
    enrichment_field: str
    cached_at: float
    ttl: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL."""
        return time.time() - self.cached_at > self.ttl

    def is_stale(self) -> bool:
        """Check if entry is stale (past 80% of TTL)."""
        age = time.time() - self.cached_at
        return age > self.ttl * 0.8

    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.cached_at

    def remaining_ttl(self) -> int:
        """Get remaining TTL in seconds."""
        remaining = self.ttl - int(self.age_seconds())
        return max(0, remaining)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "value": self.value,
            "source": self.source,
            "field": self.enrichment_field,
            "cached_at": self.cached_at,
            "ttl": self.ttl,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            value=data["value"],
            source=data["source"],
            enrichment_field=data["field"],
            cached_at=data["cached_at"],
            ttl=data["ttl"],
            metadata=data.get("metadata", {}),
        )


class InMemoryEnrichmentCache:
    """In-memory cache for enrichment results."""

    def __init__(self, max_size: int = 10000):
        """
        Initialize in-memory cache.

        Args:
            max_size: Maximum number of entries
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.is_expired():
                del self._cache[key]
                return None
            return entry

    def set(self, key: str, entry: CacheEntry) -> None:
        """Set entry in cache."""
        with self._lock:
            # Evict expired entries if at capacity
            if len(self._cache) >= self._max_size:
                self._evict_expired()
                if len(self._cache) >= self._max_size:
                    self._evict_oldest()

            self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()

    def _evict_expired(self) -> None:
        """Remove expired entries."""
        expired = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired:
            del self._cache[key]

    def _evict_oldest(self) -> None:
        """Evict oldest 10% of entries."""
        if not self._cache:
            return
        sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k].cached_at)
        evict_count = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:evict_count]:
            del self._cache[key]


class EnrichmentCache:
    """
    Redis-backed cache for enrichment results with in-memory fallback.

    Uses the same pattern as ResponseCache for consistency.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        prefix: str = "enrichment",
        fallback_to_in_memory: bool = True,
    ):
        """
        Initialize enrichment cache.

        Args:
            redis_url: Redis connection URL
            prefix: Cache key prefix
            fallback_to_in_memory: Fall back to in-memory if Redis unavailable
        """
        self._prefix = prefix
        self._redis_url = redis_url or os.getenv("CACHE_REDIS_URL") or os.getenv("REDIS_URL")
        self._redis_client: Any = None
        self._fallback_cache: Optional[InMemoryEnrichmentCache] = None
        self._fallback_enabled = fallback_to_in_memory
        self._lock = threading.RLock()

        # Try to connect to Redis
        if self._redis_url:
            self._connect_redis()

        # Initialize fallback cache
        if self._fallback_enabled and not self._redis_client:
            self._fallback_cache = InMemoryEnrichmentCache()

    def _connect_redis(self) -> None:
        """Connect to Redis."""
        try:
            import redis

            self._redis_client = redis.from_url(
                self._redis_url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            # Test connection
            self._redis_client.ping()
            logger.info("EnrichmentCache connected to Redis")
        except Exception as e:
            logger.warning("Failed to connect to Redis: %s", sanitize_for_log(e))
            self._redis_client = None
            if self._fallback_enabled:
                self._fallback_cache = InMemoryEnrichmentCache()

    def _make_key(self, source: str, property_id: str, enrichment_field: str) -> str:
        """Generate cache key."""
        return f"{self._prefix}:{source}:{property_id}:{enrichment_field}"

    def get(
        self,
        source: str,
        property_id: str,
        enrichment_field: str,
    ) -> Optional[CacheEntry]:
        """
        Get cached enrichment result.

        Args:
            source: Enrichment source name
            property_id: Property identifier
            enrichment_field: Field name

        Returns:
            CacheEntry if found and not expired, None otherwise
        """
        key = self._make_key(source, property_id, enrichment_field)

        # Try Redis first
        if self._redis_client:
            try:
                data = self._redis_client.get(key)
                if data:
                    entry = CacheEntry.from_dict(json.loads(data))
                    if not entry.is_expired():
                        return entry
                    else:
                        # Delete expired entry
                        self._redis_client.delete(key)
            except Exception as e:
                logger.warning("Redis get failed: %s", sanitize_for_log(e))

        # Fall back to in-memory
        if self._fallback_cache:
            return self._fallback_cache.get(key)

        return None

    def set(
        self,
        source: str,
        property_id: str,
        enrichment_field: str,
        value: Any,
        ttl: int = 3600,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Cache enrichment result.

        Args:
            source: Enrichment source name
            property_id: Property identifier
            enrichment_field: Field name
            value: Value to cache
            ttl: Time-to-live in seconds
            metadata: Optional metadata

        Returns:
            True if cached successfully
        """
        key = self._make_key(source, property_id, enrichment_field)
        entry = CacheEntry(
            value=value,
            source=source,
            enrichment_field=enrichment_field,
            cached_at=time.time(),
            ttl=ttl,
            metadata=metadata or {},
        )

        # Try Redis first
        if self._redis_client:
            try:
                self._redis_client.setex(
                    key,
                    ttl,
                    json.dumps(entry.to_dict()),
                )
                return True
            except Exception as e:
                logger.warning("Redis set failed: %s", sanitize_for_log(e))

        # Fall back to in-memory
        if self._fallback_cache:
            self._fallback_cache.set(key, entry)
            return True

        return False

    def delete(
        self,
        source: str,
        property_id: str,
        enrichment_field: str,
    ) -> bool:
        """
        Delete cached enrichment result.

        Args:
            source: Enrichment source name
            property_id: Property identifier
            enrichment_field: Field name

        Returns:
            True if deleted
        """
        key = self._make_key(source, property_id, enrichment_field)
        deleted = False

        if self._redis_client:
            try:
                deleted = bool(self._redis_client.delete(key))
            except Exception as e:
                logger.warning("Redis delete failed: %s", sanitize_for_log(e))

        if self._fallback_cache:
            deleted = self._fallback_cache.delete(key) or deleted

        return deleted

    def invalidate_property(self, property_id: str) -> int:
        """
        Invalidate all cached enrichments for a property.

        Args:
            property_id: Property identifier

        Returns:
            Number of entries invalidated
        """
        count = 0
        pattern = f"{self._prefix}:*:{property_id}:*"

        if self._redis_client:
            try:
                keys = self._redis_client.keys(pattern)
                if keys:
                    count = self._redis_client.delete(*keys)
            except Exception as e:
                logger.warning("Redis invalidate failed: %s", sanitize_for_log(e))

        # For in-memory cache, we need to iterate
        if self._fallback_cache:
            with self._fallback_cache._lock:
                keys_to_delete = [
                    k for k in self._fallback_cache._cache.keys() if f":{property_id}:" in k
                ]
                for key in keys_to_delete:
                    del self._fallback_cache._cache[key]
                    count += 1

        return count

    def clear(self) -> None:
        """Clear all cached entries."""
        if self._redis_client:
            try:
                keys = self._redis_client.keys(f"{self._prefix}:*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as e:
                logger.warning("Redis clear failed: %s", sanitize_for_log(e))

        if self._fallback_cache:
            self._fallback_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "redis_enabled": self._redis_client is not None,
            "fallback_enabled": self._fallback_cache is not None,
            "prefix": self._prefix,
        }

        if self._fallback_cache:
            with self._fallback_cache._lock:
                stats["in_memory_entries"] = len(self._fallback_cache._cache)

        return stats


# Global cache instance
_cache: Optional[EnrichmentCache] = None
_cache_lock = threading.Lock()


def get_enrichment_cache() -> EnrichmentCache:
    """
    Get the global enrichment cache instance.

    Returns:
        EnrichmentCache instance
    """
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                _cache = EnrichmentCache()
    return _cache


def clear_cache() -> None:
    """Clear the global cache (for testing)."""
    global _cache
    if _cache:
        _cache.clear()
    _cache = None
