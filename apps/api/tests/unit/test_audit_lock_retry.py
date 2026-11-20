"""
The audit write against the lock the request still holds.

SQLite has one writer. A request that writes holds that lock until its own
transaction commits - and its commit waits for the response to be sent. So an
audit entry written before the response is sent waits for a lock that is only
released after the audit entry is written: a circle, broken only by the busy
timeout, which loses the entry and stalls the visitor.

The audit entry is the tamper-evident trail of the request, so it must land -
and the visitor must not wait for it.
"""

import time
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.middleware.audit import add_audit_middleware
from db.database import Base, create_engine, get_db
from db.models import AuditLogEntry  # noqa: F401 - registers the table on Base


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
    assert elapsed < 5.0, f"the request waited {elapsed:.1f}s on the audit write"
