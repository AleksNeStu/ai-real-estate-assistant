import inspect
import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from threading import Lock
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.security_utils import hash_fingerprint

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

_RATE_LIMIT_EXCLUDED_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


class RedisRateLimiter:
    """
    Redis-backed distributed rate limiter.

    Provides rate limiting across multiple instances using Redis as the backing store.
    Falls back to in-memory rate limiting if Redis is unavailable.
    """

    def __init__(
        self,
        redis_url: str,
        max_requests: int = 600,
        window_seconds: int = 60,
        fallback_to_in_memory: bool = True,
    ) -> None:
        """
        Initialize Redis rate limiter.

        Args:
            redis_url: Redis connection URL
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            fallback_to_in_memory: Whether to fall back to in-memory if Redis fails
        """
        self._redis_url = redis_url
        self._max_requests = max(1, int(max_requests))
        self._window_seconds = max(1, int(window_seconds))
        self._fallback_to_in_memory = fallback_to_in_memory
        self._fallback_limiter: Optional[RateLimiter] = None
        self._redis_client: Optional[Any] = None
        self._use_redis = False

        # Try to initialize Redis connection
        self._init_redis()

    def _init_redis(self) -> bool:
        """Initialize Redis connection. Returns True if successful."""
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
            logging.info("Redis rate limiter initialized successfully")
            return True

        except ImportError:
            logging.warning("Redis Python package not installed, using in-memory rate limiting")
            if self._fallback_to_in_memory:
                self._fallback_limiter = RateLimiter(self._max_requests, self._window_seconds)
            return False

        except Exception as e:
            logging.warning("Redis connection failed: %s. Using in-memory rate limiting", e)
            if self._fallback_to_in_memory:
                self._fallback_limiter = RateLimiter(self._max_requests, self._window_seconds)
            return False

    def configure(self, max_requests: int, window_seconds: int) -> None:
        """Update rate limit configuration."""
        self._max_requests = max(1, int(max_requests))
        self._window_seconds = max(1, int(window_seconds))
        if self._fallback_limiter:
            self._fallback_limiter.configure(max_requests, window_seconds)

    def reset(self) -> None:
        """Reset rate limiter state."""
        if self._fallback_limiter:
            self._fallback_limiter.reset()

    def check(self, key: str, now: float | None = None) -> tuple[bool, int, int, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Client identifier
            now: Current time (for testing)

        Returns:
            Tuple of (allowed, limit, remaining, reset_in_seconds)
        """
        ts = time.time() if now is None else now
        key = key or "anonymous"

        # Use Redis if available
        if self._use_redis and self._redis_client:
            try:
                return self._check_redis(key, ts)
            except Exception as e:
                logging.warning("Redis rate limit check failed: %s. Falling back to in-memory", e)
                if self._fallback_limiter:
                    return self._fallback_limiter.check(key, now)

        # Fall back to in-memory
        if self._fallback_limiter:
            return self._fallback_limiter.check(key, now)

        # If no fallback available, allow all requests
        return True, self._max_requests, self._max_requests, 0

    def _check_redis(self, key: str, ts: float) -> tuple[bool, int, int, int]:
        """Check rate limit using Redis."""

        redis_key = f"ratelimit:{key}"
        assert self._redis_client is not None, "Redis client should be initialized for _check_redis"
        pipe = self._redis_client.pipeline()

        window_start = ts - self._window_seconds

        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, window_start)

        # Count current requests
        pipe.zcard(redis_key)

        # Add current request
        pipe.zadd(redis_key, {str(ts): ts})

        # Set expiration
        pipe.expire(redis_key, self._window_seconds + 10)

        results = pipe.execute()
        current_count = results[1]

        if current_count >= self._max_requests:
            # Get oldest timestamp to calculate reset time
            assert self._redis_client is not None, "Redis client should be initialized"
            oldest = self._redis_client.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_ts = float(oldest[0][1])
                reset_in = max(1, int((oldest_ts + self._window_seconds) - ts))
            else:
                reset_in = self._window_seconds

            return False, self._max_requests, 0, reset_in

        remaining = self._max_requests - current_count

        # Get oldest timestamp for reset time calculation
        assert self._redis_client is not None, "Redis client should be initialized"
        oldest = self._redis_client.zrange(redis_key, 0, 0, withscores=True)
        if oldest:
            oldest_ts = float(oldest[0][1])
            reset_in = max(1, int((oldest_ts + self._window_seconds) - ts))
        else:
            reset_in = self._window_seconds

        return True, self._max_requests, remaining, reset_in


class RateLimiter:
    def __init__(self, max_requests: int = 600, window_seconds: int = 60) -> None:
        self._max_requests = max(1, int(max_requests))
        self._window_seconds = max(1, int(window_seconds))
        self._lock = Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def configure(self, max_requests: int, window_seconds: int) -> None:
        with self._lock:
            self._max_requests = max(1, int(max_requests))
            self._window_seconds = max(1, int(window_seconds))

    def reset(self) -> None:
        with self._lock:
            self._events.clear()

    def check(self, key: str, now: float | None = None) -> tuple[bool, int, int, int]:
        ts = time.time() if now is None else now
        key = key or "anonymous"

        with self._lock:
            window_start = ts - self._window_seconds
            q = self._events[key]

            while q and q[0] <= window_start:
                q.popleft()

            if len(q) >= self._max_requests:
                oldest = q[0] if q else ts
                reset_in = max(1, int((oldest + self._window_seconds) - ts))
                return False, self._max_requests, 0, reset_in

            q.append(ts)
            remaining = max(0, self._max_requests - len(q))
            oldest = q[0] if q else ts
            reset_in = max(1, int((oldest + self._window_seconds) - ts))
            return True, self._max_requests, remaining, reset_in


def normalize_request_id(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if _REQUEST_ID_RE.fullmatch(candidate) is None:
        return None
    return candidate


def generate_request_id() -> str:
    return uuid.uuid4().hex


def client_id_from_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    return hash_fingerprint(api_key, length=12)


def add_observability(app: FastAPI, logger: logging.Logger) -> None:
    # Initialize rate limiter - use Redis if available, otherwise in-memory
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        limiter: RateLimiter | RedisRateLimiter = RedisRateLimiter(
            redis_url=redis_url,
            fallback_to_in_memory=True,
        )
        logger.info("Using Redis-backed rate limiter")
    else:
        limiter = RateLimiter()
        logger.info("Using in-memory rate limiter")

    app.state.rate_limiter = limiter  # type: ignore[assignment]
    metrics: dict[str, int] = {}
    app.state.metrics = metrics  # type: ignore[assignment]

    @app.middleware("http")
    async def _request_id_middleware(request: Request, call_next):
        from config.settings import get_settings

        settings = get_settings()

        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        if request_id is None:
            request_id = generate_request_id()

        request.state.request_id = request_id
        response_headers = {REQUEST_ID_HEADER: request_id}

        if getattr(settings, "api_rate_limit_enabled", False):
            path = request.url.path
            excluded = _RATE_LIMIT_EXCLUDED_PREFIXES
            if path.startswith("/api/v1") and not path.startswith(excluded):
                api_key = request.headers.get("X-API-Key")
                client_id = client_id_from_api_key(api_key) or "anonymous"
                rpm = int(getattr(settings, "api_rate_limit_rpm", 600))
                limiter.configure(max_requests=rpm, window_seconds=60)

                allowed, limit, remaining, reset_in = limiter.check(client_id)
                response_headers.update(
                    {
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": str(remaining),
                        "X-RateLimit-Reset": str(reset_in),
                    }
                )

                if not allowed:
                    response_headers["Retry-After"] = str(reset_in)
                    logger.info(
                        "api_rate_limited",
                        extra={
                            "event": "api_rate_limited",
                            "request_id": request_id,
                            "client_id": client_id,
                            "method": request.method,
                            "path": path,
                            "status": 429,
                            "duration_ms": 0.0,
                        },
                    )
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"},
                        headers=response_headers,
                    )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            log_client_id: str | None = client_id_from_api_key(request.headers.get("X-API-Key"))
            logger.exception(
                "api_unhandled_exception",
                extra={
                    "event": "api_unhandled_exception",
                    "request_id": request_id,
                    "client_id": (log_client_id or "-"),
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": float(elapsed_ms),
                },
            )
            key = f"{request.method} {request.url.path}"
            app.state.metrics[key] = int(app.state.metrics.get(key, 0)) + 1
            handler = app.exception_handlers.get(type(exc)) or app.exception_handlers.get(Exception)
            if handler is not None:
                response = handler(request, exc)
                if inspect.isawaitable(response):
                    response = await response
            else:
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error"},
                )
            for k, v in response_headers.items():
                response.headers[k] = v
            return response

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        for k, v in response_headers.items():
            response.headers[k] = v

        log_client_id_success: str | None = client_id_from_api_key(request.headers.get("X-API-Key"))
        logger.info(
            "api_request",
            extra={
                "event": "api_request",
                "request_id": request_id,
                "client_id": (log_client_id_success or "-"),
                "method": request.method,
                "path": request.url.path,
                "status": getattr(response, "status_code", "-"),
                "duration_ms": float(elapsed_ms),
            },
        )

        key = f"{request.method} {request.url.path}"
        app.state.metrics[key] = int(app.state.metrics.get(key, 0)) + 1

        return response
