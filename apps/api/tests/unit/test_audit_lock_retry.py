"""
The audit write against the lock the request still holds.

SQLite has one writer. A request that writes holds that lock until its own
transaction commits, and that commit waits for the response to be sent. So an
audit entry written while the request still holds the lock waits for a lock
that is only released after the entry is written - and the wait ends in a
timeout, which loses the entry.

The audit entry is the tamper-evident trail of the request, so it must land,
and it must land without the request waiting for it.
"""

import asyncio
import sqlite3
import time
from types import SimpleNamespace
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.middleware.audit import add_audit_middleware
from db.database import Base, create_engine, get_db
from db.models import AuditLogEntry  # noqa: F401 - registers the table on Base

# The request holds its transaction for this long - a chat that waits for a
# model holds it for seconds. The audit entry must not wait for it.
THE_REQUEST_HOLDS_THE_TRANSACTION_SECONDS = 2.0


@pytest.mark.asyncio
async def test_the_audit_entry_lands_while_the_request_holds_the_write_lock(tmp_path, monkeypatch):
    """The entry lands, and the request does not wait for the lock."""
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("CREATE TABLE route_writes (id INTEGER PRIMARY KEY)"))

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    )
    monkeypatch.setattr("db.database._session_factory", factory)

    app = FastAPI()

    @app.post("/api/v1/thing")
    async def thing(session: Annotated[AsyncSession, Depends(get_db)]):
        # the request writes, so it holds the write lock until it commits
        await session.execute(text("INSERT INTO route_writes VALUES (1)"))
        await asyncio.sleep(THE_REQUEST_HOLDS_THE_TRANSACTION_SECONDS)
        return {"ok": True}

    add_audit_middleware(app)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        started = time.perf_counter()
        response = await client.post("/api/v1/thing")
        elapsed = time.perf_counter() - started

    assert response.status_code == 200

    async with engine.begin() as conn:
        audit_rows = (await conn.execute(text("SELECT count(*) FROM audit_log_entries"))).scalar()
        route_rows = (await conn.execute(text("SELECT count(*) FROM route_writes"))).scalar()
    await engine.dispose()

    assert route_rows == 1, "the request's own write was lost"
    assert audit_rows == 1, "the audit entry was lost to the lock the request held"
    assert elapsed < THE_REQUEST_HOLDS_THE_TRANSACTION_SECONDS + 5.0, (
        f"the request waited {elapsed:.1f}s - the audit write waited for the lock"
    )


@pytest.mark.asyncio
async def test_the_audit_write_waits_for_the_lock_and_lands(monkeypatch):
    """The write retries when SQLite refuses it because of the lock."""
    from services.audit_service import AuditService

    class TheLockIsHeld:
        def __init__(self) -> None:
            self.attempts = 0

        async def append(self, **kwargs):
            self.attempts += 1
            if self.attempts == 1:
                raise sqlite3.OperationalError("database is locked")
            return kwargs

    class TheSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        async def commit(self) -> None:
            self.commits += 1

        async def rollback(self) -> None:
            self.rollbacks += 1

    repo = TheLockIsHeld()
    session = TheSession()
    monkeypatch.setattr("services.audit_service.AuditLogRepository", lambda _session: repo)

    service = AuditService(session)
    await service.log(action="post /api/v1/thing")

    assert repo.attempts == 2, "the write did not try again after the lock"
    assert session.commits == 1, "the entry was never committed"
    assert session.rollbacks == 1, "the failed attempt was not rolled back"


@pytest.mark.asyncio
async def test_the_audit_entry_joins_the_request_transaction(monkeypatch):
    """The entry is written in the request's own transaction, not a second one."""
    from api.middleware import audit as audit_module

    written = []

    class TheService:
        def __init__(self, session) -> None:
            self.session = session

        async def log(self, **kwargs) -> None:
            written.append((self.session, kwargs))

    monkeypatch.setattr(audit_module, "AuditService", TheService)

    the_request_session = object()

    class TheRequest:
        method = "POST"
        url = SimpleNamespace(path="/api/v1/thing")
        client = SimpleNamespace(host="127.0.0.1")
        headers = {"user-agent": "the-test"}

        def __init__(self) -> None:
            self.state = SimpleNamespace(
                db_session=the_request_session,
                user_id=None,
                user_email=None,
                user_role=None,
                request_id=None,
            )

    class TheResponse:
        status_code = 200
        background = None

    middleware = audit_module.AuditMiddleware(app=None)
    response = await middleware.dispatch(TheRequest(), lambda _request: _a_response(TheResponse()))

    assert written, "the entry was never written"
    session, kwargs = written[0]
    assert session is the_request_session, "the entry did not join the request's transaction"
    assert kwargs["commit"] is False, "the entry committed on its own, away from the request"
    assert kwargs["action"] == "post /api/v1/thing"
    assert response.background is None, "the entry was scheduled instead of written"


async def _a_response(value):
    return value
