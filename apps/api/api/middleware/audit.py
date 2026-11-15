"""
Audit Logging Middleware (Task #95).

Automatically logs mutating requests (POST/PUT/PATCH/DELETE) to the
database-backed tamper-evident audit log.
"""

import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from db.database import get_session_factory
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Paths that should NOT be audit-logged
_EXCLUDED_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/metrics",
)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs mutating HTTP requests to the audit log.

    Only POST, PUT, PATCH, and DELETE methods are logged (GET/HEAD/OPTIONS
    are read-only and excluded). Static/docs/health paths are also excluded.
    """

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response: Response = await call_next(request)

        # Only audit mutating methods
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return response

        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
            return response

        try:
            # Extract actor info from JWT state if available
            actor_id = getattr(request.state, "user_id", None)
            actor_email = getattr(request.state, "user_email", None)
            actor_role = getattr(request.state, "user_role", None)

            # Request ID from observability middleware
            request_id = getattr(request.state, "request_id", None)

            session_factory = get_session_factory()
            async with session_factory() as session:
                service = AuditService(session)
                await service.log(
                    action=f"{request.method.lower()} {path}",
                    actor_id=actor_id,
                    actor_email=actor_email,
                    actor_role=actor_role,
                    resource=path,
                    details={"status_code": response.status_code},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    request_id=request_id,
                )
        except Exception:
            logger.exception("Audit middleware failed for %s %s", request.method, path)

        return response


def add_audit_middleware(app: FastAPI) -> None:
    """Register the audit middleware on the FastAPI app."""
    app.add_middleware(AuditMiddleware)  # type: ignore[arg-type]
