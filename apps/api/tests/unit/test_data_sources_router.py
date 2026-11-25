"""Comprehensive unit tests for data_sources router.

Covers: CRUD endpoints, sync triggering, test endpoint, validation helpers,
SSRF protection, portal/URL/JSON test helpers, health score calculation,
and all error paths.
"""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "test-api-key")

from api.routers import data_sources
from api.routers.data_sources import (
    _recalculate_health_score,
    _validate_config,
    _validate_url_no_ssrf,
)
from db.database import get_db
from db.models import DataSourceDB, DataSourceSyncHistory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async client with data_sources router."""
    app = FastAPI()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(data_sources.router, prefix="/api/v1")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_data_source(db_session: AsyncSession) -> DataSourceDB:
    """Create a sample data source in the database."""
    ds = DataSourceDB(
        id="ds-test-001",
        name="Test CSV Source",
        source_type="file_upload",
        config={"filename": "properties.csv", "size_bytes": 1024},
        status="pending",
        auto_sync_enabled=False,
    )
    db_session.add(ds)
    await db_session.flush()
    await db_session.refresh(ds)
    return ds


@pytest.fixture
async def sample_active_source(db_session: AsyncSession) -> DataSourceDB:
    """Create a sample active data source."""
    ds = DataSourceDB(
        id="ds-test-002",
        name="Active URL Source",
        source_type="url",
        config={"url": "https://example.com/data.json"},
        status="active",
        last_sync_status="success",
        total_records=50,
        health_score=100.0,
        auto_sync_enabled=True,
        sync_schedule="0 0 * * *",
    )
    db_session.add(ds)
    await db_session.flush()
    await db_session.refresh(ds)
    return ds


@pytest.fixture
async def sample_syncing_source(db_session: AsyncSession) -> DataSourceDB:
    """Create a sample data source that is currently syncing."""
    ds = DataSourceDB(
        id="ds-test-syncing",
        name="Syncing Source",
        source_type="json",
        config={"data": [{"id": 1}]},
        status="syncing",
    )
    db_session.add(ds)
    await db_session.flush()
    await db_session.refresh(ds)
    return ds


@pytest.fixture
async def sample_source_with_history(
    db_session: AsyncSession,
) -> DataSourceDB:
    """Create a data source with sync history entries."""
    ds = DataSourceDB(
        id="ds-hist-001",
        name="Source With History",
        source_type="url",
        config={"url": "https://example.com/data.csv"},
        status="active",
        last_sync_status="success",
    )
    db_session.add(ds)
    await db_session.flush()

    for i in range(3):
        hist = DataSourceSyncHistory(
            id=f"hist-{i:03d}",
            data_source_id=ds.id,
            started_at=datetime(2025, 1, i + 1, tzinfo=UTC),
            completed_at=datetime(2025, 1, i + 1, 1, tzinfo=UTC),
            status="success" if i < 2 else "failed",
            records_processed=10 * (i + 1),
            records_added=5,
            records_updated=3,
            records_skipped=2,
            error_message="timeout" if i == 2 else None,
        )
        db_session.add(hist)

    await db_session.flush()
    await db_session.refresh(ds)
    return ds


# ---------------------------------------------------------------------------
# Helper: create data source payload builders
# ---------------------------------------------------------------------------


def _make_url_source(**overrides) -> dict:
    payload = {
        "name": "Test URL Source",
        "source_type": "url",
        "config": {"url": "https://example.com/data.csv"},
    }
    payload.update(overrides)
    return payload


def _make_file_source(**overrides) -> dict:
    payload = {
        "name": "Test File Source",
        "source_type": "file_upload",
        "config": {"filename": "data.csv"},
    }
    payload.update(overrides)
    return payload


def _make_json_source(**overrides) -> dict:
    payload = {
        "name": "Test JSON Source",
        "source_type": "json",
        "config": {"data": [{"id": 1, "name": "item"}]},
    }
    payload.update(overrides)
    return payload


def _make_portal_source(**overrides) -> dict:
    payload = {
        "name": "Test Portal Source",
        "source_type": "portal_api",
        "config": {"portal": "otodom"},
    }
    payload.update(overrides)
    return payload


def _make_register_source(**overrides) -> dict:
    payload = {
        "name": "Test Register Source",
        "source_type": "register",
        "config": {"city": "Krakow"},
    }
    payload.update(overrides)
    return payload


# ===========================================================================
# Tests: list_data_sources (GET /data-sources)
# ===========================================================================


@pytest.mark.asyncio
async def test_list_data_sources_empty(client: AsyncClient) -> None:
    """List returns empty when no data sources exist."""
    resp = await client.get("/api/v1/data-sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["sources"] == []
    assert body["page"] == 1
    assert body["page_size"] == 20


@pytest.mark.asyncio
async def test_list_data_sources_with_data(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """List returns created data source."""
    resp = await client.get("/api/v1/data-sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["sources"]) == 1
    assert body["sources"][0]["id"] == "ds-test-001"
    assert body["sources"][0]["name"] == "Test CSV Source"


@pytest.mark.asyncio
async def test_list_data_sources_filter_by_status(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
    sample_active_source: DataSourceDB,
) -> None:
    """Filter data sources by status."""
    resp = await client.get("/api/v1/data-sources", params={"status": "active"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["sources"][0]["status"] == "active"


@pytest.mark.asyncio
async def test_list_data_sources_filter_by_source_type(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
    sample_active_source: DataSourceDB,
) -> None:
    """Filter data sources by source_type."""
    resp = await client.get("/api/v1/data-sources", params={"source_type": "file_upload"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["sources"][0]["source_type"] == "file_upload"


@pytest.mark.asyncio
async def test_list_data_sources_pagination(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
    sample_active_source: DataSourceDB,
) -> None:
    """Paginate results correctly."""
    resp = await client.get("/api/v1/data-sources", params={"page": 1, "page_size": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["sources"]) == 1
    assert body["page"] == 1
    assert body["page_size"] == 1

    resp2 = await client.get("/api/v1/data-sources", params={"page": 2, "page_size": 1})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["sources"]) == 1


@pytest.mark.asyncio
async def test_list_data_sources_combined_filters(
    client: AsyncClient,
    sample_active_source: DataSourceDB,
) -> None:
    """Filter by both status and source_type simultaneously."""
    resp = await client.get(
        "/api/v1/data-sources",
        params={"status": "active", "source_type": "url"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["sources"][0]["id"] == "ds-test-002"


# ===========================================================================
# Tests: create_data_source (POST /data-sources)
# ===========================================================================


@pytest.mark.asyncio
async def test_create_url_source(client: AsyncClient) -> None:
    """Create a URL data source successfully."""
    resp = await client.post(
        "/api/v1/data-sources",
        json=_make_url_source(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test URL Source"
    assert body["source_type"] == "url"
    assert body["status"] == "pending"
    assert body["config"]["url"] == "https://example.com/data.csv"
    assert "id" in body
    assert body["health_score"] == 0.0


@pytest.mark.asyncio
async def test_create_file_upload_source(client: AsyncClient) -> None:
    """Create a file_upload data source successfully."""
    resp = await client.post(
        "/api/v1/data-sources",
        json=_make_file_source(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_type"] == "file_upload"


@pytest.mark.asyncio
async def test_create_json_source(client: AsyncClient) -> None:
    """Create a JSON data source successfully."""
    resp = await client.post(
        "/api/v1/data-sources",
        json=_make_json_source(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_type"] == "json"


@pytest.mark.asyncio
async def test_create_portal_api_source(client: AsyncClient) -> None:
    """Create a portal_api data source successfully."""
    resp = await client.post(
        "/api/v1/data-sources",
        json=_make_portal_source(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_type"] == "portal_api"


@pytest.mark.asyncio
async def test_create_source_with_auto_sync(client: AsyncClient) -> None:
    """Create a source with auto_sync_enabled and sync_schedule."""
    payload = _make_url_source(auto_sync_enabled=True, sync_schedule="0 0 * * *")
    resp = await client.post("/api/v1/data-sources", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["auto_sync_enabled"] is True
    assert body["sync_schedule"] == "0 0 * * *"


@pytest.mark.asyncio
async def test_create_url_source_missing_url(client: AsyncClient) -> None:
    """A URL source with no url in its config is refused with the reason."""
    payload = _make_url_source(config={"not_url": "value"})
    resp = await client.post("/api/v1/data-sources", json=payload)
    # _validate_config raises ValueError which becomes 500
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_url_source_invalid_url(client: AsyncClient) -> None:
    """A url that is not a url is refused with the reason."""
    payload = _make_url_source(config={"url": "ftp://example.com/data"})
    resp = await client.post("/api/v1/data-sources", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_portal_source_missing_portal(client: AsyncClient) -> None:
    """A portal source with no portal in its config is refused with the reason."""
    payload = _make_portal_source(config={"not_portal": "value"})
    resp = await client.post("/api/v1/data-sources", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_json_source_missing_data_and_url(client: AsyncClient) -> None:
    """A JSON source with neither data nor url is refused with the reason."""
    payload = _make_json_source(config={"not_data": "value"})
    resp = await client.post("/api/v1/data-sources", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_register_source_with_a_city_the_site_does_not_know(
    client: AsyncClient,
) -> None:
    """The answer names the city, so the operator knows what to correct."""
    payload = _make_register_source(config={"city": "Atlantis"})
    resp = await client.post("/api/v1/data-sources", json=payload)

    assert resp.status_code == 422
    assert "Atlantis" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_file_upload_source_missing_filename(client: AsyncClient) -> None:
    """A file source with no filename in its config is refused with the reason."""
    payload = _make_file_source(config={"not_filename": "value"})
    resp = await client.post("/api/v1/data-sources", json=payload)
    assert resp.status_code == 422


# ===========================================================================
# Tests: get_data_source (GET /data-sources/{source_id})
# ===========================================================================


@pytest.mark.asyncio
async def test_get_data_source_found(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Get an existing data source by ID."""
    resp = await client.get(f"/api/v1/data-sources/{sample_data_source.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sample_data_source.id
    assert body["name"] == "Test CSV Source"
    assert body["source_type"] == "file_upload"


@pytest.mark.asyncio
async def test_get_data_source_not_found(client: AsyncClient) -> None:
    """Get returns 404 for non-existent data source."""
    resp = await client.get("/api/v1/data-sources/nonexistent-id")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


# ===========================================================================
# Tests: update_data_source (PATCH /data-sources/{source_id})
# ===========================================================================


@pytest.mark.asyncio
async def test_update_data_source_name(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Update the name of a data source."""
    resp = await client.patch(
        f"/api/v1/data-sources/{sample_data_source.id}",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_data_source_config(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Update the config of a file_upload source."""
    new_config = {"filename": "new_data.xlsx", "size_bytes": 2048}
    resp = await client.patch(
        f"/api/v1/data-sources/{sample_data_source.id}",
        json={"config": new_config},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["config"]["filename"] == "new_data.xlsx"


@pytest.mark.asyncio
async def test_update_data_source_config_url_validation(
    client: AsyncClient,
    sample_active_source: DataSourceDB,
) -> None:
    """An update with a url that is not a url is refused with the reason."""
    resp = await client.patch(
        f"/api/v1/data-sources/{sample_active_source.id}",
        json={"config": {"url": "not-a-valid-url"}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_data_source_config_valid_for_existing_type(
    client: AsyncClient,
    sample_active_source: DataSourceDB,
) -> None:
    """Update config while keeping existing source_type.

    DataSourceUpdate does not allow changing source_type.
    The new config must be valid for the existing source_type (url).
    """
    resp = await client.patch(
        f"/api/v1/data-sources/{sample_active_source.id}",
        json={
            "config": {"url": "https://example.com/updated-data.csv"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["config"]["url"] == "https://example.com/updated-data.csv"
    assert body["source_type"] == "url"


@pytest.mark.asyncio
async def test_update_data_source_auto_sync(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Update auto_sync_enabled and sync_schedule."""
    resp = await client.patch(
        f"/api/v1/data-sources/{sample_data_source.id}",
        json={"auto_sync_enabled": True, "sync_schedule": "0 */6 * * *"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["auto_sync_enabled"] is True
    assert body["sync_schedule"] == "0 */6 * * *"


@pytest.mark.asyncio
async def test_update_data_source_not_found(client: AsyncClient) -> None:
    """Update returns 404 for non-existent data source."""
    resp = await client.patch(
        "/api/v1/data-sources/nonexistent-id",
        json={"name": "New Name"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_data_source_status(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Update the status field of a data source."""
    resp = await client.patch(
        f"/api/v1/data-sources/{sample_data_source.id}",
        json={"status": "disabled"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


# ===========================================================================
# Tests: delete_data_source (DELETE /data-sources/{source_id})
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_data_source_without_confirm(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Delete without confirm=true returns 400."""
    resp = await client.delete(f"/api/v1/data-sources/{sample_data_source.id}")
    assert resp.status_code == 400
    assert "confirm=true" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_data_source_with_confirm(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Delete with confirm=true returns 204 and source is gone."""
    # Create a fresh source for this test
    ds = DataSourceDB(
        id="ds-del-001",
        name="To Delete",
        source_type="file_upload",
        config={"filename": "delete.csv"},
        status="pending",
    )
    db_session.add(ds)
    await db_session.flush()

    resp = await client.delete(
        "/api/v1/data-sources/ds-del-001",
        params={"confirm": "true"},
    )
    assert resp.status_code == 204

    # Need to commit to see changes in a new query
    await db_session.commit()

    resp2 = await client.get("/api/v1/data-sources/ds-del-001")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_data_source_not_found(client: AsyncClient) -> None:
    """Delete returns 404 for non-existent data source."""
    resp = await client.delete(
        "/api/v1/data-sources/nonexistent-id",
        params={"confirm": "true"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_data_source_cascades_history(
    client: AsyncClient,
    sample_source_with_history: DataSourceDB,
    db_session: AsyncSession,
) -> None:
    """Deleting a data source removes its sync history."""
    resp = await client.delete(
        f"/api/v1/data-sources/{sample_source_with_history.id}",
        params={"confirm": "true"},
    )
    assert resp.status_code == 204

    await db_session.commit()

    from sqlalchemy import func, select

    count_result = await db_session.execute(
        select(func.count()).where(
            DataSourceSyncHistory.data_source_id == sample_source_with_history.id
        )
    )
    assert count_result.scalar() == 0


# ===========================================================================
# Tests: sync_data_source (POST /data-sources/{source_id}/sync)
# ===========================================================================


@pytest.mark.asyncio
async def test_sync_data_source_not_found(client: AsyncClient) -> None:
    """Sync returns 404 for non-existent data source."""
    resp = await client.post("/api/v1/data-sources/nonexistent-id/sync")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sync_data_source_already_syncing(
    client: AsyncClient,
    sample_syncing_source: DataSourceDB,
) -> None:
    """Sync returns 409 when source is already syncing."""
    resp = await client.post(f"/api/v1/data-sources/{sample_syncing_source.id}/sync")
    assert resp.status_code == 409
    assert "already syncing" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_sync_data_source_triggers_successfully(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Sync triggers successfully for a pending source."""
    with patch("api.dependencies.get_vector_store") as mock_vs:
        with patch("asyncio.create_task"):
            mock_vs.return_value = MagicMock()
            resp = await client.post(f"/api/v1/data-sources/{sample_data_source.id}/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert body["source_id"] == sample_data_source.id
    assert body["status"] == "syncing"
    assert body["message"] == "Sync triggered successfully"
    assert body["records_processed"] == 0
    assert body["started_at"] is not None


# ===========================================================================
# Tests: test_data_source (POST /data-sources/test)
# ===========================================================================


@pytest.mark.asyncio
async def test_test_file_upload_source(client: AsyncClient) -> None:
    """Test endpoint validates file_upload config as valid."""
    resp = await client.post(
        "/api/v1/data-sources/test",
        json={"source_type": "file_upload", "config": {"filename": "test.csv"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "valid" in body["message"].lower()


@pytest.mark.asyncio
async def test_test_url_source_with_mocked_httpx(client: AsyncClient) -> None:
    """Test URL source with mocked httpx client."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/csv"}

    mock_client_instance = AsyncMock()
    mock_client_instance.head = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        with patch(
            "utils.web_fetch._hostname_resolves_to_public_ip",
            return_value=True,
        ):
            resp = await client.post(
                "/api/v1/data-sources/test",
                json={
                    "source_type": "url",
                    "config": {"url": "https://example.com/data.csv"},
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["details"]["status_code"] == 200


@pytest.mark.asyncio
async def test_test_url_source_http_error(client: AsyncClient) -> None:
    """Test URL source returns failure on HTTP error."""
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 403

    mock_client_instance = AsyncMock()
    mock_client_instance.head = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Forbidden",
            request=MagicMock(),
            response=mock_response,
        )
    )
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        with patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True):
            resp = await client.post(
                "/api/v1/data-sources/test",
                json={
                    "source_type": "url",
                    "config": {"url": "https://example.com/forbidden"},
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "403" in body["message"]


@pytest.mark.asyncio
async def test_test_url_source_connection_error(client: AsyncClient) -> None:
    """Test URL source returns failure on connection error."""
    import httpx

    mock_client_instance = AsyncMock()
    mock_client_instance.head = AsyncMock(side_effect=httpx.RequestError("Connection refused"))
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        with patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True):
            resp = await client.post(
                "/api/v1/data-sources/test",
                json={
                    "source_type": "url",
                    "config": {"url": "https://unreachable.example.com"},
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "Connection error" in body["message"]


@pytest.mark.asyncio
async def test_test_json_source_with_inline_data(client: AsyncClient) -> None:
    """Test JSON source with inline data is valid."""
    resp = await client.post(
        "/api/v1/data-sources/test",
        json={
            "source_type": "json",
            "config": {"data": [{"id": 1, "name": "test"}]},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["details"]["type"] == "inline"
    assert body["details"]["structure"] == "list"


@pytest.mark.asyncio
async def test_test_json_source_with_dict_data(client: AsyncClient) -> None:
    """Test JSON source with dict data is valid."""
    resp = await client.post(
        "/api/v1/data-sources/test",
        json={
            "source_type": "json",
            "config": {"data": {"key": "value"}},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["details"]["structure"] == "dict"


@pytest.mark.asyncio
async def test_test_json_source_with_string_data(client: AsyncClient) -> None:
    """Test JSON source with valid JSON string data."""
    resp = await client.post(
        "/api/v1/data-sources/test",
        json={
            "source_type": "json",
            "config": {"data": '{"valid": "json"}'},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_test_json_source_with_invalid_json_string(client: AsyncClient) -> None:
    """Test JSON source with invalid JSON string returns failure."""
    resp = await client.post(
        "/api/v1/data-sources/test",
        json={
            "source_type": "json",
            "config": {"data": "not-valid-json{{{}}}"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "Invalid JSON" in body["message"]


@pytest.mark.asyncio
async def test_test_json_source_with_invalid_data_type(client: AsyncClient) -> None:
    """Test JSON source with non-object/array/string data type fails."""
    resp = await client.post(
        "/api/v1/data-sources/test",
        json={
            "source_type": "json",
            "config": {"data": 42},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "must be a JSON object or array" in body["message"]


@pytest.mark.asyncio
async def test_test_json_source_with_url(client: AsyncClient) -> None:
    """Test JSON source delegates to URL test when url is provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}

    mock_client_instance = AsyncMock()
    mock_client_instance.head = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        with patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True):
            resp = await client.post(
                "/api/v1/data-sources/test",
                json={
                    "source_type": "json",
                    "config": {"url": "https://example.com/data.json"},
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_test_json_source_no_data_no_url(client: AsyncClient) -> None:
    """Test JSON source catches ValueError when no data or url in config."""
    resp = await client.post(
        "/api/v1/data-sources/test",
        json={
            "source_type": "json",
            "config": {"other_field": "value"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "requires" in body["message"].lower()


@pytest.mark.asyncio
async def test_test_portal_source_unknown_portal_via_endpoint(client: AsyncClient) -> None:
    """Test portal source with unknown portal via endpoint."""
    with patch("data.adapters.registry.AdapterRegistry.list_adapters", return_value=["otodom"]):
        with patch("data.adapters.list_adapters", return_value=["otodom"], create=True):
            resp = await client.post(
                "/api/v1/data-sources/test",
                json={
                    "source_type": "portal_api",
                    "config": {"portal": "nonexistent_portal"},
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_test_source_validation_error(client: AsyncClient) -> None:
    """Test endpoint catches ValueError from config validation."""
    resp = await client.post(
        "/api/v1/data-sources/test",
        json={
            "source_type": "url",
            "config": {},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "requires" in body["message"].lower()


# ===========================================================================
# Tests: get_sync_history (GET /data-sources/{source_id}/history)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_sync_history_not_found(client: AsyncClient) -> None:
    """Sync history returns 404 for non-existent data source."""
    resp = await client.get("/api/v1/data-sources/nonexistent-id/history")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_sync_history_empty(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Sync history returns empty list when no history exists."""
    resp = await client.get(f"/api/v1/data-sources/{sample_data_source.id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source_id"] == sample_data_source.id
    assert body["total"] == 0
    assert body["history"] == []


@pytest.mark.asyncio
async def test_get_sync_history_with_data(
    client: AsyncClient,
    sample_source_with_history: DataSourceDB,
) -> None:
    """Sync history returns entries ordered by started_at desc."""
    resp = await client.get(f"/api/v1/data-sources/{sample_source_with_history.id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["history"]) == 3
    # Most recent first
    assert body["history"][0]["status"] in ("success", "failed")
    assert body["history"][0]["records_processed"] > 0


@pytest.mark.asyncio
async def test_get_sync_history_pagination(
    client: AsyncClient,
    sample_source_with_history: DataSourceDB,
) -> None:
    """Paginate sync history results."""
    resp = await client.get(
        f"/api/v1/data-sources/{sample_source_with_history.id}/history",
        params={"page": 1, "page_size": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["history"]) == 2


@pytest.mark.asyncio
async def test_get_sync_history_item_fields(
    client: AsyncClient,
    sample_source_with_history: DataSourceDB,
) -> None:
    """Verify all expected fields are present in history items."""
    resp = await client.get(f"/api/v1/data-sources/{sample_source_with_history.id}/history")
    assert resp.status_code == 200
    body = resp.json()
    item = body["history"][0]
    expected_keys = {
        "id",
        "started_at",
        "completed_at",
        "status",
        "records_processed",
        "records_added",
        "records_updated",
        "records_skipped",
        "error_message",
    }
    assert set(item.keys()) == expected_keys


# ===========================================================================
# Tests: _validate_config helper (direct)
# ===========================================================================


def test_validate_config_url_valid() -> None:
    """Valid URL config passes validation."""
    _validate_config("url", {"url": "https://example.com/data.csv"})


def test_validate_config_url_missing() -> None:
    """URL config without url raises ValueError."""
    with pytest.raises(ValueError, match="requires 'url'"):
        _validate_config("url", {"not_url": "value"})


def test_validate_config_url_invalid_scheme() -> None:
    """URL with invalid scheme raises ValueError."""
    with pytest.raises(ValueError, match="must start with http"):
        _validate_config("url", {"url": "ftp://example.com"})


def test_validate_config_portal_valid() -> None:
    """Valid portal config passes validation."""
    _validate_config("portal_api", {"portal": "otodom"})


def test_validate_config_portal_missing() -> None:
    """Portal config without portal raises ValueError."""
    with pytest.raises(ValueError, match="requires 'portal'"):
        _validate_config("portal_api", {"not_portal": "value"})


def test_validate_config_json_with_data() -> None:
    """JSON config with data passes validation."""
    _validate_config("json", {"data": [{"id": 1}]})


def test_validate_config_json_with_url() -> None:
    """JSON config with url passes validation."""
    _validate_config("json", {"url": "https://example.com/data.json"})


def test_validate_config_json_missing_both() -> None:
    """JSON config without data or url raises ValueError."""
    with pytest.raises(ValueError, match="requires 'data' or 'url'"):
        _validate_config("json", {"other": "value"})


def test_validate_config_file_upload_valid() -> None:
    """File upload config with filename passes validation."""
    _validate_config("file_upload", {"filename": "data.csv"})


def test_validate_config_file_upload_missing() -> None:
    """File upload config without filename raises ValueError."""
    with pytest.raises(ValueError, match="requires 'filename'"):
        _validate_config("file_upload", {"not_filename": "value"})


def test_validate_config_unknown_type() -> None:
    """Unknown source type passes validation (no checks)."""
    _validate_config("unknown_type", {})


# ===========================================================================
# Tests: _recalculate_health_score helper (direct)
# ===========================================================================


def test_health_score_zero_failures_success() -> None:
    """Health score 100 for success with no failures."""
    ds = MagicMock()
    ds.consecutive_failures = 0
    ds.last_sync_status = "success"
    ds.status = "active"
    assert _recalculate_health_score(ds) == 100.0


def test_health_score_zero_failures_partial() -> None:
    """Health score 75 for partial sync with no failures."""
    ds = MagicMock()
    ds.consecutive_failures = 0
    ds.last_sync_status = "partial"
    ds.status = "active"
    assert _recalculate_health_score(ds) == 75.0


def test_health_score_zero_failures_pending() -> None:
    """Health score 0 for pending status."""
    ds = MagicMock()
    ds.consecutive_failures = 0
    ds.last_sync_status = None
    ds.status = "pending"
    assert _recalculate_health_score(ds) == 0.0


def test_health_score_zero_failures_other_status() -> None:
    """Health score 50 for unknown status."""
    ds = MagicMock()
    ds.consecutive_failures = 0
    ds.last_sync_status = None
    ds.status = "error"
    assert _recalculate_health_score(ds) == 50.0


def test_health_score_one_failure() -> None:
    """Health score 50 for one consecutive failure."""
    ds = MagicMock()
    ds.consecutive_failures = 1
    assert _recalculate_health_score(ds) == 50.0


def test_health_score_two_failures() -> None:
    """Health score 25 for two consecutive failures."""
    ds = MagicMock()
    ds.consecutive_failures = 2
    assert _recalculate_health_score(ds) == 25.0


def test_health_score_three_failures() -> None:
    """Health score 0 for three or more consecutive failures."""
    ds = MagicMock()
    ds.consecutive_failures = 3
    assert _recalculate_health_score(ds) == 0.0


def test_health_score_many_failures() -> None:
    """Health score 0 for many consecutive failures."""
    ds = MagicMock()
    ds.consecutive_failures = 10
    assert _recalculate_health_score(ds) == 0.0


# ===========================================================================
# Tests: _validate_url_no_ssrf helper (direct)
# ===========================================================================


def test_validate_url_no_ssrf_valid() -> None:
    """Valid public URL passes SSRF check."""
    with patch(
        "utils.web_fetch._hostname_resolves_to_public_ip",
        return_value=True,
    ):
        _validate_url_no_ssrf("https://example.com/data")


def test_validate_url_no_ssrf_invalid_scheme() -> None:
    """Non-http(s) scheme fails SSRF check."""
    with pytest.raises(ValueError, match="Only http and https"):
        _validate_url_no_ssrf("ftp://example.com/data")


def test_validate_url_no_ssrf_no_hostname() -> None:
    """URL without hostname fails SSRF check."""
    with pytest.raises(ValueError, match="no hostname"):
        _validate_url_no_ssrf("http://")


def test_validate_url_no_ssrf_private_ip() -> None:
    """URL resolving to private IP fails SSRF check."""
    with patch(
        "utils.web_fetch._hostname_resolves_to_public_ip",
        return_value=False,
    ):
        with pytest.raises(ValueError, match="private/internal"):
            _validate_url_no_ssrf("http://192.168.1.1/secret")


# ===========================================================================
# Tests: _test_portal_source helper (direct function tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_portal_source_unknown_portal() -> None:
    """Test portal source with unknown portal name."""
    mock_list_adapters = MagicMock(return_value=["otodom"])

    with patch("data.adapters.list_adapters", mock_list_adapters, create=True):
        with patch("data.adapters.registry.AdapterRegistry.list_adapters", mock_list_adapters):
            result = await data_sources._test_portal_source({"portal": "unknown"})

    assert result.success is False
    assert "Unknown portal" in result.message
    assert result.details is not None
    assert "available_portals" in result.details


@pytest.mark.asyncio
async def test_portal_source_adapter_not_found() -> None:
    """Test portal source when adapter class is not found."""
    mock_list_adapters = MagicMock(return_value=["otodom"])

    with (
        patch("data.adapters.list_adapters", mock_list_adapters, create=True),
        patch("data.adapters.registry.AdapterRegistry") as mock_registry,
    ):
        mock_registry.get_adapter.return_value = None
        mock_registry.list_adapters = mock_list_adapters
        result = await data_sources._test_portal_source({"portal": "otodom"})

    assert result.success is False
    assert "Adapter not found" in result.message


@pytest.mark.asyncio
async def test_portal_source_health_check_pass() -> None:
    """Test portal source when health check passes."""
    mock_adapter_instance = AsyncMock()
    mock_adapter_instance.health_check = AsyncMock(return_value=True)

    mock_list_adapters = MagicMock(return_value=["otodom"])

    with (
        patch("data.adapters.registry.AdapterRegistry") as mock_registry,
    ):
        # The registry answers with the adapter itself.
        mock_registry.get_adapter.return_value = mock_adapter_instance
        mock_registry.list_adapters = mock_list_adapters
        result = await data_sources._test_portal_source({"portal": "otodom", "api_key": "test-key"})

    assert result.success is True
    assert "connection successful" in result.message
    mock_registry.get_adapter.assert_called_once_with("otodom", api_key="test-key")


@pytest.mark.asyncio
async def test_portal_source_health_check_fail() -> None:
    """Test portal source when health check fails."""
    mock_adapter_instance = AsyncMock()
    mock_adapter_instance.health_check = AsyncMock(return_value=False)

    mock_list_adapters = MagicMock(return_value=["otodom"])

    with (
        patch("data.adapters.registry.AdapterRegistry") as mock_registry,
    ):
        mock_registry.get_adapter.return_value = mock_adapter_instance
        mock_registry.list_adapters = mock_list_adapters
        result = await data_sources._test_portal_source({"portal": "otodom"})

    assert result.success is False
    assert "health check failed" in result.message


@pytest.mark.asyncio
async def test_portal_source_no_health_check_method() -> None:
    """Test portal source when adapter has no health_check method."""
    mock_adapter_instance = MagicMock(spec=[])  # No health_check attribute

    mock_list_adapters = MagicMock(return_value=["otodom"])

    with (
        patch("data.adapters.registry.AdapterRegistry") as mock_registry,
    ):
        mock_registry.get_adapter.return_value = mock_adapter_instance
        mock_registry.list_adapters = mock_list_adapters
        result = await data_sources._test_portal_source({"portal": "otodom"})

    assert result.success is True
    assert "no health check method" in result.message


@pytest.mark.asyncio
async def test_portal_source_exception() -> None:
    """Test portal source handles adapter exceptions."""
    mock_adapter_cls = MagicMock(side_effect=RuntimeError("Initialization failed"))
    mock_list_adapters = MagicMock(return_value=["otodom"])

    with (
        patch("data.adapters.list_adapters", mock_list_adapters, create=True),
        patch("data.adapters.registry.AdapterRegistry") as mock_registry,
    ):
        mock_registry.get_adapter.return_value = mock_adapter_cls
        mock_registry.list_adapters = mock_list_adapters
        result = await data_sources._test_portal_source({"portal": "otodom"})

    assert result.success is False
    assert "Error testing portal" in result.message


# ===========================================================================
# Tests: _test_url_source helper (direct function tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_url_source_accessible() -> None:
    """Test URL source when URL is accessible."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/csv"}

    mock_client = AsyncMock()
    mock_client.head = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True),
    ):
        result = await data_sources._test_url_source({"url": "https://example.com/data.csv"})

    assert result.success is True
    assert result.details is not None
    assert result.details["status_code"] == 200


@pytest.mark.asyncio
async def test_url_source_http_error() -> None:
    """Test URL source when HTTP error occurs."""
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_client = AsyncMock()
    mock_client.head = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True),
    ):
        result = await data_sources._test_url_source({"url": "https://example.com/error"})

    assert result.success is False
    assert result.details is not None
    assert result.details["status_code"] == 500


@pytest.mark.asyncio
async def test_url_source_connection_error() -> None:
    """Test URL source when connection error occurs."""
    import httpx

    mock_client = AsyncMock()
    mock_client.head = AsyncMock(side_effect=httpx.RequestError("Timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True),
    ):
        result = await data_sources._test_url_source({"url": "https://unreachable.example.com"})

    assert result.success is False
    assert "Connection error" in result.message
    assert result.details is None


# ===========================================================================
# Tests: _test_json_source helper (direct function tests)
# ===========================================================================


@pytest.mark.asyncio
async def test_json_source_with_list_data() -> None:
    """Test JSON source with list data."""
    result = await data_sources._test_json_source({"data": [{"id": 1}, {"id": 2}]})
    assert result.success is True
    assert result.details is not None
    assert result.details["structure"] == "list"


@pytest.mark.asyncio
async def test_json_source_with_dict_data() -> None:
    """Test JSON source with dict data."""
    result = await data_sources._test_json_source({"data": {"key": "value"}})
    assert result.success is True
    assert result.details is not None
    assert result.details["structure"] == "dict"


@pytest.mark.asyncio
async def test_json_source_with_string_data_valid() -> None:
    """Test JSON source with valid JSON string."""
    result = await data_sources._test_json_source({"data": '{"valid": true}'})
    assert result.success is True


@pytest.mark.asyncio
async def test_json_source_with_string_data_invalid() -> None:
    """Test JSON source with invalid JSON string."""
    result = await data_sources._test_json_source({"data": "not-json{{{}}}"})
    assert result.success is False
    assert "Invalid JSON" in result.message


@pytest.mark.asyncio
async def test_json_source_with_non_object_data() -> None:
    """Test JSON source with non-object/array data type raises ValueError."""
    with pytest.raises(ValueError, match="must be a JSON object or array"):
        await data_sources._test_json_source({"data": 123.45})


@pytest.mark.asyncio
async def test_json_source_with_url_delegation() -> None:
    """Test JSON source delegates to URL test when url is provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}

    mock_client = AsyncMock()
    mock_client.head = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("utils.web_fetch._hostname_resolves_to_public_ip", return_value=True),
    ):
        result = await data_sources._test_json_source({"url": "https://example.com/data.json"})

    assert result.success is True


@pytest.mark.asyncio
async def test_json_source_no_data_no_url() -> None:
    """Test JSON source with neither data nor url returns failure."""
    result = await data_sources._test_json_source({"other": "value"})
    assert result.success is False
    assert "No data or URL" in result.message


# ===========================================================================
# Tests: edge cases
# ===========================================================================


@pytest.mark.asyncio
async def test_list_data_sources_default_pagination(
    client: AsyncClient,
) -> None:
    """Default pagination values are page=1, page_size=20."""
    resp = await client.get("/api/v1/data-sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 20


@pytest.mark.asyncio
async def test_create_and_get_roundtrip(client: AsyncClient) -> None:
    """Create a source and retrieve it by ID."""
    create_resp = await client.post(
        "/api/v1/data-sources",
        json=_make_file_source(),
    )
    assert create_resp.status_code == 201
    source_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/data-sources/{source_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == source_id
    assert get_resp.json()["name"] == "Test File Source"


@pytest.mark.asyncio
async def test_update_preserves_unmodified_fields(
    client: AsyncClient,
    sample_data_source: DataSourceDB,
) -> None:
    """Updating name does not change other fields."""
    original = (await client.get(f"/api/v1/data-sources/{sample_data_source.id}")).json()

    resp = await client.patch(
        f"/api/v1/data-sources/{sample_data_source.id}",
        json={"name": "Only Name Changed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Only Name Changed"
    assert body["source_type"] == original["source_type"]
    assert body["config"] == original["config"]


# ---------------------------------------------------------------------------
# The suffix a downloaded document is read under
# ---------------------------------------------------------------------------


def test_the_url_suffix_wins_over_the_content_type() -> None:
    """A url that ends in .csv is a csv document, whatever the server says."""
    assert (
        data_sources._suffix_for("https://example.com/listings.csv", "application/json") == ".csv"
    )


def test_the_content_type_answers_when_the_url_says_nothing() -> None:
    """A url without a suffix is read under the format the server names."""
    assert data_sources._suffix_for("https://example.com/listings", "text/csv") == ".csv"
    assert data_sources._suffix_for("https://example.com/listings", "application/json") == ".json"


def test_a_content_type_that_names_no_format_says_nothing() -> None:
    """A guess would hand an .xls to the loader under the suffix of another format."""
    assert data_sources._format_suffix("application/vnd.ms-excel") == ".xls"
    assert data_sources._format_suffix("application/octet-stream") == ""
    assert data_sources._format_suffix("text/plain; charset=utf-8") == ""
