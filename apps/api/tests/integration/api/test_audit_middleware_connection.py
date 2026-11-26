"""The audit middleware must leave the pool the way it found it.

A request that fails rolls its transaction back and closes its session
before the middleware writes the audit entry - the error response is built
after the dependency has been torn down. The middleware used to write into
that closed session: the write opened a fresh connection, nothing returned
it to the pool, and the garbage collector had to terminate it. The entry
was lost with it, because the session it was written into was never
committed.

Both halves are checked here: the pool is empty afterwards, and the entry
is in the log.
"""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.middleware.audit import add_audit_middleware
from db.database import Base, create_engine, get_db
from db.models import AuditLogEntry


@pytest.fixture
async def engine(tmp_path, monkeypatch):
    """An engine of its own, on a file, so the pool has something to hold."""
    eng = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("db.database.get_session_factory", lambda: factory)
    monkeypatch.setattr("api.middleware.audit.get_session_factory", lambda: factory)
    yield eng
    await eng.dispose()


def _app() -> FastAPI:
    app = FastAPI()
    add_audit_middleware(app)

    @app.post("/mutating")
    async def mutating(session: Annotated[AsyncSession, Depends(get_db)]):
        return {"ok": True}

    @app.post("/failing")
    async def failing(session: Annotated[AsyncSession, Depends(get_db)]):
        raise HTTPException(status_code=409, detail="already registered")

    return app


async def _entries(engine) -> list[AuditLogEntry]:
    async with AsyncSession(engine) as session:
        result = await session.execute(select(AuditLogEntry))
        return list(result.scalars().all())


@pytest.mark.asyncio
async def test_a_failed_request_leaves_no_connection_behind(engine):
    app = _app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/failing")

    assert response.status_code == 409
    assert engine.pool.checkedout() == 0


@pytest.mark.asyncio
async def test_the_entry_of_a_failed_request_is_in_the_log(engine):
    app = _app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/failing")

    entries = await _entries(engine)
    assert len(entries) == 1
    assert entries[0].action == "post /failing"
    assert engine.pool.checkedout() == 0


@pytest.mark.asyncio
async def test_the_entry_of_a_successful_request_is_in_the_log(engine):
    app = _app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/mutating")

    assert response.status_code == 200
    entries = await _entries(engine)
    assert len(entries) == 1
    assert entries[0].action == "post /mutating"
    assert engine.pool.checkedout() == 0
