import asyncio
import logging
import os
import signal
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Load .env from project root when running from apps/api/
_root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _root_env.exists():
    from dotenv import load_dotenv

    load_dotenv(_root_env, override=False)

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module=r"langchain_google_genai\.chat_models",
)

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.auth import get_api_key, get_optional_api_key
from api.dependencies import get_vector_store
from api.health import HealthStatus, get_git_info, get_health_status
from api.middleware.csrf import add_csrf_middleware
from api.middleware.error_handler import add_error_handlers
from api.middleware.latency import add_latency_middleware
from api.middleware.request_size import add_request_size_limits
from api.middleware.security import add_security_headers
from api.middleware.versioning import add_versioning_middleware
from api.observability import REQUEST_ID_HEADER, add_observability
from api.routers import (
    admin,
    agent_analytics,  # Task #56: Agent Performance Analytics
    agents,  # Task #45: Agent/Broker Integration
    anomalies,  # Task #53: Market Anomaly Detection
    auth,
    auth_jwt,  # JWT authentication endpoints
    bulk_jobs,  # Task #80: Import/Export Data API
    chat,
    cma,  # Task #85: Comparative Market Analysis
    collections,  # Task #37: Property collections
    data_sources,  # Task #79: Data Sources Dashboard
    documents,  # Task #43: Document Management
    esignatures,  # Task #57: E-Signature Integration
    exports,
    favorites,  # Task #37: Property favorites
    feedback,  # Task #118: Search Relevance Rating
    filter_presets,  # Task #75: Advanced Filter Presets
    investment,  # Task #83: Investment Report Generator
    leads,  # Task #55: Lead Scoring System
    market,  # Task #38: Price History & Trends
    mcp_admin,  # Task #68: MCP Allowlist Governance
    mcp_audit,  # Task #69: MCP Audit Logging
    metrics,  # Task #62: Production Monitoring
    model_preferences,  # Task #87: Model Preferences Per-Task
    monitoring,  # Task #57: Production Monitoring Dashboard
    profile,  # Task #88: User Profile Management
    prompt_templates,
    push,  # Task #63: Push Notifications
    ranking_config,  # Task #76: Ranking Configuration
    saved_searches,
    search,
    tools,
    user_activity,  # Task #82: User Activity Analytics
    webhooks,  # Task #57: E-Signature Webhooks
)
from api.routers import (
    rag as rag_router,
)
from api.routers import (
    settings as settings_router,
)
from config.settings import get_settings
from notifications.email_service import (
    EmailConfig,
    EmailProvider,
    EmailService,
    EmailServiceFactory,
)
from notifications.scheduler import NotificationScheduler
from notifications.uptime_monitor import (
    UptimeMonitor,
    UptimeMonitorConfig,
    make_http_checker,
)
from utils.connection_pool import get_connection_pool_manager
from utils.json_logging import configure_json_logging
from utils.response_cache import CacheConfig, ResponseCache

configure_json_logging(logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize Sentry error tracking (Task #56)
from api.sentry_init import init_sentry

init_sentry()

API_DESCRIPTION = """\
# AI Real Estate Assistant API

Conversational AI platform for property search, market analysis, and investment tools.

## Authentication

- **API Key** — pass via `X-API-Key` header for general access
- **JWT Bearer** — pass via `Authorization: Bearer <token>` for user-scoped features (favorites, saved searches, market data, etc.)

## Base URL

```
/api/v1
```

All endpoints listed below are mounted under this prefix.
"""

OPENAPI_TAGS = [
    # Core
    {
        "name": "Search",
        "description": "Semantic property search with filters, ranking, and pagination",
    },
    {"name": "Chat", "description": "Conversational AI assistant for property queries"},
    {"name": "RAG", "description": "Document upload and Q&A with citations"},
    {
        "name": "Tools",
        "description": "Mortgage, TCO, investment, commute, valuation, and other calculators",
    },
    # Property management
    {"name": "Favorites", "description": "Property favorites and watchlist"},
    {"name": "Collections", "description": "Organize favorites into named collections"},
    {"name": "Saved Searches", "description": "Save search queries with alert settings"},
    {"name": "Filter Presets", "description": "Saved filter configurations"},
    # Market & analysis
    {
        "name": "Market Analytics",
        "description": "Price history, trends, indicators, and area insights",
    },
    {"name": "CMA", "description": "Comparative Market Analysis reports"},
    {"name": "Anomalies", "description": "Market anomaly detection and management"},
    {"name": "Lead Scoring", "description": "Property lead scoring system"},
    {"name": "Investment", "description": "Investment property analysis and report generation"},
    # Agents
    {"name": "Agents", "description": "Real estate agent and broker management"},
    {"name": "Agent Analytics", "description": "Agent performance metrics and coaching"},
    # Documents & signatures
    {"name": "Documents", "description": "Document upload, download, and management"},
    {"name": "E-Signatures", "description": "Electronic signature request workflow"},
    {"name": "Webhooks", "description": "Incoming webhook endpoints"},
    # Data management
    {"name": "Data Sources", "description": "External data source configuration and sync"},
    {"name": "Bulk Jobs", "description": "Bulk import and export job management"},
    {"name": "Export", "description": "Export properties to CSV, Excel, JSON"},
    # Admin
    {"name": "Admin", "description": "Data ingestion, reindexing, and system administration"},
    {"name": "Audit", "description": "Audit log querying"},
    {"name": "Settings", "description": "Application settings"},
    {"name": "Profile", "description": "User profile management"},
    {"name": "Feedback", "description": "Search relevance ratings and feedback metrics"},
    # Auth
    {"name": "Auth", "description": "API key authentication"},
    {"name": "JWT Auth", "description": "JWT-based user authentication (register, login, refresh)"},
    # Configuration
    {"name": "Model Preferences", "description": "Per-task LLM model preferences"},
    {"name": "Ranking Configuration", "description": "Property ranking algorithm configuration"},
    {"name": "Prompt Templates", "description": "System prompt templates and rendering"},
    {"name": "MCP Admin", "description": "MCP connector allowlist governance"},
    {"name": "MCP Audit", "description": "MCP connector audit log management"},
    # System
    {"name": "Monitoring", "description": "Prometheus metrics and health checks"},
    {"name": "Push Notifications", "description": "Web push notification subscriptions"},
    {"name": "User Activity Analytics", "description": "User behavior and activity tracking"},
]

app = FastAPI(
    title=settings.app_title,
    version=settings.version,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
)

# Response compression — reduces JSON payload sizes by 60-80%
from starlette.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)


add_observability(app, logger)
add_latency_middleware(app)  # Task #120: p95 latency monitoring
add_security_headers(app)
add_versioning_middleware(app)  # Task #97: API version headers
add_request_size_limits(app)
add_csrf_middleware(app)
add_error_handlers(app)

# Rate limiting (Task #62)
from api.middleware.rate_limit import add_rate_limit_middleware

add_rate_limit_middleware(app)

# Audit middleware (Task #95) — conditionally enabled with JWT auth
if settings.auth_jwt_enabled:
    from api.middleware.audit import add_audit_middleware

    add_audit_middleware(app)

# Global scheduler instance
scheduler = None

# Graceful shutdown configuration
SHUTDOWN_DRAIN_SECONDS = int(os.getenv("SHUTDOWN_DRAIN_SECONDS", "30"))
SHUTDOWN_MAX_WAIT_SECONDS = int(os.getenv("SHUTDOWN_MAX_WAIT_SECONDS", "60"))


@app.on_event("startup")
async def startup_event():
    """Initialize application services on startup and setup signal handlers."""
    global scheduler
    from time import time

    # Set application start time for uptime metrics
    app.state.start_time = time()

    # Setup signal handlers for graceful shutdown (only in main thread)
    import threading

    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            if hasattr(signal, sig.name):
                signal.signal(sig, lambda s, f: None)  # Let FastAPI handle

    # 1. Initialize Vector Store (lazy — first request triggers actual init via @lru_cache)
    logger.info("Vector Store will initialize on first request (lazy loading)...")
    app.state.vector_store = None  # Set by get_vector_store() on first use

    # 1.1 Auto-seed demo data (opt-in via SEED_ON_STARTUP env var)
    if os.getenv("SEED_ON_STARTUP", "false").lower() == "true":
        logger.info("SEED_ON_STARTUP enabled — seeding demo data...")
        try:
            from alembic.seed import seed_all

            await seed_all()
            logger.info("Demo data seeded successfully.")
        except Exception as e:
            logger.warning("Auto-seed failed (non-fatal): %s", e)

    # 1.2 Generate comprehensive demo data for maximum feature showcase (if demo mode enabled)
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        logger.info("DEMO_MODE enabled — generating comprehensive demo data...")
        try:
            from alembic.demo_data_generator import generate_comprehensive_demo_data
            from db.database import get_db_session

            # Get a database session for the generator
            async for session in get_db_session():
                await generate_comprehensive_demo_data(session)
                break  # Only generate once per startup
            logger.info("Comprehensive demo data generated successfully.")
        except Exception as demo_error:
            logger.warning("Comprehensive demo data generation failed (non-fatal): %s", demo_error)

    # 1.5 Initialize Auth Database (if JWT auth enabled)
    if settings.auth_jwt_enabled:
        logger.info("Initializing Auth Database...")
        try:
            from db.database import init_db

            await init_db()
            logger.info("Auth Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Auth Database: {e}")

    # 2. Initialize Email Service
    logger.info("Initializing Email Service...")
    email_service = EmailServiceFactory.create_from_env()

    if not email_service:
        logger.warning(
            "No email configuration found in environment. "
            "Using dummy service (emails will not be sent)."
        )
        # Create dummy service for scheduler to function without crashing
        dummy_config = EmailConfig(
            provider=EmailProvider.CUSTOM,
            smtp_server="localhost",
            smtp_port=1025,
            username="dummy",
            password="dummy",
            from_email="noreply@example.com",
        )
        email_service = EmailService(dummy_config)

    # 3. Initialize and Start Scheduler
    logger.info("Starting Notification Scheduler...")
    try:
        # Get vector store lazily for scheduler (may be None if not yet initialized)
        vs = get_vector_store()
        scheduler = NotificationScheduler(
            email_service=email_service,
            vector_store=vs,
            poll_interval_seconds=60,
        )
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Notification Scheduler started successfully.")
    except Exception as e:
        logger.error(f"Failed to start Notification Scheduler: {e}")

    # 4. Initialize Uptime Monitor (optional via env)
    try:
        enabled_raw = os.getenv("UPTIME_MONITOR_ENABLED", "false").strip().lower()
        enabled = enabled_raw in {"1", "true", "yes", "y", "on"}
        if enabled and email_service:
            health_url = os.getenv(
                "UPTIME_MONITOR_HEALTH_URL", "http://localhost:8000/health"
            ).strip()
            to_email = (
                os.getenv("UPTIME_MONITOR_EMAIL_TO", "ops@example.com").strip() or "ops@example.com"
            )
            interval = float(os.getenv("UPTIME_MONITOR_INTERVAL", "60").strip() or "60")
            threshold = int(os.getenv("UPTIME_MONITOR_FAIL_THRESHOLD", "3").strip() or "3")
            cooldown = float(os.getenv("UPTIME_MONITOR_COOLDOWN_SECONDS", "1800").strip() or "1800")
            checker = make_http_checker(health_url, timeout=3.0)
            mon_cfg = UptimeMonitorConfig(
                interval_seconds=interval,
                fail_threshold=threshold,
                alert_cooldown_seconds=cooldown,
                to_email=to_email,
            )
            uptime_monitor = UptimeMonitor(
                checker=checker, email_service=email_service, config=mon_cfg, logger=logger
            )
            uptime_monitor.start()
            app.state.uptime_monitor = uptime_monitor
            logger.info(
                "Uptime Monitor started url=%s to=%s interval=%s", health_url, to_email, interval
            )
    except Exception as e:
        logger.error(f"Failed to start Uptime Monitor: {e}")

    # 5. Initialize Response Cache (TASK-017: Production Deployment Optimization)
    logger.info("Initializing Response Cache...")
    try:
        cache_settings = CacheConfig(
            enabled=getattr(settings, "cache_enabled", True),
            ttl_seconds=getattr(settings, "cache_ttl_seconds", 300),
            prefix=getattr(settings, "cache_prefix", "api_cache"),
            max_memory_mb=getattr(settings, "cache_max_memory_mb", 100),
            stale_while_revalidate=getattr(settings, "cache_stale_while_revalidate", False),
        )
        redis_url = getattr(settings, "cache_redis_url", None)
        response_cache = ResponseCache(config=cache_settings, redis_url=redis_url)
        app.state.response_cache = response_cache
        logger.info("Response Cache initialized: %s", response_cache.get_stats())
    except Exception as e:
        logger.warning(f"Failed to initialize Response Cache: {e}")

    # 6. Initialize Connection Pool Manager (TASK-017)
    logger.info("Initializing Connection Pool Manager...")
    try:
        pool_manager = get_connection_pool_manager()
        app.state.pool_manager = pool_manager
        logger.info("Connection Pool Manager initialized: %s", pool_manager.get_stats())
    except Exception as e:
        logger.warning(f"Failed to initialize Connection Pool Manager: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on shutdown with graceful drain period.

    This handler:
    1. Logs the shutdown initiation
    2. Waits for a drain period to allow in-flight requests to complete
    3. Stops background services (scheduler, monitors)
    4. Closes database/vector store connections
    5. Logs completion of shutdown
    """
    logger.info("Graceful shutdown initiated...")
    shutdown_start_time = asyncio.get_event_loop().time()

    # Step 1: Stop accepting new requests (handled by uvicorn)
    # We just need to drain in-flight requests during this period

    # Step 2: Stop Uptime Monitor first (doesn't depend on other services)
    mon = getattr(app.state, "uptime_monitor", None)
    if mon:
        logger.info("Stopping Uptime Monitor...")
        try:
            mon.stop()
            logger.info("Uptime Monitor stopped.")
        except Exception as e:
            logger.error(f"Error stopping Uptime Monitor: {e}")

    # Step 3: Stop Notification Scheduler
    if scheduler:
        logger.info("Stopping Notification Scheduler...")
        try:
            scheduler.stop()
            logger.info("Notification Scheduler stopped.")
        except Exception as e:
            logger.error(f"Error stopping Notification Scheduler: {e}")

    # Step 4: Wait for drain period to allow in-flight requests to complete
    if SHUTDOWN_DRAIN_SECONDS > 0:
        logger.info(f"Waiting {SHUTDOWN_DRAIN_SECONDS}s drain period for in-flight requests...")
        try:
            await asyncio.sleep(SHUTDOWN_DRAIN_SECONDS)
        except Exception as e:
            logger.warning(f"Drain period interrupted: {e}")

    # Step 5: Close vector store connection
    vector_store = getattr(app.state, "vector_store", None)
    if vector_store:
        logger.info("Closing Vector Store connection...")
        try:
            # ChromaDB doesn't need explicit closing, but if we had
            # a database connection we would close it here
            if hasattr(vector_store, "close"):
                await vector_store.close()
            logger.info("Vector Store connection closed.")
        except Exception as e:
            logger.error(f"Error closing Vector Store: {e}")

    # Step 6: Close rate limiter connections if using Redis
    rate_limiter = getattr(app.state, "rate_limiter", None)
    if rate_limiter and hasattr(rate_limiter, "_redis_client"):
        redis_client = rate_limiter._redis_client
        if redis_client:
            logger.info("Closing Redis connection...")
            try:
                await redis_client.aclose() if hasattr(
                    redis_client, "aclose"
                ) else redis_client.close()
                logger.info("Redis connection closed.")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    # Step 7: Clear response cache (TASK-017)
    response_cache = getattr(app.state, "response_cache", None)
    if response_cache:
        logger.info("Clearing Response Cache...")
        try:
            await response_cache.clear_all()
            logger.info("Response Cache cleared.")
        except Exception as e:
            logger.error(f"Error clearing Response Cache: {e}")

    # Step 8: Close connection pools (TASK-017)
    pool_manager = getattr(app.state, "pool_manager", None)
    if pool_manager:
        logger.info("Closing connection pools...")
        try:
            pool_manager.close_all()
            logger.info("Connection pools closed.")
        except Exception as e:
            logger.error(f"Error closing connection pools: {e}")

    shutdown_elapsed = asyncio.get_event_loop().time() - shutdown_start_time
    logger.info(f"Graceful shutdown completed in {shutdown_elapsed:.2f}s")


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)

# Include Routers
app.include_router(search.router, prefix="/api/v1", dependencies=[Depends(get_optional_api_key)])
app.include_router(chat.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
# Task #89: Free tier chat (no API key required, rate-limited)
app.include_router(chat.free_router, prefix="/api/v1")
app.include_router(rag_router.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(settings_router.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(tools.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(prompt_templates.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(admin.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
# Task #79: Data Sources Dashboard
app.include_router(data_sources.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
# Task #80: Import/Export Data API
app.include_router(bulk_jobs.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(mcp_admin.router, prefix="/api/v1")  # Task #68: MCP Admin (has own auth)
app.include_router(mcp_audit.router, prefix="/api/v1")  # Task #69: MCP Audit (has own auth)
app.include_router(exports.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(auth.router, prefix="/api/v1")
# Task #62: Prometheus metrics endpoint (no auth required for monitoring)
app.include_router(metrics.router)
# Task #57: Production Monitoring Dashboard (health, readiness, metrics, overview)
app.include_router(monitoring.router)

# JWT Auth Router (conditionally enabled)
if settings.auth_jwt_enabled:
    app.include_router(auth_jwt.router, prefix="/api/v1")
    # Saved searches requires JWT auth
    app.include_router(saved_searches.router, prefix="/api/v1")
    # Task #37: Favorites and Collections require JWT auth
    app.include_router(collections.router, prefix="/api/v1")
    app.include_router(favorites.router, prefix="/api/v1")
    # Task #75: Filter Presets
    app.include_router(filter_presets.router, prefix="/api/v1")
    # Task #38: Market analytics (price history, trends, indicators)
    app.include_router(market.router, prefix="/api/v1")
    app.include_router(anomalies.router, prefix="/api/v1")
    # Task #55: Lead Scoring System
    app.include_router(leads.router, prefix="/api/v1")
    # Task #56: Agent Performance Analytics
    app.include_router(agent_analytics.router, prefix="/api/v1")
    # Task #63: Push Notifications
    app.include_router(push.router, prefix="/api/v1")
    # Task #45: Agent/Broker Integration
    app.include_router(agents.router, prefix="/api/v1")
    # Task #43: Document Management System
    app.include_router(documents.router, prefix="/api/v1")
    # Task #57: E-Signature Integration
    app.include_router(esignatures.router, prefix="/api/v1")
    app.include_router(webhooks.esignatures.router, prefix="/api/v1")
    # Task #82: User Activity Analytics
    app.include_router(user_activity.router, prefix="/api/v1")
    # Task #87: Model Preferences Per-Task
    app.include_router(model_preferences.router, prefix="/api/v1")
    # Task #88: User Profile Management
    app.include_router(profile.router, prefix="/api/v1")
else:
    # Fallback /auth/me so frontend gets 401 instead of 404 when JWT is disabled
    @app.get("/api/v1/auth/me", include_in_schema=False)
    async def auth_me_fallback():
        raise HTTPException(status_code=401, detail="JWT authentication is not enabled")


# Task #76: Ranking Configuration
app.include_router(ranking_config.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
# Task #83: Investment Report Generator
app.include_router(investment.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
# Task #85: Comparative Market Analysis (CMA)
app.include_router(cma.router, prefix="/api/v1")
# Task #118: Search Relevance Rating
app.include_router(feedback.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])


@app.get("/health", tags=["System"])
async def health_check(include_dependencies: bool = True):
    """
    Health check endpoint to verify API status.

    Args:
        include_dependencies: Whether to check dependency health
            (vector store, Redis, LLM providers)

    Returns:
        Comprehensive health status including dependencies
    """
    health = await get_health_status(include_dependencies=include_dependencies)

    # Convert to dict for JSON response
    response: dict[str, str | float | dict[str, Any]] = {
        "status": health.status.value,
        "version": health.version,
        "timestamp": health.timestamp,
        "uptime_seconds": health.uptime_seconds,
    }

    if health.dependencies:
        response["dependencies"] = {
            name: {
                "status": dep.status.value,
                "message": dep.message,
                "latency_ms": dep.latency_ms,
            }
            for name, dep in health.dependencies.items()
        }

    # Add git info for production deployments
    git_info = get_git_info()
    if git_info.get("commit") != "unknown":
        response["git"] = git_info

    # Return appropriate HTTP status based on health
    from fastapi import status as http_status

    status_code = http_status.HTTP_200_OK
    if health.status.value == "unhealthy":
        status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    elif health.status.value == "degraded":
        status_code = http_status.HTTP_200_OK  # Degraded is still 200, with info

    from fastapi.responses import JSONResponse

    return JSONResponse(content=response, status_code=status_code)


@app.get("/health/ready", tags=["System"])
async def readiness_check():
    """
    K8s readiness probe - checks if app can serve traffic.
    Returns 200 if all critical dependencies are available.
    """
    health = await get_health_status(include_dependencies=True)

    # Only vector_store is critical for serving traffic
    vs_health = health.dependencies.get("vector_store")
    if vs_health and vs_health.status == HealthStatus.UNHEALTHY:
        return JSONResponse(
            content={"status": "not_ready", "reason": "vector_store_unhealthy"}, status_code=503
        )

    return {"status": "ready"}


@app.get("/health/live", tags=["System"])
async def liveness_check():
    """
    K8s liveness probe - checks if app is alive.
    Simple ping endpoint (no dependency checks).
    """
    return {"status": "alive", "timestamp": datetime.now(tz=UTC).isoformat()}


@app.get("/api/v1/verify-auth", dependencies=[Depends(get_api_key)], tags=["Auth"])
async def verify_auth():
    """
    Verify API key authentication.
    """
    return {"message": "Authenticated successfully", "valid": True}


@app.get("/metrics", tags=["System"])
async def metrics_endpoint():
    """
    Prometheus-compatible metrics endpoint (TASK-017).

    Returns application metrics in Prometheus text format.
    """
    from time import time

    metrics = []
    metrics.append("# HELP api_requests_total Total number of API requests")
    metrics.append("# TYPE api_requests_total counter")

    # Get request metrics from app state
    if hasattr(app.state, "metrics"):
        for key, count in app.state.metrics.items():
            method, path = key.split(" ", 1) if " " in key else ("UNKNOWN", key)
            # Sanitize path for Prometheus label
            safe_path = path.replace("/", "_").strip("_") or "root"
            metrics.append(f'api_requests_total{{method="{method}",path="{safe_path}"}} {count}')

    # Add cache metrics if available
    response_cache = getattr(app.state, "response_cache", None)
    if response_cache:
        cache_stats = response_cache.get_stats()
        metrics.append("\n# HELP api_cache_size Current number of cached entries")
        metrics.append("# TYPE api_cache_size gauge")
        metrics.append(f"api_cache_size {cache_stats.get('size', 0)}")
        metrics.append("\n# HELP api_cache_enabled Whether caching is enabled")
        metrics.append("# TYPE api_cache_enabled gauge")
        metrics.append(f"api_cache_enabled {1 if cache_stats.get('enabled') else 0}")

    # Add uptime metric
    if hasattr(app.state, "start_time"):
        uptime = time() - app.state.start_time
        metrics.append("\n# HELP api_uptime_seconds Application uptime in seconds")
        metrics.append("# TYPE api_uptime_seconds gauge")
        metrics.append(f"api_uptime_seconds {uptime:.2f}")

    return "\n".join(metrics), 200, {"Content-Type": "text/plain; version=0.0.4"}
