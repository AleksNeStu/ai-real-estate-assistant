"""Tests for the data-sources router.

The sync-history endpoint is the one the changed-lines coverage gate looks
at: it reads the history rows through two queries, and the second one has
to name its own result, because a reused name makes the two row types look
like one.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routers import data_sources
from db.database import get_db
from db.models import DataSourceDB


@pytest.fixture
def test_app(db_session):
    """Create test app with data_sources router and mocked dependencies."""
    app = FastAPI()
    app.include_router(data_sources.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_sync_history_of_a_data_source(client, db_session):
    """Returns the sync history of a data source - empty when it has none."""
    db_session.add(DataSourceDB(id="src-history-1", name="History", source_type="file_upload"))
    await db_session.flush()

    resp = await client.get("/api/v1/data-sources/src-history-1/history")

    assert resp.status_code == 200
    body = resp.json()
    assert body["source_id"] == "src-history-1"
    assert body["total"] == 0
    assert body["history"] == []

    # The endpoint is called directly as well: a request handler runs in its
    # own task, and the coverage tracer does not come back after the task
    # suspends, so the lines of the handler are only visible to the report
    # when they run in the test's own task.
    direct = await data_sources.get_sync_history("src-history-1", db_session, 1, 20)
    assert direct.source_id == "src-history-1"
    assert direct.total == 0


@pytest.mark.asyncio
async def test_get_sync_history_of_a_missing_data_source(client):
    """Returns 404 for the sync history of a source that does not exist."""
    resp = await client.get("/api/v1/data-sources/nonexistent-id/history")

    assert resp.status_code == 404
