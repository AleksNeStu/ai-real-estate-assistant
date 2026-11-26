import json
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_vector_store
from api.main import app
from data.schemas import Property, PropertyCollection


@pytest.fixture(autouse=True)
def _open_the_admin_gate(open_admin_gate):
    """These tests exercise the handlers behind the gate, not the gate."""


client = TestClient(app)


@pytest.fixture
def valid_headers():
    return {"X-API-Key": "dev-secret-key"}


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    return store


def test_admin_health_check(valid_headers, mock_vector_store):
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store

    # Mock load_collection to return something (healthy)
    with patch("api.routers.admin.load_collection") as mock_load:
        mock_load.return_value = PropertyCollection(properties=[], total_count=0)

        response = client.get("/api/v1/admin/health", headers=valid_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    app.dependency_overrides = {}


def test_admin_version_endpoint_returns_runtime_build_info(valid_headers):
    response = client.get("/api/v1/admin/version", headers=valid_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["version"]
    assert data["environment"]
    assert data["app_title"]
    assert re.match(r"^\d+\.\d+\.\d+$", data["python_version"])
    assert data["platform"]


def test_admin_ingest(valid_headers):
    # Mock DataLoaderCsv
    with (
        patch("api.routers.admin.DataLoaderCsv") as MockLoader,
        patch("api.routers.admin.save_collection") as mock_save,
    ):
        mock_instance = MockLoader.return_value
        # Mock load_df
        mock_instance.load_df.return_value = pd.DataFrame()
        # Mock load_format_df to return a valid DF with property columns
        mock_instance.load_format_df.return_value = pd.DataFrame(
            [
                {
                    "id": "1",
                    "title": "Test Property",
                    "price": 100000,
                    "city": "Test City",
                    "rooms": 2,
                    "area_sqm": 50,
                }
            ]
        )

        payload = {"file_urls": ["http://example.com/data.csv"]}
        response = client.post("/api/v1/admin/ingest", json=payload, headers=valid_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Ingestion successful"
        assert data["properties_processed"] == 1

        mock_save.assert_called_once()


def test_admin_reindex(valid_headers, mock_vector_store):
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store

    # Mock load_collection to return data
    with patch("api.routers.admin.load_collection") as mock_load:
        mock_load.return_value = PropertyCollection(
            properties=[Property(id="1", title="Test Property", price=100, city="City", rooms=1)],
            total_count=1,
        )

        response = client.post("/api/v1/admin/reindex", json={}, headers=valid_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Reindexing successful"
        assert data["count"] == 1

        mock_vector_store.add_properties.assert_called_once()

    app.dependency_overrides = {}


def test_admin_endpoints_unauthorized(open_admin_gate):
    """Without the key and without an identity the request is refused.

    The gate is closed for this one test: the module opens it for the tests
    that exercise the handlers behind it.
    """
    from api.deps.auth import require_admin_access

    app.dependency_overrides.pop(require_admin_access, None)

    deployment = MagicMock(admin_emails=[], demo_api_key_bypass=False)
    key = MagicMock(api_access_key="dev-secret-key", api_access_keys=[], demo_api_key_bypass=False)
    with (
        patch("api.deps.auth.get_settings", return_value=deployment),
        patch("api.deps.auth._has_admin_account", new=AsyncMock(return_value=False)),
        patch("api.auth.get_settings", return_value=key),
    ):
        response = client.get("/api/v1/admin/health")
        assert response.status_code == 401

        response = client.get("/api/v1/admin/version")
        assert response.status_code == 401

        response = client.post("/api/v1/admin/ingest", json={})
        assert response.status_code == 401

        response = client.post("/api/v1/admin/reindex", json={})
        assert response.status_code == 401


def test_admin_reindex_no_cache_returns_404(valid_headers, mock_vector_store):
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    with patch("api.routers.admin.load_collection") as mock_load:
        mock_load.return_value = None
        response = client.post("/api/v1/admin/reindex", json={}, headers=valid_headers)
        assert response.status_code == 404
        assert "Run ingestion first" in response.json()["detail"]
    app.dependency_overrides = {}


def test_admin_ingest_no_urls_returns_400(valid_headers, monkeypatch):
    import api.routers.admin as admin_router

    # Ensure no defaults configured
    monkeypatch.setattr(admin_router, "settings", SimpleNamespace(default_datasets=[]))
    response = client.post("/api/v1/admin/ingest", json={"file_urls": []}, headers=valid_headers)
    assert response.status_code == 400
    assert "No URLs provided" in response.json()["detail"]


def test_admin_notifications_stats_endpoint_returns_queue_and_sent_counts(valid_headers, tmp_path):
    (tmp_path / "sent_alerts.json").write_text(
        json.dumps({"alerts": ["sent-1", "sent-2"], "last_updated": "2026-01-24T10:00:00"}),
        encoding="utf-8",
    )
    (tmp_path / "pending_alerts.json").write_text(
        json.dumps(
            {
                "alerts": [{"alert_type": "price_drop", "created_at": "2026-01-24T10:01:00"}],
                "last_updated": "2026-01-24T10:01:10",
            }
        ),
        encoding="utf-8",
    )

    class _ThreadStub:
        def is_alive(self) -> bool:
            return False

    class _SchedulerStub:
        _storage_path_alerts = str(tmp_path)
        _thread = _ThreadStub()

    old_scheduler = getattr(app.state, "scheduler", None)
    app.state.scheduler = _SchedulerStub()
    try:
        response = client.get("/api/v1/admin/notifications-stats", headers=valid_headers)
    finally:
        if old_scheduler is None:
            delattr(app.state, "scheduler")
        else:
            app.state.scheduler = old_scheduler

    assert response.status_code == 200
    data = response.json()
    assert data["scheduler_running"] is False
    assert data["sent_alerts_total"] == 2
    assert data["pending_alerts_total"] == 1
    assert data["pending_alerts_by_type"]["price_drop"] == 1
