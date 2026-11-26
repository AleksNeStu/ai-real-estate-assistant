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
        path = request.url.path
        audited = request.method in ("POST", "PUT", "PATCH", "DELETE") and not any(
            path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES
        )
        if audited:
            # The entry is written into the request's own transaction, after
            # the route has returned. The request's commit waits for that
            # write, so the session cannot be closed under it.
            request.state.db_audit_pending = True

        response: Response = await call_next(request)

        # Only audit mutating methods
        if not audited:
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

        # The request's own session is the request's own transaction, and
        # SQLite has one writer. The entry rides with it: no second writer,
        # no deadlock on the write lock, and the request's commit carries
        # the entry. The session is published only while it is open - a
        # request that failed rolled its transaction back and closed it
        # before the response was built.
        session = getattr(request.state, "db_session", None)
        if session is not None:
            try:
                service = AuditService(session)
                await service.log(commit=False, **entry)
            except Exception:
                logger.exception("Audit middleware failed for %s", entry.get("action"))
            finally:
                self._signal_audit_written(request)
            return response

        # The request has no session of its own, or its session is already
        # closed - a request that failed. The entry goes on a session of its
        # own, and it is written here rather than in a background task: the
        # response was already sent by the time this middleware is handed
        # it, so a task attached to it would never run.
        await self._write_entry(entry)
        self._signal_audit_written(request)

        return response

    @staticmethod
    def _signal_audit_written(request: Request) -> None:
        """Tell the request's session that the audit entry has been written."""
        audit_written = getattr(request.state, "db_audit_written", None)
        if audit_written is not None:
            audit_written.set()

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
