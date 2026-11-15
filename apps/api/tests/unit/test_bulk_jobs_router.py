"""Comprehensive unit tests for bulk_jobs router covering all code paths.

Covers: route handlers, validation functions, background task functions,
helper functions, and edge cases for 100% line coverage of bulk_jobs.py.
"""

import os
import sys
import types
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "test-api-key")

from api.auth import get_api_key
from api.models import BulkJobSourceType, BulkJobStatus
from api.routers import bulk_jobs
from api.routers.bulk_jobs import (
    JOB_RESULT_EXPIRATION_HOURS,
    _calculate_progress_percent,
    _job_to_response,
    _process_file_import,
    _process_portal_import,
    _process_url_import,
    _run_export_job,
    _run_import_job,
    _validate_export_config,
    _validate_import_config,
)
from db.database import get_db
from db.models import BulkJob

# ---------------------------------------------------------------------------
# Helper: install a mock module into sys.modules for lazy-import patching
# ---------------------------------------------------------------------------


def _install_mock_module(name: str, attrs: dict) -> types.ModuleType:
    """Create and install a mock module with given attributes."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


@pytest.fixture(autouse=True)
def _cleanup_mock_modules():
    """Remove any mock modules after each test."""
    yield
    for key in list(sys.modules.keys()):
        if key == "data.loaders" or key == "data.adapters":
            if not hasattr(sys.modules[key], "__file__") or sys.modules[key].__file__ is None:
                # It's our mock module, remove it
                del sys.modules[key]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async client with bulk jobs router."""
    app = FastAPI()

    async def override_get_api_key():
        return "test-api-key"

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_api_key] = override_get_api_key
    app.dependency_overrides[get_db] = override_get_db

    app.include_router(bulk_jobs.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """API key auth headers."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
async def sample_import_job(db_session: AsyncSession) -> BulkJob:
    """Create a sample import job for testing."""
    job = BulkJob(
        id="test-import-001",
        job_type="import",
        source_type="url",
        config={
            "file_urls": ["https://example.com/data.csv"],
            "source_name": "Test Import",
        },
        status="completed",
        records_total=100,
        records_processed=100,
        records_failed=0,
        progress_percent=100.0,
        result_data={"records_processed": 100},
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def sample_pending_job(db_session: AsyncSession) -> BulkJob:
    """Create a pending job for cancellation tests."""
    job = BulkJob(
        id="test-pending-001",
        job_type="import",
        source_type="url",
        config={"file_urls": ["https://example.com/data.csv"]},
        status="pending",
        records_total=0,
        records_processed=0,
        records_failed=0,
        progress_percent=0.0,
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


# ===========================================================================
# Test _calculate_progress_percent helper
# ===========================================================================


class TestCalculateProgressPercent:
    """Tests for the _calculate_progress_percent helper function."""

    def test_zero_total(self):
        assert _calculate_progress_percent(10, 0) == 0.0

    def test_negative_total(self):
        assert _calculate_progress_percent(5, -1) == 0.0

    def test_half_progress(self):
        assert _calculate_progress_percent(50, 100) == 50.0

    def test_full_progress(self):
        assert _calculate_progress_percent(100, 100) == 100.0

    def test_over_100_capped(self):
        assert _calculate_progress_percent(200, 100) == 100.0

    def test_partial_progress(self):
        assert _calculate_progress_percent(1, 3) == pytest.approx(33.333, rel=1e-2)


# ===========================================================================
# Test _job_to_response helper
# ===========================================================================


class TestJobToResponse:
    """Tests for the _job_to_response conversion function."""

    def test_converts_all_fields(self):
        now = datetime.now(UTC)
        job = MagicMock(spec=BulkJob)
        job.id = "job-123"
        job.job_type = "import"
        job.source_type = "url"
        job.status = "completed"
        job.records_total = 50
        job.records_processed = 50
        job.records_failed = 0
        job.progress_percent = 100.0
        job.result_url = "https://example.com/download"
        job.result_data = {"key": "value"}
        job.error_message = None
        job.created_at = now
        job.started_at = now
        job.completed_at = now
        job.expires_at = now

        resp = _job_to_response(job)
        assert resp.id == "job-123"
        assert resp.job_type == "import"
        assert resp.source_type == "url"
        assert resp.status == "completed"
        assert resp.records_total == 50
        assert resp.records_processed == 50
        assert resp.records_failed == 0
        assert resp.progress_percent == 100.0
        assert resp.result_url == "https://example.com/download"
        assert resp.result_data == {"key": "value"}
        assert resp.error_message is None
        assert resp.created_at == now
        assert resp.started_at == now
        assert resp.completed_at == now
        assert resp.expires_at == now

    def test_optional_fields_none(self):
        job = MagicMock(spec=BulkJob)
        job.id = "job-456"
        job.job_type = "export"
        job.source_type = "search"
        job.status = "pending"
        job.records_total = 0
        job.records_processed = 0
        job.records_failed = 0
        job.progress_percent = 0.0
        job.result_url = None
        job.result_data = None
        job.error_message = None
        job.created_at = datetime.now(UTC)
        job.started_at = None
        job.completed_at = None
        job.expires_at = None

        resp = _job_to_response(job)
        assert resp.result_url is None
        assert resp.result_data is None
        assert resp.error_message is None
        assert resp.started_at is None
        assert resp.completed_at is None
        assert resp.expires_at is None


# ===========================================================================
# Test _validate_import_config
# ===========================================================================


class TestValidateImportConfig:
    """Tests for the _validate_import_config function."""

    def test_url_source_missing_file_urls(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_import_config(BulkJobSourceType.URL, {})
        assert exc_info.value.status_code == 422
        assert "file_urls" in exc_info.value.detail

    def test_url_source_file_urls_not_list(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_import_config(BulkJobSourceType.URL, {"file_urls": "not-a-list"})
        assert exc_info.value.status_code == 422
        assert "must be a list" in exc_info.value.detail

    def test_url_source_invalid_url_scheme(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_import_config(BulkJobSourceType.URL, {"file_urls": ["ftp://bad.url"]})
        assert exc_info.value.status_code == 422
        assert "Invalid URL" in exc_info.value.detail

    def test_url_source_valid_urls(self):
        _validate_import_config(
            BulkJobSourceType.URL,
            {"file_urls": ["https://example.com/data.csv"]},
        )

    def test_file_upload_missing_temp_path(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_import_config(BulkJobSourceType.FILE_UPLOAD, {})
        assert exc_info.value.status_code == 422
        assert "temp_file_path" in exc_info.value.detail

    def test_file_upload_valid(self):
        _validate_import_config(
            BulkJobSourceType.FILE_UPLOAD,
            {"temp_file_path": "/tmp/upload.csv"},
        )

    def test_portal_api_missing_portal(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_import_config(BulkJobSourceType.PORTAL_API, {})
        assert exc_info.value.status_code == 422
        assert "portal" in exc_info.value.detail

    def test_portal_api_valid(self):
        _validate_import_config(BulkJobSourceType.PORTAL_API, {"portal": "overpass"})

    def test_search_source_no_validation(self):
        _validate_import_config(BulkJobSourceType.SEARCH, {})


# ===========================================================================
# Test _validate_export_config
# ===========================================================================


class TestValidateExportConfig:
    """Tests for the _validate_export_config function."""

    def test_search_source_missing_all(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_export_config(BulkJobSourceType.SEARCH, {})
        assert exc_info.value.status_code == 422
        assert "query" in exc_info.value.detail

    def test_search_source_with_query(self):
        _validate_export_config(BulkJobSourceType.SEARCH, {"query": "test"})

    def test_search_source_with_filters(self):
        _validate_export_config(BulkJobSourceType.SEARCH, {"filters": {"city": "Warsaw"}})

    def test_search_source_with_property_ids(self):
        _validate_export_config(BulkJobSourceType.SEARCH, {"property_ids": ["id-1", "id-2"]})

    def test_url_source_no_validation(self):
        _validate_export_config(BulkJobSourceType.URL, {})

    def test_file_upload_source_no_validation(self):
        _validate_export_config(BulkJobSourceType.FILE_UPLOAD, {})

    def test_portal_api_source_no_validation(self):
        _validate_export_config(BulkJobSourceType.PORTAL_API, {})


# ===========================================================================
# Test _process_url_import background helper
# ===========================================================================


def _setup_data_loaders_mock(csv_cls=None, excel_cls=None):
    """Install mock data.loaders module into sys.modules for lazy import."""
    loaders_mod = types.ModuleType("data.loaders")
    # Always set both to satisfy `from data.loaders import DataLoaderCsv, DataLoaderExcel`
    loaders_mod.DataLoaderCsv = csv_cls or MagicMock()
    loaders_mod.DataLoaderExcel = excel_cls or MagicMock()
    sys.modules["data.loaders"] = loaders_mod
    return loaders_mod


def _setup_data_adapters_mock(get_adapter_fn=None):
    """Install mock data.adapters module into sys.modules for lazy import."""
    import importlib

    adapters_mod = types.ModuleType("data.adapters")
    # The stub stands in for the package, so it needs a path and the
    # submodules the code imports from it.
    adapters_mod.__path__ = []
    adapters_mod.get_adapter = get_adapter_fn or MagicMock()
    for submodule in ("base", "registry"):
        real = importlib.import_module(f"data.adapters.{submodule}")
        setattr(adapters_mod, submodule, real)
        sys.modules[f"data.adapters.{submodule}"] = real
    sys.modules["data.adapters"] = adapters_mod
    return adapters_mod


class TestProcessUrlImport:
    """Tests for _process_url_import background processing function."""

    @pytest.mark.asyncio
    async def test_csv_url_processing(self, db_session: AsyncSession):
        job = BulkJob(
            id="url-csv-001",
            job_type="import",
            source_type="url",
            config={"file_urls": ["https://example.com/data.csv"]},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_loader = AsyncMock()
        mock_loader.load.return_value = [{"id": 1}, {"id": 2}]
        mock_csv_cls = MagicMock(return_value=mock_loader)

        _setup_data_loaders_mock(csv_cls=mock_csv_cls)
        await _process_url_import(job, {"file_urls": ["https://example.com/data.csv"]}, db_session)

        assert job.records_total == 2
        assert job.records_processed == 2
        assert job.records_failed == 0

    @pytest.mark.asyncio
    async def test_excel_url_processing(self, db_session: AsyncSession):
        job = BulkJob(
            id="url-excel-001",
            job_type="import",
            source_type="url",
            config={"file_urls": ["https://example.com/data.xlsx"]},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_loader = AsyncMock()
        mock_loader.load.return_value = [{"id": 1}]
        mock_excel_cls = MagicMock(return_value=mock_loader)

        _setup_data_loaders_mock(excel_cls=mock_excel_cls)
        await _process_url_import(
            job,
            {"file_urls": ["https://example.com/data.xlsx"]},
            db_session,
        )

        assert job.records_total == 1
        assert job.records_processed == 1

    @pytest.mark.asyncio
    async def test_xls_extension(self, db_session: AsyncSession):
        job = BulkJob(
            id="url-xls-001",
            job_type="import",
            source_type="url",
            config={"file_urls": ["https://example.com/data.xls"]},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_loader = AsyncMock()
        mock_loader.load.return_value = [{"id": 1}]
        mock_excel_cls = MagicMock(return_value=mock_loader)

        _setup_data_loaders_mock(excel_cls=mock_excel_cls)
        await _process_url_import(
            job,
            {"file_urls": ["https://example.com/data.xls"]},
            db_session,
        )

        assert job.records_processed == 1

    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, db_session: AsyncSession):
        job = BulkJob(
            id="url-unsupported-001",
            job_type="import",
            source_type="url",
            config={"file_urls": ["https://example.com/data.txt"]},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        _setup_data_loaders_mock()
        await _process_url_import(
            job,
            {"file_urls": ["https://example.com/data.txt"]},
            db_session,
        )

        assert job.records_total == 0
        assert job.records_failed == 1

    @pytest.mark.asyncio
    async def test_loader_exception(self, db_session: AsyncSession):
        job = BulkJob(
            id="url-error-001",
            job_type="import",
            source_type="url",
            config={"file_urls": ["https://example.com/data.csv"]},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_loader = AsyncMock()
        mock_loader.load.side_effect = Exception("Download failed")
        mock_csv_cls = MagicMock(return_value=mock_loader)

        _setup_data_loaders_mock(csv_cls=mock_csv_cls)
        await _process_url_import(
            job,
            {"file_urls": ["https://example.com/data.csv"]},
            db_session,
        )

        assert job.records_failed == 1

    @pytest.mark.asyncio
    async def test_multiple_urls_mixed_results(self, db_session: AsyncSession):
        job = BulkJob(
            id="url-mixed-001",
            job_type="import",
            source_type="url",
            config={
                "file_urls": [
                    "https://example.com/a.csv",
                    "https://example.com/b.txt",
                ]
            },
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_loader = AsyncMock()
        mock_loader.load.return_value = [{"id": 1}]
        mock_csv_cls = MagicMock(return_value=mock_loader)

        _setup_data_loaders_mock(csv_cls=mock_csv_cls)
        await _process_url_import(
            job,
            {
                "file_urls": [
                    "https://example.com/a.csv",
                    "https://example.com/b.txt",
                ]
            },
            db_session,
        )

        assert job.records_total == 1
        assert job.records_processed == 1
        assert job.records_failed == 1

    @pytest.mark.asyncio
    async def test_custom_header_row(self, db_session: AsyncSession):
        job = BulkJob(
            id="url-header-001",
            job_type="import",
            source_type="url",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_loader = AsyncMock()
        mock_loader.load.return_value = [{"id": 1}]
        mock_csv_cls = MagicMock(return_value=mock_loader)

        _setup_data_loaders_mock(csv_cls=mock_csv_cls)
        await _process_url_import(
            job,
            {"file_urls": ["https://example.com/data.csv"], "header_row": 2},
            db_session,
        )
        mock_csv_cls.assert_called_once_with("https://example.com/data.csv", header_row=2)

    @pytest.mark.asyncio
    async def test_sheet_name_for_excel(self, db_session: AsyncSession):
        job = BulkJob(
            id="url-sheet-001",
            job_type="import",
            source_type="url",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_loader = AsyncMock()
        mock_loader.load.return_value = [{"id": 1}]
        mock_excel_cls = MagicMock(return_value=mock_loader)

        _setup_data_loaders_mock(excel_cls=mock_excel_cls)
        await _process_url_import(
            job,
            {
                "file_urls": ["https://example.com/data.xlsx"],
                "sheet_name": "Sheet2",
                "header_row": 1,
            },
            db_session,
        )
        mock_excel_cls.assert_called_once_with(
            "https://example.com/data.xlsx", sheet_name="Sheet2", header_row=1
        )


# ===========================================================================
# Test _process_file_import background helper
# ===========================================================================


class TestProcessFileImport:
    """Tests for _process_file_import background processing function."""

    @pytest.mark.asyncio
    async def test_successful_file_import(self, db_session: AsyncSession):
        job = BulkJob(
            id="file-ok-001",
            job_type="import",
            source_type="file_upload",
            config={"temp_file_path": "/tmp/upload.csv"},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        await _process_file_import(
            job,
            {"temp_file_path": "/tmp/upload.csv", "filename": "upload.csv"},
            db_session,
        )

        assert job.records_total == 1
        assert job.records_processed == 1
        assert job.progress_percent == 100.0

    @pytest.mark.asyncio
    async def test_missing_temp_file_path(self, db_session: AsyncSession):
        job = BulkJob(
            id="file-no-path-001",
            job_type="import",
            source_type="file_upload",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        with pytest.raises(ValueError, match="temp_file_path is required"):
            await _process_file_import(job, {}, db_session)

    @pytest.mark.asyncio
    async def test_null_temp_file_path(self, db_session: AsyncSession):
        job = BulkJob(
            id="file-null-path-001",
            job_type="import",
            source_type="file_upload",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        with pytest.raises(ValueError, match="temp_file_path is required"):
            await _process_file_import(
                job, {"temp_file_path": None, "filename": "test.csv"}, db_session
            )


# ===========================================================================
# Test _process_portal_import background helper
# ===========================================================================


class TestProcessPortalImport:
    """Tests for _process_portal_import background processing function."""

    @pytest.mark.asyncio
    async def test_successful_portal_import(self, db_session: AsyncSession):
        job = BulkJob(
            id="portal-ok-001",
            job_type="import",
            source_type="portal_api",
            config={"portal": "overpass"},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        # The adapter answers with a fetch result: it takes a PortalFilter
        # and returns the properties it found.
        mock_adapter = MagicMock()
        mock_adapter.fetch.return_value = MagicMock(
            properties=[{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]
        )
        mock_get_adapter = MagicMock(return_value=mock_adapter)

        _setup_data_adapters_mock(get_adapter_fn=mock_get_adapter)
        await _process_portal_import(
            job,
            {
                "portal": "overpass",
                "city": "Warsaw",
                "filters": {"listing_type": "rent"},
                "limit": 50,
            },
            db_session,
        )

        assert job.records_total == 3
        assert job.records_processed == 3
        assert job.progress_percent == 100.0
        portal_filters = mock_adapter.fetch.call_args.args[0]
        assert portal_filters.city == "Warsaw"
        assert portal_filters.listing_type == "rent"
        assert portal_filters.limit == 50

    @pytest.mark.asyncio
    async def test_missing_portal(self, db_session: AsyncSession):
        job = BulkJob(
            id="portal-no-name-001",
            job_type="import",
            source_type="portal_api",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        with pytest.raises(ValueError, match="portal is required"):
            await _process_portal_import(job, {}, db_session)

    @pytest.mark.asyncio
    async def test_default_listing_type(self, db_session: AsyncSession):
        job = BulkJob(
            id="portal-default-001",
            job_type="import",
            source_type="portal_api",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_adapter = MagicMock()
        mock_adapter.fetch.return_value = MagicMock(properties=[])
        mock_get_adapter = MagicMock(return_value=mock_adapter)

        _setup_data_adapters_mock(get_adapter_fn=mock_get_adapter)
        await _process_portal_import(
            job,
            {"portal": "overpass", "city": "Krakow"},
            db_session,
        )

        portal_filters = mock_adapter.fetch.call_args.args[0]
        assert portal_filters.city == "Krakow"
        assert portal_filters.listing_type == "rent"
        assert portal_filters.limit == 50

    @pytest.mark.asyncio
    async def test_adapter_exception_reraises(self, db_session: AsyncSession):
        job = BulkJob(
            id="portal-err-001",
            job_type="import",
            source_type="portal_api",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        mock_adapter = MagicMock()
        mock_adapter.fetch.side_effect = ConnectionError("Timeout")
        mock_get_adapter = MagicMock(return_value=mock_adapter)

        _setup_data_adapters_mock(get_adapter_fn=mock_get_adapter)
        with pytest.raises(ConnectionError, match="Timeout"):
            await _process_portal_import(
                job,
                {"portal": "overpass", "city": "Warsaw"},
                db_session,
            )


# ===========================================================================
# Helper to build mock session/engine for _run_import_job / _run_export_job
# ===========================================================================


def _make_mock_async_context_manager(return_value):
    """Create an async context manager mock."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=return_value)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _make_mock_session_factory(session):
    """Create a mock async_sessionmaker that returns the given session."""
    factory = MagicMock()
    factory.return_value = _make_mock_async_context_manager(session)
    return factory


def _make_mock_engine():
    """Create a mock async engine."""
    engine = MagicMock()
    engine.dispose = AsyncMock()
    return engine


def _mock_db_execute_first_call_returns(job):
    """Create execute mock where first call returns the job."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    return mock_result


# ===========================================================================
# Test _run_import_job background task
# ===========================================================================


class TestRunImportJob:
    """Tests for _run_import_job background task function."""

    @pytest.mark.asyncio
    async def test_job_not_found(self):
        mock_engine = _make_mock_engine()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_factory = _make_mock_session_factory(mock_session)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
        ):
            await _run_import_job("nonexistent-id", "sqlite+aiosqlite:///:memory:")

        mock_engine.dispose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_url_import_success(self, db_session: AsyncSession):
        job = BulkJob(
            id="run-url-001",
            job_type="import",
            source_type="url",
            config={"file_urls": ["https://example.com/data.csv"]},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_loader = AsyncMock()
        mock_loader.load.return_value = [{"id": 1}]
        mock_csv_cls = MagicMock(return_value=mock_loader)

        _setup_data_loaders_mock(csv_cls=mock_csv_cls)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
        ):
            await _run_import_job("run-url-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value
        assert job.progress_percent == 100.0
        assert job.completed_at is not None
        assert job.expires_at is not None
        assert job.result_data is not None
        assert job.result_data is not None
        assert job.result_data["source_type"] == "url"

    @pytest.mark.asyncio
    async def test_unknown_source_type(self, db_session: AsyncSession):
        job = BulkJob(
            id="run-unknown-001",
            job_type="import",
            source_type="unknown_source",
            config={},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
        ):
            await _run_import_job("run-unknown-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.FAILED.value
        assert job.error_message is not None
        assert "Unknown source type" in job.error_message

    @pytest.mark.asyncio
    async def test_exception_sets_failed_status(self, db_session: AsyncSession):
        job = BulkJob(
            id="run-exc-001",
            job_type="import",
            source_type="url",
            config={"file_urls": ["https://example.com/data.csv"]},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = job
            return result

        actual_db.execute = AsyncMock(side_effect=mock_execute)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs._process_url_import", side_effect=RuntimeError("Crash")),
        ):
            await _run_import_job("run-exc-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.FAILED.value
        assert job.error_message is not None
        assert "Crash" in job.error_message
        assert job.error_details is not None
        assert job.error_details is not None
        assert job.error_details["exception_type"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_file_upload_import(self, db_session: AsyncSession):
        job = BulkJob(
            id="run-file-001",
            job_type="import",
            source_type="file_upload",
            config={"temp_file_path": "/tmp/upload.csv"},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
        ):
            await _run_import_job("run-file-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value
        assert job.records_processed == 1

    @pytest.mark.asyncio
    async def test_portal_api_import(self, db_session: AsyncSession):
        job = BulkJob(
            id="run-portal-001",
            job_type="import",
            source_type="portal_api",
            config={"portal": "overpass"},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_adapter = MagicMock()
        mock_adapter.fetch.return_value = MagicMock(properties=[{"id": "p1"}])
        mock_get_adapter = MagicMock(return_value=mock_adapter)

        _setup_data_adapters_mock(get_adapter_fn=mock_get_adapter)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
        ):
            await _run_import_job("run-portal-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value
        assert job.records_processed == 1

    @pytest.mark.asyncio
    async def test_exception_in_error_handler(self, db_session: AsyncSession):
        job = BulkJob(
            id="run-dblerr-001",
            job_type="import",
            source_type="url",
            config={"file_urls": ["https://example.com/data.csv"]},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        call_count = [0]

        async def mock_execute(_stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                result = MagicMock()
                result.scalar_one_or_none.return_value = job
                return result
            # Second call in error handler also raises
            raise Exception("DB also broken")

        actual_db.execute = AsyncMock(side_effect=mock_execute)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        _setup_data_loaders_mock(csv_cls=MagicMock(side_effect=RuntimeError("Crash")))

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
        ):
            # Should not raise - error handler swallows the exception
            await _run_import_job("run-dblerr-001", "sqlite+aiosqlite:///:memory:")

        mock_engine.dispose.assert_awaited_once()


# ===========================================================================
# Test _run_export_job background task
# ===========================================================================


class TestRunExportJob:
    """Tests for _run_export_job background task function."""

    @pytest.mark.asyncio
    async def test_job_not_found(self):
        mock_engine = _make_mock_engine()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = _make_mock_session_factory(mock_session)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
        ):
            await _run_export_job("nonexistent-id", "sqlite+aiosqlite:///:memory:")

        mock_engine.dispose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_export_search_source(self, db_session: AsyncSession):
        job = BulkJob(
            id="exp-search-001",
            job_type="export",
            source_type="search",
            config={
                "format": "csv",
                "query": "apartments",
                "limit": 10,
            },
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_store = MagicMock()
        doc1 = MagicMock()
        doc1.metadata = {"id": "p1", "city": "Warsaw"}
        doc2 = MagicMock()
        doc2.metadata = {"id": "p2", "city": "Krakow"}
        mock_store.hybrid_search.return_value = [(doc1, 0.9), (doc2, 0.8)]

        mock_exporter = MagicMock()
        mock_exporter.df = MagicMock()
        mock_exporter.df.columns = ["id", "city"]
        mock_exporter.export.return_value = "id,city\np1,Warsaw\np2,Krakow"

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs.get_vector_store", return_value=mock_store),
            patch("api.routers.bulk_jobs.PropertyExporter", return_value=mock_exporter),
        ):
            await _run_export_job("exp-search-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value
        assert job.records_total == 2
        assert job.records_processed == 2
        assert job.progress_percent == 100.0
        assert job.result_data is not None
        assert job.result_data["format"] == "csv"
        assert job.result_data is not None
        assert job.result_data["records_exported"] == 2
        assert job.completed_at is not None
        assert job.expires_at is not None

    @pytest.mark.asyncio
    async def test_export_with_property_ids(self, db_session: AsyncSession):
        """Runs export job using property_ids in config (non-search source_type)."""
        job = BulkJob(
            id="exp-ids-001",
            job_type="export",
            source_type="url",
            config={
                "format": "csv",
                "property_ids": ["p1", "p2"],
            },
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_store = MagicMock()
        doc = MagicMock()
        doc.metadata = {"id": "p1"}
        mock_store.get_properties_by_ids.return_value = [doc]

        mock_exporter = MagicMock()
        mock_exporter.df = MagicMock()
        mock_exporter.df.columns = ["id"]
        mock_exporter.export.return_value = "id\np1"

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs.get_vector_store", return_value=mock_store),
            patch("api.routers.bulk_jobs.PropertyExporter", return_value=mock_exporter),
        ):
            await _run_export_job("exp-ids-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value
        assert job.records_total == 1
        mock_store.get_properties_by_ids.assert_called_once_with(["p1", "p2"])

    @pytest.mark.asyncio
    async def test_export_vector_store_unavailable(self, db_session: AsyncSession):
        job = BulkJob(
            id="exp-nostore-001",
            job_type="export",
            source_type="search",
            config={"format": "csv", "query": "test"},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = job
            return result

        actual_db.execute = AsyncMock(side_effect=mock_execute)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs.get_vector_store", return_value=None),
        ):
            await _run_export_job("exp-nostore-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.FAILED.value
        assert job.error_message is not None
        assert "not available" in job.error_message

    @pytest.mark.asyncio
    async def test_export_doc_without_id_metadata(self, db_session: AsyncSession):
        job = BulkJob(
            id="exp-no-id-001",
            job_type="export",
            source_type="search",
            config={"format": "csv", "query": "test"},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_store = MagicMock()
        doc = MagicMock()
        doc.metadata = {"city": "Warsaw"}
        mock_store.hybrid_search.return_value = [(doc, 0.9)]

        mock_exporter = MagicMock()
        mock_exporter.df = MagicMock()
        mock_exporter.df.columns = ["id", "city"]
        mock_exporter.export.return_value = "id,city\nunknown,Warsaw"

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs.get_vector_store", return_value=mock_store),
            patch("api.routers.bulk_jobs.PropertyExporter", return_value=mock_exporter),
        ):
            await _run_export_job("exp-no-id-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value
        assert job.result_data is not None
        assert job.result_data["records_exported"] == 1

    @pytest.mark.asyncio
    async def test_export_doc_with_none_metadata(self, db_session: AsyncSession):
        job = BulkJob(
            id="exp-null-meta-001",
            job_type="export",
            source_type="search",
            config={"format": "csv", "query": "test"},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_store = MagicMock()
        doc = MagicMock()
        doc.metadata = None
        mock_store.hybrid_search.return_value = [(doc, 0.9)]

        mock_exporter = MagicMock()
        mock_exporter.df = MagicMock()
        mock_exporter.df.columns = ["id"]
        mock_exporter.export.return_value = "id\nunknown"

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs.get_vector_store", return_value=mock_store),
            patch("api.routers.bulk_jobs.PropertyExporter", return_value=mock_exporter),
        ):
            await _run_export_job("exp-null-meta-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_export_default_format(self, db_session: AsyncSession):
        """Uses 'json' as default format when not specified in config."""
        job = BulkJob(
            id="exp-defmt-001",
            job_type="export",
            source_type="search",
            config={"query": "test"},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_store = MagicMock()
        mock_store.hybrid_search.return_value = []

        # For JSON format, the exporter.export will call export_to_json which
        # doesn't accept include_header. Since the real PropertyExporter is
        # used for the ExportFormat conversion, we mock it to avoid the real call.
        mock_exporter_instance = MagicMock()
        mock_exporter_instance.df = MagicMock()
        mock_exporter_instance.df.columns = []
        mock_exporter_instance.export.return_value = "[]"

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs.get_vector_store", return_value=mock_store),
            patch("api.routers.bulk_jobs.PropertyExporter", return_value=mock_exporter_instance),
        ):
            await _run_export_job("exp-defmt-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value
        assert job.result_data is not None
        assert job.result_data["format"] == "json"

    @pytest.mark.asyncio
    async def test_export_with_columns_and_header(self, db_session: AsyncSession):
        job = BulkJob(
            id="exp-cols-001",
            job_type="export",
            source_type="search",
            config={
                "query": "test",
                "format": "csv",
                "columns": ["id", "price"],
                "include_header": False,
            },
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_store = MagicMock()
        doc = MagicMock()
        doc.metadata = {"id": "p1", "price": 1000}
        mock_store.hybrid_search.return_value = [(doc, 0.9)]

        mock_exporter = MagicMock()
        mock_exporter.df = MagicMock()
        mock_exporter.df.columns = ["id", "price"]
        mock_exporter.export.return_value = "p1,1000"

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs.get_vector_store", return_value=mock_store),
            patch("api.routers.bulk_jobs.PropertyExporter", return_value=mock_exporter),
        ):
            await _run_export_job("exp-cols-001", "sqlite+aiosqlite:///:memory:")

        mock_exporter.export.assert_called_once()
        call_kwargs = mock_exporter.export.call_args
        assert call_kwargs[1]["columns"] == ["id", "price"]
        assert call_kwargs[1]["include_header"] is False

    @pytest.mark.asyncio
    async def test_export_exception_sets_failed(self, db_session: AsyncSession):
        job = BulkJob(
            id="exp-exc-001",
            job_type="export",
            source_type="search",
            config={"query": "test", "format": "csv"},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = job
            return result

        actual_db.execute = AsyncMock(side_effect=mock_execute)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch(
                "api.routers.bulk_jobs.get_vector_store", side_effect=RuntimeError("Store error")
            ),
        ):
            await _run_export_job("exp-exc-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.FAILED.value
        assert job.error_message is not None
        assert "Store error" in job.error_message

    @pytest.mark.asyncio
    async def test_export_non_search_no_property_ids(self, db_session: AsyncSession):
        job = BulkJob(
            id="exp-empty-001",
            job_type="export",
            source_type="url",
            config={"format": "csv"},
            status="pending",
        )
        db_session.add(job)
        await db_session.flush()

        actual_db: Any = db_session
        mock_engine = _make_mock_engine()

        mock_result = _mock_db_execute_first_call_returns(job)
        actual_db.execute = AsyncMock(return_value=mock_result)
        actual_db.commit = AsyncMock()
        actual_db.flush = AsyncMock()

        mock_factory = _make_mock_session_factory(actual_db)

        mock_store = MagicMock()
        mock_exporter = MagicMock()
        mock_exporter.df = MagicMock()
        mock_exporter.df.columns = []
        mock_exporter.export.return_value = ""

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_factory),
            patch("api.routers.bulk_jobs.get_vector_store", return_value=mock_store),
            patch("api.routers.bulk_jobs.PropertyExporter", return_value=mock_exporter),
        ):
            await _run_export_job("exp-empty-001", "sqlite+aiosqlite:///:memory:")

        assert job.status == BulkJobStatus.COMPLETED.value
        assert job.records_total == 0
        assert job.records_processed == 0


# ===========================================================================
# Test create_import_job route
# ===========================================================================


class TestCreateImportJobRoutes:
    """Tests for POST /bulk-jobs/import route."""

    @pytest.mark.asyncio
    async def test_create_url_import(self, client: AsyncClient, auth_headers: dict):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task") as mock_add_task:
            response = await client.post(
                "/api/v1/bulk-jobs/import",
                headers=auth_headers,
                json={
                    "source_type": "url",
                    "config": {"file_urls": ["https://example.com/data.csv"]},
                    "source_name": "Test Import",
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "import"
        assert data["status"] == "pending"
        assert data["message"] == "Import job started"
        mock_add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_file_upload_import(self, client: AsyncClient, auth_headers: dict):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/import",
                headers=auth_headers,
                json={
                    "source_type": "file_upload",
                    "config": {
                        "temp_file_path": "/tmp/upload.csv",
                        "filename": "upload.csv",
                    },
                },
            )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_portal_import(self, client: AsyncClient, auth_headers: dict):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/import",
                headers=auth_headers,
                json={
                    "source_type": "portal_api",
                    "config": {"portal": "overpass", "city": "Warsaw"},
                },
            )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_url_import_missing_urls(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={"source_type": "url", "config": {}},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_url_import_invalid_url(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={
                "source_type": "url",
                "config": {"file_urls": ["not-a-valid-url"]},
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_url_import_file_urls_not_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={
                "source_type": "url",
                "config": {"file_urls": "not-a-list"},
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_file_upload_missing_temp_path(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={"source_type": "file_upload", "config": {}},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_portal_missing_portal_name(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={"source_type": "portal_api", "config": {}},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_source_type(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={"source_type": "invalid_type", "config": {}},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_import_job_creates_db_record(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/import",
                headers=auth_headers,
                json={
                    "source_type": "url",
                    "config": {"file_urls": ["https://example.com/data.csv"]},
                    "source_name": "DB Test",
                },
            )
        assert response.status_code == 201
        job_id = response.json()["id"]

        from sqlalchemy import select

        result = await db_session.execute(select(BulkJob).where(BulkJob.id == job_id))
        job = result.scalar_one_or_none()
        assert job is not None
        assert job.job_type == "import"
        assert job.config["source_name"] == "DB Test"


# ===========================================================================
# Test create_export_job route
# ===========================================================================


class TestCreateExportJobRoutes:
    """Tests for POST /bulk-jobs/export route."""

    @pytest.mark.asyncio
    async def test_create_csv_export(self, client: AsyncClient, auth_headers: dict):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task") as mock_add_task:
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "csv",
                    "source_type": "search",
                    "config": {"query": "apartments in Warsaw"},
                    "include_header": True,
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "export"
        assert data["status"] == "pending"
        assert data["message"] == "Export job started"
        mock_add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_export_invalid_format(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/bulk-jobs/export",
            headers=auth_headers,
            json={
                "format": "invalid_format",
                "source_type": "search",
                "config": {"query": "test"},
            },
        )
        assert response.status_code == 400
        assert "Invalid format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_export_missing_config_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/v1/bulk-jobs/export",
            headers=auth_headers,
            json={
                "format": "csv",
                "source_type": "search",
                "config": {},
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_export_all_valid_formats(self, client: AsyncClient, auth_headers: dict):
        valid_formats = ["csv", "json", "xlsx", "md", "pdf", "parquet"]
        for fmt in valid_formats:
            with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
                response = await client.post(
                    "/api/v1/bulk-jobs/export",
                    headers=auth_headers,
                    json={
                        "format": fmt,
                        "source_type": "search",
                        "config": {"query": "test"},
                    },
                )
            assert response.status_code == 201, f"Format {fmt} should be valid"

    @pytest.mark.asyncio
    async def test_export_with_columns(self, client: AsyncClient, auth_headers: dict):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "json",
                    "source_type": "search",
                    "config": {"query": "apartments"},
                    "columns": ["id", "price", "city"],
                },
            )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_export_with_property_ids(self, client: AsyncClient, auth_headers: dict):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "xlsx",
                    "source_type": "search",
                    "config": {"property_ids": ["p1", "p2"]},
                },
            )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_export_with_filters(self, client: AsyncClient, auth_headers: dict):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "csv",
                    "source_type": "search",
                    "config": {"filters": {"city": "Warsaw"}},
                },
            )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_export_creates_db_record(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "csv",
                    "source_type": "search",
                    "config": {"query": "test"},
                },
            )
        assert response.status_code == 201
        job_id = response.json()["id"]

        from sqlalchemy import select

        result = await db_session.execute(select(BulkJob).where(BulkJob.id == job_id))
        job = result.scalar_one_or_none()
        assert job is not None
        assert job.job_type == "export"
        assert job.config["format"] == "csv"
        assert job.config["include_header"] is True


# ===========================================================================
# Test list_bulk_jobs route
# ===========================================================================


class TestListBulkJobsRoutes:
    """Tests for GET /bulk-jobs route."""

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/bulk-jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["jobs"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_with_jobs(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_import_job: BulkJob,
    ):
        response = await client.get("/api/v1/bulk-jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["jobs"]) >= 1

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        for i in range(25):
            job = BulkJob(
                id=f"job-page-{i:03d}",
                job_type="import",
                source_type="url",
                config={"file_urls": [f"https://example.com/data{i}.csv"]},
                status="completed",
            )
            db_session.add(job)
        await db_session.flush()

        response = await client.get("/api/v1/bulk-jobs?page=1&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["jobs"]) == 10
        assert data["page"] == 1

        response = await client.get("/api/v1/bulk-jobs?page=3&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 5
        assert data["page"] == 3

    @pytest.mark.asyncio
    async def test_list_filter_by_job_type(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        for jtype in ["import", "export"]:
            job = BulkJob(
                id=f"job-type-{jtype}",
                job_type=jtype,
                source_type="url",
                config={},
                status="completed",
            )
            db_session.add(job)
        await db_session.flush()

        response = await client.get("/api/v1/bulk-jobs?job_type=import", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["job_type"] == "import"

    @pytest.mark.asyncio
    async def test_list_filter_by_status(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        for status_val in ["completed", "failed", "pending"]:
            job = BulkJob(
                id=f"job-status-{status_val}",
                job_type="import",
                source_type="url",
                config={},
                status=status_val,
            )
            db_session.add(job)
        await db_session.flush()

        response = await client.get("/api/v1/bulk-jobs?status=failed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_list_filter_by_source_type(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        for stype in ["url", "portal_api", "search"]:
            job = BulkJob(
                id=f"job-src-{stype}",
                job_type="import" if stype != "search" else "export",
                source_type=stype,
                config={},
                status="completed",
            )
            db_session.add(job)
        await db_session.flush()

        response = await client.get(
            "/api/v1/bulk-jobs?source_type=portal_api", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["source_type"] == "portal_api"

    @pytest.mark.asyncio
    async def test_list_combined_filters(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        for jtype in ["import", "export"]:
            for status_val in ["completed", "failed"]:
                job = BulkJob(
                    id=f"job-combined-{jtype}-{status_val}",
                    job_type=jtype,
                    source_type="url",
                    config={},
                    status=status_val,
                )
                db_session.add(job)
        await db_session.flush()

        response = await client.get(
            "/api/v1/bulk-jobs?job_type=import&status=completed", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["job_type"] == "import"
        assert data["jobs"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_pagination_limits(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/bulk-jobs?page_size=200", headers=auth_headers)
        assert response.status_code == 422

        response = await client.get("/api/v1/bulk-jobs?page=0", headers=auth_headers)
        assert response.status_code == 422


# ===========================================================================
# Test get_bulk_job route
# ===========================================================================


class TestGetBulkJobRoutes:
    """Tests for GET /bulk-jobs/{job_id} route."""

    @pytest.mark.asyncio
    async def test_get_existing_job(
        self, client: AsyncClient, auth_headers: dict, sample_import_job: BulkJob
    ):
        response = await client.get(
            f"/api/v1/bulk-jobs/{sample_import_job.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_import_job.id
        assert data["job_type"] == "import"
        assert data["status"] == "completed"
        assert data["records_total"] == 100
        assert data["progress_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/bulk-jobs/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_job_with_all_fields(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        now = datetime.now(UTC)
        job = BulkJob(
            id="test-fields-001",
            job_type="export",
            source_type="search",
            config={"format": "csv"},
            status="completed",
            records_total=10,
            records_processed=10,
            records_failed=0,
            progress_percent=100.0,
            result_url="https://example.com/download",
            result_data={"format": "csv", "records_exported": 10},
            error_message=None,
            started_at=now,
            completed_at=now,
            expires_at=now,
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.get(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["result_url"] == "https://example.com/download"
        assert data["result_data"]["records_exported"] == 10
        assert data["started_at"] is not None
        assert data["completed_at"] is not None
        assert data["expires_at"] is not None


# ===========================================================================
# Test cancel_bulk_job route
# ===========================================================================


class TestCancelBulkJobRoutes:
    """Tests for POST /bulk-jobs/{job_id}/cancel route."""

    @pytest.mark.asyncio
    async def test_cancel_pending_job(
        self, client: AsyncClient, auth_headers: dict, sample_pending_job: BulkJob
    ):
        response = await client.post(
            f"/api/v1/bulk-jobs/{sample_pending_job.id}/cancel", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["error_message"] == "Job cancelled by user"
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_cancel_running_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        job = BulkJob(
            id="test-running-cancel-001",
            job_type="import",
            source_type="url",
            config={},
            status="running",
            started_at=datetime.now(UTC),
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.post(f"/api/v1/bulk-jobs/{job.id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_job(
        self, client: AsyncClient, auth_headers: dict, sample_import_job: BulkJob
    ):
        response = await client.post(
            f"/api/v1/bulk-jobs/{sample_import_job.id}/cancel", headers=auth_headers
        )
        assert response.status_code == 400
        assert "Cannot cancel" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/bulk-jobs/nonexistent-id/cancel", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_failed_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        job = BulkJob(
            id="test-failed-cancel-001",
            job_type="import",
            source_type="url",
            config={},
            status="failed",
            error_message="Previous error",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.post(f"/api/v1/bulk-jobs/{job.id}/cancel", headers=auth_headers)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_cancelled_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        job = BulkJob(
            id="test-dblcancel-001",
            job_type="import",
            source_type="url",
            config={},
            status="cancelled",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.post(f"/api/v1/bulk-jobs/{job.id}/cancel", headers=auth_headers)
        assert response.status_code == 400


# ===========================================================================
# Test delete_bulk_job route
# ===========================================================================


class TestDeleteBulkJobRoutes:
    """Tests for DELETE /bulk-jobs/{job_id} route."""

    @pytest.mark.asyncio
    async def test_delete_completed_job(
        self, client: AsyncClient, auth_headers: dict, sample_import_job: BulkJob
    ):
        response = await client.delete(
            f"/api/v1/bulk-jobs/{sample_import_job.id}", headers=auth_headers
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_failed_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        job = BulkJob(
            id="test-del-failed-001",
            job_type="import",
            source_type="url",
            config={},
            status="failed",
            error_message="Something went wrong",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.delete(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_cancelled_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        job = BulkJob(
            id="test-del-cancelled-001",
            job_type="import",
            source_type="url",
            config={},
            status="cancelled",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.delete(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_pending_job(
        self, client: AsyncClient, auth_headers: dict, sample_pending_job: BulkJob
    ):
        response = await client.delete(
            f"/api/v1/bulk-jobs/{sample_pending_job.id}", headers=auth_headers
        )
        assert response.status_code == 400
        assert "Cannot delete active job" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_running_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        job = BulkJob(
            id="test-del-running-001",
            job_type="import",
            source_type="url",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.delete(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_nonexistent_job(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/bulk-jobs/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_returns_204_for_completed(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Verify delete returns 204 for a deletable job."""
        job = BulkJob(
            id="test-del-verify-001",
            job_type="export",
            source_type="search",
            config={"format": "csv"},
            status="completed",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.delete(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 204


# ===========================================================================
# Test constants and module-level items
# ===========================================================================


class TestModuleConstants:
    """Tests for module-level constants and configuration."""

    def test_job_result_expiration_hours(self):
        assert JOB_RESULT_EXPIRATION_HOURS == 24

    def test_router_prefix(self):
        assert bulk_jobs.router.prefix == "/bulk-jobs"
        assert "Bulk Jobs" in bulk_jobs.router.tags
