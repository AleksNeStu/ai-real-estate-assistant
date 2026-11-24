"""Integration tests for bulk jobs router."""

import sys
from enum import Enum
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# The real `utils` package is imported BEFORE the exporters stub below goes in.
# `utils/__init__.py` re-exports from `.exporters`, so a package imported while
# the stub is installed cannot satisfy it - and the failure lands on whichever
# line happens to import a `utils` submodule first. Importing the package for
# real here makes the order explicit instead of accidental.
import utils  # noqa: F401  quality-gate-allow: must load before the exporters stub below

# Stub heavy dependencies before importing the router.
# bulk_jobs imports api.dependencies which triggers agents→langchain→protobuf chain.
# We stub the entire chain to avoid the protobuf TypeError.
#
# `data.loaders` is deliberately NOT stubbed. It never existed - the loaders live
# in `data.csv_loader` and `data.excel_loader` - and stubbing a module that is
# not imported is what kept the broken import path green while the runtime
# raised ImportError.
_stubbed_modules = {}
for mod_name in [
    "agents",
    "agents.hybrid_agent",
    "api.dependencies",
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
from db.database import (  # noqa: E402  quality-gate-allow: must follow the stub install
    Base,
    create_engine,
    get_db,
)

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


@pytest.fixture
async def import_client(tmp_path, monkeypatch):
    """A client whose bulk jobs run against a real, file-backed database.

    The background task opens its OWN engine (bulk_jobs.create_engine), so the
    test patches that seam - the one place every engine of this application is
    built - to hand back the same database the request reads. The file lives in
    tmp_path, and the working directory moves there too, so the property cache
    the import writes lands in the temp directory and not in the checkout.
    """
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "bulk_jobs.db"
    engine = create_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    app = FastAPI()
    app.include_router(bulk_jobs.router, prefix="/api/v1")

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(bulk_jobs, "create_engine", lambda *args, **kwargs: engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


def _listing_rows(count: int) -> dict[str, Any]:
    """A sheet of `count` well-formed listings."""
    return {
        "id": [f"listing-{i}" for i in range(count)],
        "title": [f"Listing {i}" for i in range(count)],
        "city": ["Krakow"] * count,
        "price": [1000.0 + i for i in range(count)],
        "rooms": [2.0] * count,
    }


def _write_xlsx(path: Path, count: int) -> Path:
    pd.DataFrame(_listing_rows(count)).to_excel(path, index=False)
    return path


def _write_csv(path: Path, count: int) -> Path:
    pd.DataFrame(_listing_rows(count)).to_csv(path, index=False)
    return path


async def _run_import(client: AsyncClient, path: Path) -> dict[str, Any]:
    """Post a file to the bulk-job import route and return the finished job."""
    resp = await client.post(
        "/api/v1/bulk-jobs/import",
        json={
            "source_type": "file_upload",
            "config": {"temp_file_path": str(path), "filename": path.name},
            "source_name": "integration-test",
        },
    )
    assert resp.status_code == 201, resp.text
    job_id = resp.json()["id"]

    job = await client.get(f"/api/v1/bulk-jobs/{job_id}")
    assert job.status_code == 200, job.text
    payload: dict[str, Any] = job.json()
    return payload


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


class TestBulkJobImport:
    """The import path, driven with real spreadsheets."""

    @pytest.mark.asyncio
    async def test_import_job_reads_a_real_xlsx(self, import_client, tmp_path):
        """A real .xlsx through the route counts every row of the sheet."""
        path = _write_xlsx(tmp_path / "listings.xlsx", 3)

        job = await _run_import(import_client, path)

        assert job["status"] == "completed", job
        assert job["records_processed"] == 3, job
        assert job["records_failed"] == 0, job
        assert job["records_total"] == 3, job

    @pytest.mark.asyncio
    async def test_import_job_reads_a_real_csv(self, import_client, tmp_path):
        """The same for a .csv."""
        path = _write_csv(tmp_path / "listings.csv", 4)

        job = await _run_import(import_client, path)

        assert job["status"] == "completed", job
        assert job["records_processed"] == 4, job
        assert job["records_failed"] == 0, job

    @pytest.mark.asyncio
    async def test_import_job_writes_the_properties_it_read(self, import_client, tmp_path):
        """The imported rows reach the cache the product reads from."""
        from utils.property_cache import load_collection

        path = _write_csv(tmp_path / "listings.csv", 2)

        job = await _run_import(import_client, path)
        assert job["records_processed"] == 2, job

        collection = load_collection()
        assert collection is not None
        assert collection.total_count == 2
        assert {p.city for p in collection.properties} == {"Krakow"}
