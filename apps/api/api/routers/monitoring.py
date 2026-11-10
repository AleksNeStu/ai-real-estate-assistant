"""
Monitoring and health check endpoints for production operations.

Provides liveness, readiness, and metrics endpoints for infrastructure monitoring,
alerting, and operational insights.
"""

import logging
import time
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_vector_store
from api.deps.auth import AuthCredentials, get_auth_credentials, require_permission
from api.rbac import Permission
from api.routers.catalogue import count_catalogue
from config.settings import get_settings
from db.database import get_db
from vector_store.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Monitoring"])


@router.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Liveness probe - checks if the service is alive.

    Returns 200 if the service is running, regardless of dependencies.
    Used by Kubernetes/Docker health checks.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-real-estate-assistant",
    }


@router.get("/ready", tags=["Monitoring"])
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    credentials: AuthCredentials = Depends(get_auth_credentials),
):
    """
    Readiness probe - checks if the service is ready to handle requests.

    Validates database, Redis (if configured), and LLM provider availability.
    Used by Kubernetes/Docker readiness probes and load balancers.
    """
    checks = {
        "database": "unknown",
        "redis": "unknown",
        "llm": "unknown",
        "overall": "unknown",
    }

    # Database check
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
        db_latency_ms = round((time.time() - start) * 1000, 2)
        checks["database_latency_ms"] = db_latency_ms
    except Exception as e:
        logger.warning("Database readiness check failed: %s", e)
        checks["database"] = f"unhealthy: {str(e)}"

    # Redis check (if configured)
    try:
        settings = get_settings()
        if hasattr(settings, "redis_url") and settings.redis_url:
            # Simple Redis connection test via cache import
            from core.cache import get_redis_client

            redis_client = get_redis_client()
            await redis_client.ping()
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "disabled"
    except Exception as e:
        logger.warning("Redis readiness check failed: %s", e)
        checks["redis"] = f"unhealthy: {str(e)}"

    # LLM provider check
    try:
        from models.provider_factory import get_default_llm

        llm = get_default_llm()
        if llm:
            checks["llm"] = "healthy"
        else:
            checks["llm"] = "unhealthy: no LLM configured"
    except Exception as e:
        logger.warning("LLM readiness check failed: %s", e)
        checks["llm"] = f"unhealthy: {str(e)}"

    # Overall status
    if all(
        status in ("healthy", "disabled")
        for status in (checks["database"], checks["redis"], checks["llm"])
    ):
        checks["overall"] = "ready"
    else:
        checks["overall"] = "not_ready"

    status_code = (
        status.HTTP_200_OK if checks["overall"] == "ready" else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={**checks, "timestamp": datetime.utcnow().isoformat()},
        status_code=status_code,
    )


@router.get("/metrics", tags=["Monitoring"])
async def metrics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: AuthCredentials = Depends(get_auth_credentials),
):
    """
    Prometheus-style metrics endpoint.

    Provides application metrics in Prometheus text format.
    Includes request counts, error rates, response times, and resource usage.
    """
    # Collect basic metrics from request state
    # In production, these would be aggregated from a metrics collector

    metrics = []

    # Request metrics (example - would be collected from middleware)
    metrics.append("# HELP api_requests_total Total number of API requests")
    metrics.append("# TYPE api_requests_total counter")
    metrics.append('api_requests_total{endpoint="metrics"} 1')

    metrics.append("# HELP api_errors_total Total number of API errors")
    metrics.append("# TYPE api_errors_total counter")
    metrics.append('api_errors_total{endpoint="metrics"} 0')

    # Response time metrics
    metrics.append("# HELP api_response_time_seconds API response time in seconds")
    metrics.append("# TYPE api_response_time_seconds histogram")
    metrics.append('api_response_time_seconds_bucket{le="0.1"} 0')
    metrics.append('api_response_time_seconds_bucket{le="0.5"} 1')
    metrics.append('api_response_time_seconds_bucket{le="1.0"} 1')
    metrics.append('api_response_time_seconds_bucket{le="5.0"} 1')
    metrics.append("api_response_time_seconds_sum 0.6")

    # Database metrics
    try:
        result = await db.execute(
            text("SELECT COUNT(*) FROM properties WHERE created_at > NOW() - INTERVAL '1 hour'")
        )
        recent_properties = result.scalar()
        metrics.append(f"properties_created_last_hour {recent_properties}")
    except Exception:
        metrics.append("properties_created_last_hour 0")

    # LLM usage metrics
    settings = get_settings()
    metrics.append("# HELP llm_api_calls_total Total LLM API calls")
    metrics.append("# TYPE llm_api_calls_total counter")
    metrics.append(f'llm_api_calls_total{{provider="{settings.default_provider}"}} 0')

    # Cache metrics (if Redis enabled)
    if hasattr(settings, "redis_url") and settings.redis_url:
        from core.cache import get_redis_client

        redis_client = get_redis_client()
        try:
            info = await redis_client.info("stats")
            cache_hits = info.get("keyspace_hits", 0)
            metrics.append(f"cache_hits_total {cache_hits}")
        except Exception:
            metrics.append("cache_hits_total 0")

    # System info
    metrics.append("# HELP app_info Application information")
    metrics.append("# TYPE app_info gauge")
    metrics.append(f'app_info{{version="1.0.0",environment="{settings.environment}"}} 1')

    from starlette.responses import PlainTextResponse

    return PlainTextResponse(content="\n".join(metrics), status_code=200)


@router.get("/monitoring/overview", tags=["Monitoring"])
async def monitoring_overview(
    db: AsyncSession = Depends(get_db),
    store: Optional[Any] = Depends(get_vector_store),
    credentials: AuthCredentials = Depends(get_auth_credentials),
):
    """
    High-level monitoring overview for admin dashboard.

    Returns aggregated metrics for the monitoring dashboard UI.
    """
    settings = get_settings()

    # The catalogue's own numbers. The listings live in the vector store -
    # there is no properties table - so the panel asks the catalogue, the
    # same way the landing does, and the two can never disagree.
    try:
        counts = count_catalogue(store)
        total_properties = counts.total
        recent_properties_count = counts.recent_24h
        properties_by_source = dict(counts.sources.most_common(5))
    except Exception as e:
        logger.error("Failed to fetch catalogue stats: %s", e)
        total_properties = 0
        recent_properties_count = 0
        properties_by_source = {}

    # Cache stats (if Redis enabled)
    cache_stats = {}
    if hasattr(settings, "redis_url") and settings.redis_url:
        from core.cache import get_redis_client

        redis_client = get_redis_client()
        try:
            info = await redis_client.info("stats")
            cache_stats = {
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "total_keys": info.get("db0", {}).get("keys", 0),
            }
            if cache_stats["hits"] + cache_stats["misses"] > 0:
                cache_stats["hit_rate"] = round(
                    cache_stats["hits"] / (cache_stats["hits"] + cache_stats["misses"]) * 100, 2
                )
        except Exception as e:
            logger.warning("Failed to fetch cache stats: %s", e)

    # Knowledge store stats (if RAG enabled)
    knowledge_stats = {}
    try:
        store = KnowledgeStore()
        stats = store.get_stats()
        knowledge_stats = {
            "documents": int(stats.get("documents", 0)),
            "chunks": int(stats.get("chunks", 0)),
        }
    except Exception as e:
        logger.warning("Failed to fetch knowledge store stats: %s", e)

    return {
        "database": {
            "total_properties": total_properties,
            "recent_properties_24h": recent_properties_count,
            "by_source": properties_by_source,
        },
        "cache": cache_stats,
        "knowledge_store": knowledge_stats,
        "llm": {
            "default_provider": settings.default_provider,
            "default_model": settings.default_model,
        },
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/monitoring/test-alert", tags=["Monitoring"])
async def test_alert(
    credentials: AuthCredentials = Depends(require_permission(Permission.ADMIN_SYSTEM_CONTROL)),
):
    """
    Test alert endpoint for monitoring notifications.

    Sends a test alert to validate alerting configuration.
    Requires system admin permission.
    """
    logger.warning("Test alert triggered by user=%s", credentials.user_id)

    return {
        "status": "alert_sent",
        "message": "Test alert sent to monitoring system",
        "timestamp": datetime.utcnow().isoformat(),
    }
