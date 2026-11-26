import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_vector_store
from api.main import app
from data.adapters.base import PortalFetchResult


@pytest.fixture(autouse=True)
def _open_the_admin_gate(open_admin_gate):
    """These tests exercise the handlers behind the gate, not the gate."""


client = TestClient(app)

CSRF_TOKEN = "test-csrf-token"
HEADERS = {"X-API-Key": "test-key", "X-CSRF-Token": CSRF_TOKEN}

# Set the CSRF token cookie on the client
client.cookies.set("csrf_token", CSRF_TOKEN)


@patch("api.routers.admin.DataLoaderExcel")
@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_uses_defaults_and_returns_success(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_csv_cls,
    mock_loader_excel_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = ["http://example.com/test.csv"]
    mock_settings.max_properties = 100  # type: ignore
    mock_loader_excel_cls.detect_source_type.return_value = "csv"

    def _mock_load_format_df(df, rows_count=None):
        # Handle rows_count safely - only use head() if it's a positive int
        if rows_count is not None and isinstance(rows_count, int) and rows_count > 0:
            return df.head(rows_count)
        return df

    loader = MagicMock()
    loader.load_df.return_value = pd.DataFrame([{"city": "Warsaw"}, {"city": "Krakow"}])
    loader.load_format_df.side_effect = _mock_load_format_df
    mock_loader_csv_cls.return_value = loader

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Ingestion successful"
    assert data["properties_processed"] == 2
    assert data["errors"] == []
    assert mock_save_collection.called


@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_returns_400_when_no_urls_and_no_defaults(
    mock_get_settings, mock_settings, mock_loader_cls
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = []

    resp = client.post("/api/v1/admin/ingest", json={"file_urls": []}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No URLs provided and no defaults configured"
    assert not mock_loader_cls.called


@patch("api.routers.admin.DataLoaderExcel")
@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_returns_500_when_no_properties_loaded(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_csv_cls,
    mock_loader_excel_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = ["http://example.com/empty.csv"]
    mock_settings.max_properties = 100  # type: ignore
    mock_loader_excel_cls.detect_source_type.return_value = "csv"

    def _mock_load_format_df(df, rows_count=None):
        if rows_count is not None and isinstance(rows_count, int) and rows_count > 0:
            return df.head(rows_count)
        return df

    loader = MagicMock()
    # DataFrame without required 'city' field, so no properties will be created
    loader.load_df.return_value = pd.DataFrame([{"bad": "row"}])
    loader.load_format_df.side_effect = _mock_load_format_df
    mock_loader_csv_cls.return_value = loader

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "No properties could be loaded"
    assert not mock_save_collection.called


@patch("api.routers.admin.DataLoaderExcel")
@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_returns_errors_when_some_urls_fail(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_csv_cls,
    mock_loader_excel_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    urls = ["http://example.com/ok.csv", "http://example.com/bad.csv"]
    mock_settings.default_datasets = urls
    mock_settings.max_properties = 100  # type: ignore
    mock_loader_excel_cls.detect_source_type.return_value = "csv"

    def _mock_load_format_df(df, rows_count=None):
        if rows_count is not None and isinstance(rows_count, int) and rows_count > 0:
            return df.head(rows_count)
        return df

    ok_loader = MagicMock()
    ok_loader.load_df.return_value = pd.DataFrame([{"city": "Warsaw"}])
    ok_loader.load_format_df.side_effect = _mock_load_format_df

    def _loader(url: str):
        if url.endswith("bad.csv"):
            raise RuntimeError("network down")
        return ok_loader

    mock_loader_csv_cls.side_effect = _loader

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["properties_processed"] == 1
    assert len(data["errors"]) == 1
    assert "Failed to load" in data["errors"][0]
    assert mock_save_collection.called


@patch("api.routers.admin.DataLoaderExcel")
@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_enforces_max_properties_limit(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_csv_cls,
    mock_loader_excel_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.max_properties = 2  # type: ignore
    mock_settings.default_datasets = ["http://example.com/test.csv"]
    mock_loader_excel_cls.detect_source_type.return_value = "csv"

    # Track rows_count passed to format_df
    format_df_calls = []

    def _format_df(df, rows_count=None):
        format_df_calls.append(rows_count)
        if rows_count is not None and isinstance(rows_count, int) and rows_count > 0:
            return df.head(rows_count)
        return df

    loader = MagicMock()
    # Create a DataFrame with 5 rows, but max_properties is 2
    loader.load_df.return_value = pd.DataFrame(
        [
            {"city": "Warsaw"},
            {"city": "Krakow"},
            {"city": "Gdansk"},
            {"city": "Poznan"},
            {"city": "Wroclaw"},
        ]
    )
    loader.load_format_df.side_effect = _format_df
    mock_loader_csv_cls.return_value = loader

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    # Should only process 2 properties (max_properties limit)
    assert data["properties_processed"] == 2
    # Message should indicate limit was reached
    assert "maximum property limit" in data["message"]
    # Verify rows_count was passed correctly (remaining capacity = 2 - 0 = 2)
    assert format_df_calls[0] == 2
    assert mock_save_collection.called


@patch("api.routers.admin.DataLoaderExcel")
@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_returns_500_on_unhandled_exception(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_csv_cls,
    mock_loader_excel_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = ["http://example.com/test.csv"]
    mock_settings.max_properties = 100  # type: ignore
    mock_loader_excel_cls.detect_source_type.return_value = "csv"

    def _mock_load_format_df(df, rows_count=None):
        if rows_count is not None and isinstance(rows_count, int) and rows_count > 0:
            return df.head(rows_count)
        return df

    loader = MagicMock()
    loader.load_df.return_value = pd.DataFrame([{"city": "Warsaw"}])
    loader.load_format_df.side_effect = _mock_load_format_df
    mock_loader_csv_cls.return_value = loader
    mock_save_collection.side_effect = RuntimeError("disk full")

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "disk full"


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_reindex_returns_404_when_no_cache(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = None
    app.dependency_overrides[get_vector_store] = lambda: MagicMock()

    try:
        resp = client.post("/api/v1/admin/reindex", json={}, headers=HEADERS)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "No data in cache. Run ingestion first."
    finally:
        app.dependency_overrides.pop(get_vector_store, None)


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_reindex_returns_503_when_store_unavailable(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = MagicMock(properties=[MagicMock()])
    app.dependency_overrides[get_vector_store] = lambda: None

    try:
        resp = client.post("/api/v1/admin/reindex", json={}, headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Vector store unavailable"


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_reindex_success(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = MagicMock(properties=[MagicMock(), MagicMock()])
    store = MagicMock()
    app.dependency_overrides[get_vector_store] = lambda: store

    try:
        resp = client.post("/api/v1/admin/reindex", json={}, headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Reindexing successful"
    assert data["count"] == 2
    store.add_properties.assert_called_once()


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_reindex_returns_500_when_store_fails(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = MagicMock(properties=[MagicMock()])
    store = MagicMock()
    store.add_properties.side_effect = RuntimeError("boom")
    app.dependency_overrides[get_vector_store] = lambda: store

    try:
        resp = client.post("/api/v1/admin/reindex", json={}, headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 500
    assert resp.json()["detail"] == "boom"


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_health_degraded_when_no_cache_or_store(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = None
    app.dependency_overrides[get_vector_store] = lambda: None

    try:
        resp = client.get("/api/v1/admin/health", headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded (vector store unavailable)"


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_health_degraded_when_no_cache(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = None
    app.dependency_overrides[get_vector_store] = lambda: MagicMock()

    try:
        resp = client.get("/api/v1/admin/health", headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded (no data cache)"


@patch("api.auth.get_settings")
def test_admin_metrics_returns_app_state_metrics(mock_get_settings):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    old_metrics = getattr(app.state, "metrics", None)
    app.state.metrics = {"GET /api/v1/verify-auth": 2}
    try:
        resp = client.get("/api/v1/admin/metrics", headers=HEADERS)
        assert resp.status_code == 200
        # API returns comprehensive metrics structure
        data = resp.json()
        assert "requests" in data
        assert data["requests"] == {"GET /api/v1/verify-auth": 2}
        assert "cache" in data
        assert "vector_store" in data
        assert "uptime_seconds" in data
        assert "version" in data
    finally:
        app.state.metrics = old_metrics if old_metrics is not None else {}


@patch("api.routers.admin.platform.platform")
@patch("api.routers.admin._format_python_version")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_version_returns_expected_fields(
    mock_get_settings,
    mock_settings,
    mock_python_version,
    mock_platform,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.version = "9.9.9"
    mock_settings.environment = "test"
    mock_settings.app_title = "AI REA Test"
    mock_python_version.return_value = "3.12.3"
    mock_platform.return_value = "TestOS-1.0"

    resp = client.get("/api/v1/admin/version", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {
        "version": "9.9.9",
        "environment": "test",
        "app_title": "AI REA Test",
        "python_version": "3.12.3",
        "platform": "TestOS-1.0",
    }


@patch("api.auth.get_settings")
def test_admin_metrics_returns_500_on_invalid_metrics(mock_get_settings):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    old_metrics = getattr(app.state, "metrics", None)

    class _Metrics:
        def __init__(self):
            self._d: dict[str, int] = {}

        def get(self, key, default=0):
            return self._d.get(key, default)

        def __setitem__(self, key, value):
            self._d[key] = value

        def __iter__(self):
            raise TypeError("not iterable")

    app.state.metrics = _Metrics()
    try:
        resp = client.get("/api/v1/admin/metrics", headers=HEADERS)
        assert resp.status_code == 500
        assert resp.json()["detail"]
    finally:
        app.state.metrics = old_metrics if old_metrics is not None else {}


@patch("api.auth.get_settings")
def test_admin_notifications_stats_reads_alert_storage_and_scheduler_state(
    mock_get_settings, tmp_path
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")

    (tmp_path / "sent_alerts.json").write_text(
        json.dumps({"alerts": ["sent-1"], "last_updated": "2026-01-24T10:00:00"}), encoding="utf-8"
    )
    (tmp_path / "pending_alerts.json").write_text(
        json.dumps(
            {
                "alerts": [{"alert_type": "new_property", "created_at": "2026-01-24T10:00:00"}],
                "last_updated": "2026-01-24T10:00:10",
            }
        ),
        encoding="utf-8",
    )

    class _ThreadStub:
        def is_alive(self) -> bool:
            return True

    class _SchedulerStub:
        _storage_path_alerts = str(tmp_path)
        _thread = _ThreadStub()

    old_scheduler = getattr(app.state, "scheduler", None)
    app.state.scheduler = _SchedulerStub()
    try:
        resp = client.get("/api/v1/admin/notifications-stats", headers=HEADERS)
    finally:
        if old_scheduler is None:
            delattr(app.state, "scheduler")
        else:
            app.state.scheduler = old_scheduler

    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduler_running"] is True
    assert data["alerts_storage_path"] == str(tmp_path)
    assert data["sent_alerts_total"] == 1
    assert data["pending_alerts_total"] == 1
    assert data["pending_alerts_by_type"]["new_property"] == 1


@patch("api.routers.admin.ExcelDataLoader")
@patch("api.auth.get_settings")
def test_admin_excel_sheets_returns_rows_and_default_sheet(
    mock_get_settings, mock_excel_loader_cls
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    sheet_names = ["SheetA", "SheetB"]

    root_loader = MagicMock()
    root_loader.get_sheet_names.return_value = sheet_names

    sheet_a_loader = MagicMock()
    sheet_a_loader.load.return_value = pd.DataFrame([{"city": "Warsaw"}])

    sheet_b_loader = MagicMock()
    sheet_b_loader.load.return_value = pd.DataFrame([])

    def _loader_factory(_url, sheet_name=None, **_kwargs):
        if sheet_name is None:
            return root_loader
        if sheet_name == "SheetA":
            return sheet_a_loader
        return sheet_b_loader

    mock_excel_loader_cls.side_effect = _loader_factory

    resp = client.post(
        "/api/v1/admin/excel/sheets",
        json={"file_url": "http://example.com/test.xlsx"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sheet_names"] == sheet_names
    assert data["default_sheet"] == "SheetA"
    assert data["row_count"]["SheetA"] == 1
    assert data["row_count"]["SheetB"] == 0


@patch("api.routers.admin.ExcelDataLoader")
@patch("api.auth.get_settings")
def test_admin_excel_sheets_returns_400_on_import_error(mock_get_settings, mock_excel_loader_cls):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_excel_loader_cls.side_effect = ImportError("missing")

    resp = client.post(
        "/api/v1/admin/excel/sheets",
        json={"file_url": "http://example.com/test.xlsx"},
        headers=HEADERS,
    )
    assert resp.status_code == 400
    assert "Excel libraries not available" in resp.json()["detail"]


@patch("data.adapters.registry.AdapterRegistry.get_all_info")
@patch("api.auth.get_settings")
def test_admin_portals_list_success(mock_get_settings, mock_get_all_info):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_get_all_info.return_value = [
        {
            "name": "p1",
            "display_name": "Portal One",
            "configured": True,
            "has_api_key": True,
            "rate_limit": {"rpm": 10},
        },
        None,
    ]

    resp = client.get("/api/v1/admin/portals", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["adapters"][0]["name"] == "p1"
    assert data["adapters"][0]["display_name"] == "Portal One"


@patch("data.adapters.registry.AdapterRegistry.list_adapters")
@patch("data.adapters.get_adapter")
@patch("api.auth.get_settings")
def test_admin_portal_fetch_returns_404_when_adapter_missing(
    mock_get_settings, mock_get_adapter, mock_list_adapters
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_get_adapter.return_value = None
    mock_list_adapters.return_value = ["p1"]

    resp = client.post(
        "/api/v1/admin/portals/fetch",
        json={"portal": "missing"},
        headers=HEADERS,
    )
    assert resp.status_code == 404
    assert "Available portals" in resp.json()["detail"]


@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("data.adapters.get_adapter")
@patch("api.auth.get_settings")
def test_admin_portal_fetch_returns_success(
    mock_get_settings, mock_get_adapter, mock_settings, mock_save_collection
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.max_properties = 100

    result = PortalFetchResult(
        success=True,
        properties=[{"city": "Warsaw"}],
        count=1,
        source="portal-source",
        source_type="portal",
        errors=[],
    )
    adapter = MagicMock()
    adapter.fetch.return_value = result
    mock_get_adapter.return_value = adapter

    resp = client.post(
        "/api/v1/admin/portals/fetch",
        json={"portal": "p1", "city": "Warsaw", "source_name": "custom-source"},
        headers=HEADERS,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["portal"] == "p1"
    assert data["properties_processed"] == 1
    assert data["source_type"] == "portal"
    assert data["source_name"] == "custom-source"
    assert data["errors"] == []
    assert data["filters_applied"]["city"] == "Warsaw"
    assert mock_save_collection.called


@patch("api.routers.admin.save_collection")
@patch("data.adapters.get_adapter")
@patch("api.auth.get_settings")
def test_admin_portal_fetch_returns_failed_result_when_adapter_errors(
    mock_get_settings, mock_get_adapter, mock_save_collection
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")

    result = PortalFetchResult(
        success=False,
        properties=[],
        count=0,
        source="portal-source",
        source_type="portal",
        errors=["boom"],
    )
    adapter = MagicMock()
    adapter.fetch.return_value = result
    mock_get_adapter.return_value = adapter

    resp = client.post(
        "/api/v1/admin/portals/fetch",
        json={"portal": "p1", "city": "Warsaw"},
        headers=HEADERS,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["message"] == "Failed to fetch from portal: boom"
    assert data["errors"] == ["boom"]
    assert data["properties_processed"] == 0
    assert not mock_save_collection.called


@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("data.adapters.get_adapter")
@patch("api.auth.get_settings")
def test_admin_portal_fetch_returns_no_valid_properties_when_validation_fails(
    mock_get_settings, mock_get_adapter, mock_settings, mock_save_collection
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.max_properties = 100

    result = PortalFetchResult(
        success=True,
        properties=[{"bad": "record"}],
        count=1,
        source="portal-source",
        source_type="portal",
        errors=[],
    )
    adapter = MagicMock()
    adapter.fetch.return_value = result
    mock_get_adapter.return_value = adapter

    resp = client.post(
        "/api/v1/admin/portals/fetch",
        json={"portal": "p1", "city": "Warsaw"},
        headers=HEADERS,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["message"] == "No valid properties could be fetched from portal"
    assert data["properties_processed"] == 0
    assert data["errors"]
    assert not mock_save_collection.called


@patch("data.adapters.get_adapter")
@patch("api.auth.get_settings")
def test_admin_portal_fetch_returns_500_on_adapter_exception(mock_get_settings, mock_get_adapter):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    adapter = MagicMock()
    adapter.fetch.side_effect = RuntimeError("fetch failed")
    mock_get_adapter.return_value = adapter

    resp = client.post(
        "/api/v1/admin/portals/fetch",
        json={"portal": "p1", "city": "Warsaw"},
        headers=HEADERS,
    )
    assert resp.status_code == 500
    assert resp.json()["detail"] == "fetch failed"


@patch("data.adapters.registry.AdapterRegistry.get_all_info")
@patch("api.auth.get_settings")
def test_admin_portals_list_returns_500_on_failure(mock_get_settings, mock_get_all_info):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_get_all_info.side_effect = RuntimeError("registry down")

    resp = client.get("/api/v1/admin/portals", headers=HEADERS)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "registry down"


@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_version_uses_real_python_version(mock_get_settings, mock_settings):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.version = "1.0.0"
    mock_settings.environment = "test"
    mock_settings.app_title = "Test App"

    resp = client.get("/api/v1/admin/version", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert data["environment"] == "test"
    assert data["app_title"] == "Test App"
    assert isinstance(data["python_version"], str)
    assert data["python_version"]
    assert isinstance(data["platform"], str)


@patch("api.routers.admin.ExcelDataLoader")
@patch("api.routers.admin.DataLoaderExcel")
@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_excel_path_includes_sheet_and_header(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_csv_cls,
    mock_loader_excel_cls,
    mock_excel_loader_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = ["http://example.com/test.xlsx"]
    mock_settings.max_properties = 50
    mock_loader_excel_cls.detect_source_type.return_value = "excel"

    excel_loader = MagicMock()
    excel_loader.load_normalized.return_value = pd.DataFrame([{"city": "Warsaw"}])
    mock_excel_loader_cls.return_value = excel_loader

    resp = client.post(
        "/api/v1/admin/ingest",
        json={"sheet_name": "Sheet1", "header_row": 2},
        headers=HEADERS,
    )

    assert resp.status_code == 200
    assert mock_excel_loader_cls.called
    mock_loader_csv_cls.assert_not_called()
    assert mock_save_collection.called


@patch("api.routers.admin.ExcelDataLoader")
@patch("api.auth.get_settings")
def test_admin_excel_sheets_defaults_to_first_sheet_when_all_empty(
    mock_get_settings, mock_excel_loader_cls
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    sheet_names = ["SheetA", "SheetB"]

    root_loader = MagicMock()
    root_loader.get_sheet_names.return_value = sheet_names

    failing_loader = MagicMock()
    failing_loader.load.side_effect = RuntimeError("read error")

    def _loader_factory(_url, sheet_name=None, **_kwargs):
        if sheet_name is None:
            return root_loader
        return failing_loader

    mock_excel_loader_cls.side_effect = _loader_factory

    resp = client.post(
        "/api/v1/admin/excel/sheets",
        json={"file_url": "http://example.com/test.xlsx"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["default_sheet"] == "SheetA"
    assert data["row_count"]["SheetA"] == 0
    assert data["row_count"]["SheetB"] == 0


@patch("api.routers.admin.load_alert_storage_summary")
@patch("api.auth.get_settings")
def test_admin_notifications_stats_without_scheduler_uses_default_path(
    mock_get_settings, mock_summary
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_summary.return_value = SimpleNamespace(
        sent_total=2,
        pending_total=1,
        pending_by_type={"price_drop": 1},
        pending_oldest_created_at="2026-01-24T10:00:00",
        pending_newest_created_at="2026-01-24T10:00:10",
    )

    resp = client.get("/api/v1/admin/notifications-stats", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduler_running"] is False
    assert data["alerts_storage_path"] == ".alerts"
    assert data["sent_alerts_total"] == 2
    assert data["pending_alerts_total"] == 1


@patch("api.routers.admin.load_alert_storage_summary")
@patch("api.auth.get_settings")
def test_admin_notifications_stats_returns_500_on_summary_error(mock_get_settings, mock_summary):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_summary.side_effect = RuntimeError("summary failed")

    resp = client.get("/api/v1/admin/notifications-stats", headers=HEADERS)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "summary failed"


def test_admin_get_available_portals_returns_empty_on_error():
    import api.routers.admin as admin_router

    with patch(
        "data.adapters.registry.AdapterRegistry.list_adapters", side_effect=RuntimeError("boom")
    ):
        assert admin_router._get_available_portal_names() == []
