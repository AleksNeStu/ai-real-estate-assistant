"""Integration tests for bulk jobs router."""

import sys
from enum import Enum
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Stub heavy dependencies before importing the router.
# bulk_jobs imports api.dependencies which triggers agents→langchain→protobuf chain.
# We stub the entire chain to avoid the protobuf TypeError.
_stubbed_modules = {}
for mod_name in [
    "agents",
    "agents.hybrid_agent",
    "api.dependencies",
    "data.loaders",
    "data.adapters",
]:
    if mod_name not in sys.modules:
        _stubbed_modules[mod_name] = MagicMock()
        sys.modules[mod_name] = _stubbed_modules[mod_name]

# utils.exporters must provide a real ExportFormat enum (Pydantic uses it in models)
import types as _types  # noqa: E402

_exporters: Any = _types.ModuleType("utils.exporters")


class _ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"


_exporters.ExportFormat = _ExportFormat
_exporters.PropertyExporter = MagicMock()
_exporters_original = sys.modules.get("utils.exporters")
if "utils.exporters" not in sys.modules:
    sys.modules["utils.exporters"] = _exporters

from api.routers import bulk_jobs  # noqa: E402
from db.database import get_db  # noqa: E402

# Restore original modules immediately after importing the router,
# so that subsequent test modules see the real packages during collection.
for mod_name in _stubbed_modules:
    sys.modules.pop(mod_name, None)
if _exporters_original is not None:
    sys.modules["utils.exporters"] = _exporters_original
elif "utils.exporters" in sys.modules and sys.modules["utils.exporters"] is _exporters:
    sys.modules.pop("utils.exporters", None)


@pytest.fixture(autouse=True)
def _isolate_stubbed_modules():
    """Re-install stubs during each test, restore after."""
    _saved = {name: sys.modules.get(name) for name in _stubbed_modules}
    _saved["utils.exporters"] = sys.modules.get("utils.exporters")
    for name, stub in _stubbed_modules.items():
        sys.modules[name] = stub
    sys.modules["utils.exporters"] = _exporters
    yield
    for name in _saved:
        if _saved[name] is not None:
            sys.modules[name] = _saved[name]
        else:
            sys.modules.pop(name, None)


@pytest.fixture
def test_app(db_session):
    """Create test app with bulk_jobs router and mocked dependencies."""
    app = FastAPI()
    app.include_router(bulk_jobs.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestBulkJobsAPI:
    """Integration tests for bulk jobs endpoints."""

    @pytest.mark.asyncio
    async def test_list_bulk_jobs_empty(self, client):
        """Returns empty list when no jobs exist."""
        resp = await client.get("/api/v1/bulk-jobs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_bulk_jobs_with_pagination(self, client):
        """Supports pagination parameters."""
        resp = await client.get(
            "/api/v1/bulk-jobs",
            params={"page": 1, "page_size": 10},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_bulk_job_not_found(self, client):
        """Returns 404 for non-existent job."""
        resp = await client.get("/api/v1/bulk-jobs/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_bulk_job_not_found(self, client):
        """Returns 404 when cancelling non-existent job."""
        resp = await client.post("/api/v1/bulk-jobs/nonexistent-id/cancel")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_bulk_job_not_found(self, client):
        """Returns 404 when deleting non-existent job."""
        resp = await client.delete("/api/v1/bulk-jobs/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_bulk_jobs_with_filters(self, client):
        """Supports job_type and status filters."""
        resp = await client.get(
            "/api/v1/bulk-jobs",
            params={"job_type": "import", "status_filter": "completed"},
        )
        assert resp.status_code == 200
