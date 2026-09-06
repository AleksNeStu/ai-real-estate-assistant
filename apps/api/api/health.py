"""
Enhanced health check module with dependency verification.

Provides comprehensive health status including:
- API status
- Vector store availability
- Database connectivity
- Redis cache (optional)
- LLM provider availability
- Service version and git commit info
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from fastapi import HTTPException, status

from api.dependencies import get_vector_store
from config.settings import get_settings
from core.circuit_breaker import get_all_breaker_states

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class DependencyHealth:
    """Health status of a single dependency."""

    name: str
    status: HealthStatus
    message: str
    latency_ms: Optional[float] = None
    details: Optional[dict[str, Any]] = None


@dataclass
class HealthCheckResponse:
    """Comprehensive health check response."""

    status: HealthStatus
    version: str
    timestamp: str
    dependencies: dict[str, DependencyHealth]
    uptime_seconds: float
    request_id: Optional[str] = None


# Application start time
_start_time: datetime = datetime.now(tz=UTC)


async def check_vector_store() -> DependencyHealth:
    """
    Check vector store health.

    Returns:
        DependencyHealth with vector store status
    """
    start = asyncio.get_event_loop().time()
    try:
        vector_store = await asyncio.to_thread(get_vector_store)
        if vector_store is None:
            return DependencyHealth(
                name="vector_store",
                status=HealthStatus.UNHEALTHY,
                message="Vector store not initialized",
                latency_ms=None,
            )

        # Try a simple query to verify connectivity
        # This will vary based on your vector store implementation
        # For ChromaDB, we can check if the collection exists
        latency_ms = (asyncio.get_event_loop().time() - start) * 1000

        # Check if we can access the store
        try:
            # ChromaDB collection operations are synchronous, so keep them
            # off the event loop used to serve health probes.
            if hasattr(vector_store, "_collection"):
                count = await asyncio.to_thread(vector_store._collection.count)
                return DependencyHealth(
                    name="vector_store",
                    status=HealthStatus.HEALTHY,
                    message=f"OK ({count} items indexed)",
                    latency_ms=latency_ms,
                    details={"item_count": count},
                )
            return DependencyHealth(
                name="vector_store",
                status=HealthStatus.HEALTHY,
                message="OK",
                latency_ms=latency_ms,
            )
        except Exception as e:
            return DependencyHealth(
                name="vector_store",
                status=HealthStatus.DEGRADED,
                message=f"Accessible but error checking: {str(e)[:100]}",
                latency_ms=latency_ms,
            )

    except Exception as e:
        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
        return DependencyHealth(
            name="vector_store",
            status=HealthStatus.UNHEALTHY,
            message=f"Error: {str(e)[:100]}",
            latency_ms=latency_ms,
        )


async def check_redis() -> Optional[DependencyHealth]:
    """
    Check Redis cache health (if enabled).

    Returns:
        DependencyHealth with Redis status, or None if not configured
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None

    start = asyncio.get_event_loop().time()
    try:
        # Try to connect to Redis and ping
        import redis

        client = redis.from_url(redis_url, decode_responses=True)
        await asyncio.to_thread(client.ping)
        client.close()

        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
        return DependencyHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="OK",
            latency_ms=latency_ms,
        )
    except ImportError:
        return DependencyHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            message="Redis configured but redis-py not installed",
            latency_ms=None,
        )
    except Exception as e:
        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
        return DependencyHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Error: {str(e)[:100]}",
            latency_ms=latency_ms,
        )


async def check_llm_provider() -> DependencyHealth:
    """
    Check LLM provider availability.

    Returns:
        DependencyHealth with LLM provider status
    """
    start = asyncio.get_event_loop().time()
    settings = get_settings()

    # Check if at least one provider API key is configured
    providers = []
    if settings.openai_api_key:
        providers.append("openai")
    if settings.anthropic_api_key:
        providers.append("anthropic")
    if settings.google_api_key:
        providers.append("google")
    if settings.grok_api_key:
        providers.append("grok")
    if settings.deepseek_api_key:
        providers.append("deepseek")

    # Check Ollama availability
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_available = False
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            ollama_available = response.status_code == 200
    except Exception:
        pass

    if ollama_available:
        providers.append("ollama")

    latency_ms = (asyncio.get_event_loop().time() - start) * 1000

    if not providers:
        return DependencyHealth(
            name="llm_providers",
            status=HealthStatus.DEGRADED,
            message="No LLM providers configured (set at least one API key)",
            latency_ms=latency_ms,
            details={"configured_providers": []},
        )

    return DependencyHealth(
        name="llm_providers",
        status=HealthStatus.HEALTHY,
        message=f"OK ({len(providers)} provider(s) available)",
        latency_ms=latency_ms,
        details={
            "configured_providers": providers,
            "default": settings.default_provider,
        },
    )


async def check_database() -> Optional[DependencyHealth]:
    """
    Check database connectivity (SQLite or PostgreSQL).

    Returns:
        DependencyHealth with database status, or None if not configured
    """
    start = asyncio.get_event_loop().time()
    settings = get_settings()

    db_url = settings.database_url or os.getenv("DATABASE_URL")
    if not db_url:
        return None  # Database not configured

    try:
        from sqlalchemy import text

        from db.database import get_engine

        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
        return DependencyHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="OK",
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
        return DependencyHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Error: {str(e)[:100]}",
            latency_ms=latency_ms,
        )


def get_git_info() -> dict[str, str]:
    """
    Get git commit information.

    Returns:
        Dict with commit hash, branch, and timestamp
    """
    git_info = {"commit": "unknown", "branch": "unknown", "timestamp": "unknown"}

    try:
        import subprocess

        # Get current commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            git_info["commit"] = result.stdout.strip()[:8]

        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            git_info["branch"] = result.stdout.strip()

        # Get commit timestamp
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            git_info["timestamp"] = result.stdout.strip()

    except Exception as e:
        logger.debug("Could not get git info: %s", e)

    return git_info


async def _bounded_dependency_check(
    check: Any,
    name: str,
    timeout_seconds: float = 4.0,
) -> Optional[DependencyHealth]:
    """Run one dependency check without letting it stall the health endpoint."""
    try:
        return await asyncio.wait_for(check(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning("Health check timed out: %s", name)
        return DependencyHealth(
            name=name,
            status=HealthStatus.DEGRADED,
            message=f"Timed out after {timeout_seconds:.1f}s",
        )
    except Exception as e:
        logger.error("Health check error for %s: %s", name, e)
        return None


async def get_health_status(include_dependencies: bool = True) -> HealthCheckResponse:
    """
    Get comprehensive health status.

    Args:
        include_dependencies: Whether to check dependency health

    Returns:
        HealthCheckResponse with comprehensive status
    """
    settings = get_settings()
    dependencies: dict[str, DependencyHealth] = {}

    if include_dependencies:
        # Check all dependencies in parallel; each has its own bounded budget
        # so a slow dependency cannot hold the entire /health response.
        results = await asyncio.gather(
            _bounded_dependency_check(check_vector_store, "vector_store", 4.0),
            _bounded_dependency_check(check_redis, "redis", 2.0),
            _bounded_dependency_check(check_database, "database", 4.0),
            _bounded_dependency_check(check_llm_provider, "llm_providers", 2.0),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error("Health check error: %s", result)
                continue
            if result is None:
                continue
            health_result: DependencyHealth = result  # type: ignore[assignment]
            dependencies[health_result.name] = health_result

    # Include circuit breaker states (Task #96)
    breaker_states = get_all_breaker_states()
    circuit_breakers: dict[str, DependencyHealth] = {}
    for name, state in breaker_states.items():
        breaker_status = HealthStatus.HEALTHY
        if state["state"] == "open":
            breaker_status = HealthStatus.UNHEALTHY
        elif state["state"] == "half_open":
            breaker_status = HealthStatus.DEGRADED
        circuit_breakers[name] = DependencyHealth(
            name=f"circuit_breaker:{name}",
            status=breaker_status,
            message=f"State: {state['state']}, failures: {state['total_failures']}/{state['total_calls']}",
            details=state,
        )
    dependencies.update(circuit_breakers)

    # Determine overall status
    # - UNHEALTHY if any critical dependency is unhealthy
    # - DEGRADED if any non-critical dependency is unhealthy or circuit breaker is open
    # - HEALTHY otherwise
    critical_unhealthy = any(
        d.status == HealthStatus.UNHEALTHY and d.name in {"vector_store"}
        for d in dependencies.values()
    )
    any_unhealthy = any(d.status == HealthStatus.UNHEALTHY for d in dependencies.values())
    any_degraded = any(d.status == HealthStatus.DEGRADED for d in dependencies.values())

    if critical_unhealthy:
        overall_status = HealthStatus.UNHEALTHY
    elif any_unhealthy or any_degraded:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY

    # Calculate uptime
    uptime = (datetime.now(tz=UTC) - _start_time).total_seconds()

    return HealthCheckResponse(
        status=overall_status,
        version=settings.version,
        timestamp=datetime.now(tz=UTC).isoformat(),
        dependencies=dependencies,
        uptime_seconds=uptime,
    )


async def require_healthy(dependencies: Optional[list[str]] = None) -> None:
    """
    Require that specified dependencies are healthy.

    Raises HTTPException if any required dependency is unhealthy.

    Args:
        dependencies: List of dependency names to check. If None, checks all.

    Raises:
        HTTPException: 503 if any required dependency is unhealthy
    """
    health = await get_health_status(include_dependencies=True)

    if health.status == HealthStatus.UNHEALTHY:
        # Find unhealthy dependencies
        unhealthy_deps = [
            name
            for name, dep in health.dependencies.items()
            if dep.status == HealthStatus.UNHEALTHY
        ]

        if dependencies:
            # Filter to only requested dependencies
            unhealthy_deps = [d for d in unhealthy_deps if d in dependencies]

        if unhealthy_deps:
            deps_list = ", ".join(unhealthy_deps)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service unavailable due to unhealthy dependencies: {deps_list}",
            )
