"""
Audit Logging Middleware (Task #95).

Automatically logs mutating requests (POST/PUT/PATCH/DELETE) to the
database-backed tamper-evident audit log.

The entry is written after the response is on the wire, not before. SQLite
has one writer: a request that writes holds that lock until its own
transaction commits, and that commit waits for the response to be sent. An
entry written before the response is sent therefore waits for a lock that is
only released after the entry is written - and the visitor waits for it.
"""

import logging
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.background import BackgroundTask
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

        # Extract actor info from JWT state if available
        actor_id = getattr(request.state, "user_id", None)
        actor_email = getattr(request.state, "user_email", None)
        actor_role = getattr(request.state, "user_role", None)

        # Request ID from observability middleware
        request_id = getattr(request.state, "request_id", None)

        entry: dict[str, Any] = {
            "action": f"{request.method.lower()} {path}",
            "actor_id": actor_id,
            "actor_email": actor_email,
            "actor_role": actor_role,
            "resource": path,
            "details": {"status_code": response.status_code},
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "request_id": request_id,
        }

        # The write happens after the response is on the wire. A task the
        # route set itself still runs - the audit entry does not replace it.
        existing = response.background
        audit = BackgroundTask(self._write_entry, entry)
        if existing is None:
            response.background = audit
        else:

            async def write_audit_after_the_route() -> None:
                await existing()
                await audit()

            response.background = BackgroundTask(write_audit_after_the_route)

        return response

    async def _write_entry(self, entry: dict[str, Any]) -> None:
        """Write one audit entry, on its own session."""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                service = AuditService(session)
                await service.log(**entry)
        except Exception:
            logger.exception("Audit middleware failed for %s", entry.get("action"))


def add_audit_middleware(app: FastAPI) -> None:
    """Register the audit middleware on the FastAPI app."""
    app.add_middleware(AuditMiddleware)  # type: ignore[arg-type]
