"""
Response caching layer for API endpoints with Redis backend.

This module provides production-ready response caching with:
- Redis-backed distributed cache
- Cache key generation based on request parameters
- TTL-based cache invalidation
- Cache warming for frequently accessed data
- Graceful fallback to in-memory cache when Redis is unavailable
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from fastapi import Request

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheConfig:
    """Configuration for response caching."""

    enabled: bool = True
    ttl_seconds: int = 300  # 5 minutes default
    prefix: str = "api_cache"
    max_memory_mb: int = 100
    include_headers: bool = True
    stale_while_revalidate: bool = False
    stale_ttl_seconds: int = 600  # 10 minutes


@dataclass
class CacheEntry:
    """A cached response entry."""

    data: dict[str, Any]
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    cached_at: float = field(default_factory=time.time)
    ttl: int = 300

    def is_expired(self, now: float | None = None) -> bool:
        """Check if the cache entry is expired."""
        if now is None:
            now = time.time()
        return (now - self.cached_at) > self.ttl

    def is_stale(self, now: float | None = None) -> bool:
        """Check if the cache entry is stale (for stale-while-revalidate)."""
        if now is None:
            now = time.time()
        return (now - self.cached_at) > (self.ttl * 2)

    def age_seconds(self, now: float | None = None) -> float:
        """Get the age of the cache entry in seconds."""
        if now is None:
            now = time.time()
        return now - self.cached_at


class InMemoryCache:
    """Simple in-memory cache as fallback when Redis is unavailable."""

    def __init__(self, max_size: int = 1000) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = None

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get a cache entry."""
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            return entry
        if entry and entry.is_expired():
            del self._cache[key]
        return None

    def set(self, key: str, entry: CacheEntry) -> None:
        """Set a cache entry."""
        # Simple LRU: if at capacity, delete oldest entries
        if len(self._cache) >= self._max_size and key not in self._cache:
            # Delete 10% of entries to make room
            to_delete = int(self._max_size * 0.1) + 1
            oldest_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k].cached_at,
            )[:to_delete]
            for k in oldest_keys:
                del self._cache[k]

        self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        return self._cache.pop(key, None) is not None

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def size(self) -> int:
        """Get the number of cached entries."""
        return len(self._cache)


class RedisCache:
    """Redis-backed distributed cache."""

    def __init__(
        self,
        redis_url: str,
        prefix: str = "api_cache",
        fallback_to_in_memory: bool = True,
    ) -> None:
        self._redis_url = redis_url
        self._prefix = prefix
        self._fallback_to_in_memory = fallback_to_in_memory
        self._fallback_cache: Optional[InMemoryCache] = None
        self._redis_client: Optional[Any] = None
        self._use_redis = False

        self._init_redis()

    def _init_redis(self) -> bool:
        """Initialize Redis connection."""
        try:
            import redis

            self._redis_client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            # Test connection
            self._redis_client.ping()
            self._use_redis = True
            logger.info("Redis response cache initialized successfully")
            return True
        except ImportError:
            logger.warning("Redis Python package not installed, using in-memory cache")
            if self._fallback_to_in_memory:
                self._fallback_cache = InMemoryCache()
            return False
        except Exception as e:
            logger.warning("Redis connection failed: %s. Using in-memory cache", e)
            if self._fallback_to_in_memory:
                self._fallback_cache = InMemoryCache()
            return False

    def _make_key(self, key: str) -> str:
        """Create a prefixed Redis key."""
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get a cache entry."""
        redis_key = self._make_key(key)

        if self._use_redis and self._redis_client:
            try:
                data = self._redis_client.get(redis_key)
                if data:
                    entry_dict = json.loads(data)
                    entry = CacheEntry(**entry_dict)
                    if not entry.is_expired():
                        return entry
                    # Remove expired entry
                    self._redis_client.delete(redis_key)
                    return None
            except Exception as e:
                logger.warning("Redis get failed: %s. Falling back to in-memory", e)
                if self._fallback_cache:
                    return self._fallback_cache.get(key)

        # Fall back to in-memory cache
        if self._fallback_cache:
            return self._fallback_cache.get(key)

        return None

    def set(self, key: str, entry: CacheEntry, ttl: Optional[int] = None) -> None:
        """Set a cache entry."""
        redis_key = self._make_key(key)
        ttl_seconds = ttl or entry.ttl

        if self._use_redis and self._redis_client:
            try:
                entry_dict = {
                    "data": entry.data,
                    "status_code": entry.status_code,
                    "headers": entry.headers,
                    "cached_at": entry.cached_at,
                    "ttl": entry.ttl,
                }
                data = json.dumps(entry_dict)
                self._redis_client.setex(redis_key, ttl_seconds, data)
                return
            except Exception as e:
                logger.warning("Redis set failed: %s. Falling back to in-memory", e)
                if self._fallback_cache:
                    self._fallback_cache.set(key, entry)
                    return

        # Fall back to in-memory cache
        if self._fallback_cache:
            self._fallback_cache.set(key, entry)

    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        redis_key = self._make_key(key)
        deleted = False

        if self._use_redis and self._redis_client:
            try:
                deleted = self._redis_client.delete(redis_key) > 0
            except Exception as e:
                logger.warning("Redis delete failed: %s", e)

        if self._fallback_cache:
            deleted = self._fallback_cache.delete(key) or deleted

        return deleted

    def clear(self) -> None:
        """Clear all cache entries with the prefix."""
        if self._use_redis and self._redis_client:
            try:
                pattern = f"{self._prefix}:*"
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as e:
                logger.warning("Redis clear failed: %s", e)

        if self._fallback_cache:
            self._fallback_cache.clear()

    def size(self) -> int:
        """Get the number of cached entries."""
        if self._use_redis and self._redis_client:
            try:
                pattern = f"{self._prefix}:*"
                keys = self._redis_client.keys(pattern)
                return len(keys) if keys else 0
            except Exception:
                pass

        if self._fallback_cache:
            return self._fallback_cache.size()

        return 0


class ResponseCache:
    """
    Response cache manager that supports Redis and in-memory fallback.
    """

    def __init__(
        self,
        config: CacheConfig,
        redis_url: Optional[str] = None,
    ) -> None:
        self._config = config
        self._backend: Optional[RedisCache | InMemoryCache] = None
        self._hits: int = 0
        self._misses: int = 0
        # Secondary index: path prefix -> set of cache keys for targeted invalidation
        self._prefix_index: dict[str, set[str]] = {}

        if redis_url and config.enabled:
            self._backend = RedisCache(
                redis_url=redis_url,
                prefix=config.prefix,
                fallback_to_in_memory=True,
            )
        elif config.enabled:
            self._backend = InMemoryCache()

    def _generate_cache_key(
        self,
        request: Request,
        body_hash: Optional[str] = None,
    ) -> str:
        """
        Generate a cache key based on request parameters.

        Includes method, path, query params, and (optionally) request body.
        """
        parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items())),
        ]

        if body_hash:
            parts.append(body_hash)

        key_string = ":".join(parts)
        # nosemgrep: py/weak-sensitive-data-hashing - truncated hash for cache key, not security
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

    def _hash_request_body(self, body: bytes | str) -> str:
        """Hash request body for cache key generation."""
        if isinstance(body, str):
            body = body.encode("utf-8")
        # nosemgrep: py/weak-sensitive-data-hashing - truncated hash for cache key, not security
        return hashlib.sha256(body).hexdigest()[:16]

    @staticmethod
    def _path_prefix(path: str) -> str:
        """Extract path prefix for index grouping (e.g., /api/v1/search from /api/v1/search?x=1)."""
        # Group by first 3 path segments: /api/v1/<resource>
        parts = path.strip("/").split("/")
        return "/" + "/".join(parts[:3]) if len(parts) >= 3 else path

    async def get(
        self,
        request: Request,
        body_hash: Optional[str] = None,
    ) -> Optional[CacheEntry]:
        """Get cached response for a request."""
        if not self._backend or not self._config.enabled:
            return None

        key = self._generate_cache_key(request, body_hash)
        entry = self._backend.get(key)

        if entry:
            self._hits += 1
            logger.debug(
                "Cache HIT: %s %s (age: %.1fs)",
                request.method,
                request.url.path,
                entry.age_seconds(),
            )
            return entry

        self._misses += 1
        logger.debug("Cache MISS: %s %s", request.method, request.url.path)
        return None

    async def set(
        self,
        request: Request,
        data: dict[str, Any],
        status_code: int = 200,
        headers: Optional[dict[str, str]] = None,
        body_hash: Optional[str] = None,
    ) -> None:
        """Cache a response."""
        if not self._backend or not self._config.enabled:
            return

        key = self._generate_cache_key(request, body_hash)
        entry = CacheEntry(
            data=data,
            status_code=status_code,
            headers=headers or {},
            ttl=self._config.ttl_seconds,
        )

        self._backend.set(key, entry)

        # Track key by path prefix for targeted invalidation
        prefix = self._path_prefix(request.url.path)
        if prefix not in self._prefix_index:
            self._prefix_index[prefix] = set()
        self._prefix_index[prefix].add(key)
        logger.debug(
            "Cached response for %s %s (TTL: %ds)", request.method, request.url.path, entry.ttl
        )

    async def delete(self, request: Request, body_hash: Optional[str] = None) -> bool:
        """Delete cached response for a request."""
        if not self._backend:
            return False

        key = self._generate_cache_key(request, body_hash)
        return self._backend.delete(key)

    async def clear_all(self) -> None:
        """Clear all cached responses."""
        if self._backend:
            self._backend.clear()
            self._prefix_index.clear()
            logger.info("Cleared all cached responses")

    def invalidate_by_prefix(self, path_prefix: str) -> int:
        """
        Invalidate all cache entries for paths starting with a prefix.

        Uses the secondary index for targeted invalidation — only removes entries
        matching the given path prefix, leaving other cached data intact.
        """
        if not self._backend:
            return 0

        deleted = 0
        # Find all indexed prefixes that start with the given path_prefix
        keys_to_delete: set[str] = set()
        for prefix, keys in list(self._prefix_index.items()):
            if prefix.startswith(path_prefix) or path_prefix.startswith(prefix):
                keys_to_delete.update(keys)
                if prefix.startswith(path_prefix):
                    del self._prefix_index[prefix]

        for key in keys_to_delete:
            if self._backend.delete(key):
                deleted += 1

        logger.info("Invalidated %d cache entries for path prefix: %s", deleted, path_prefix)
        return deleted

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self._backend:
            return {"enabled": False, "backend": "none"}

        return {
            "enabled": True,
            "backend": "redis" if isinstance(self._backend, RedisCache) else "memory",
            "size": self._backend.size(),
            "ttl_seconds": self._config.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / (self._hits + self._misses)
            if (self._hits + self._misses) > 0
            else 0.0,
        }


def cached_response(
    ttl_seconds: int = 300,
    include_headers: bool = True,
) -> Callable:
    """
    Decorator to cache FastAPI endpoint responses.

    Usage:
        @router.get("/properties")
        @cached_response(ttl_seconds=60)
        async def get_properties(...):
            ...

    Args:
        ttl_seconds: Time-to-live for cached responses
        include_headers: Whether to include response headers in cache key

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Try to get request from kwargs (FastAPI dependency injection)
            request: Optional[Request] = kwargs.get("request")
            if not request:
                # Try to get request from args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # Get cache from app state
            cache: Optional[ResponseCache] = None
            if request and hasattr(request.app.state, "response_cache"):
                cache = request.app.state.response_cache

            # Check cache
            if cache and request:
                cached = await cache.get(request)
                if cached:
                    return cached.data  # type: ignore[return-value]

            # Execute original function
            result: T = await func(*args, **kwargs)  # type: ignore[misc]

            # Cache result. Preserve the response shape so FastAPI's
            # response_model validation passes on cache hits: dicts and
            # Pydantic models go in as-is (model_dump if available), and
            # lists are stored directly. Only wrap in {"data": ...} as a
            # last resort for unrecognized return types -- the previous
            # behavior of always wrapping Pydantic models in {"data":
            # model} caused ResponseValidationError on cache hits because
            # the outer dict lacked the model's declared fields.
            if cache and request:
                if isinstance(result, (dict, list)):
                    data = result
                elif hasattr(result, "model_dump"):
                    data = result.model_dump()
                else:
                    data = {"data": result}
                await cache.set(
                    request,
                    data=data,
                    status_code=200,
                )

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
