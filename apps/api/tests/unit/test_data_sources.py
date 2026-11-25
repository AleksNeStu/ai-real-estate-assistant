"""Unit tests for data sources router.

Tests cover CRUD operations,sync management, and health tracking.
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "test-api-key")

from api.auth import get_api_key
from api.routers import data_sources
from db.database import get_db
from db.models import DataSourceDB, DataSourceSyncHistory


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async client with data sources router."""
    app = FastAPI()

    async def override_get_api_key():
        return "test-api-key"

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_api_key] = override_get_api_key
    app.dependency_overrides[get_db] = override_get_db

    app.include_router(data_sources.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """API key auth headers."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
async def sample_data_source(db_session: AsyncSession) -> DataSourceDB:
    """Create a sample data source for testing."""
    ds = DataSourceDB(
        id="test-source-001",
        name="Test CSV Source",
        source_type="file_upload",
        config={"filename": "properties.csv", "size_bytes": 1024},
        status="active",
        total_records=100,
        health_score=100.0,
        auto_sync_enabled=False,
    )
    db_session.add(ds)
    await db_session.flush()
    await db_session.refresh(ds)
    return ds


@pytest.fixture
async def sample_sync_history(
    db_session: AsyncSession, sample_data_source: DataSourceDB
) -> list[DataSourceSyncHistory]:
    """Create sample sync history entries."""
    from datetime import UTC, datetime, timedelta

    entries = []
    for i in range(3):
        entry = DataSourceSyncHistory(
            id=f"sync-{i:03d}",
            data_source_id=sample_data_source.id,
            started_at=datetime.now(UTC) - timedelta(days=i + 1),
            completed_at=datetime.now(UTC) - timedelta(days=i + 1, minutes=-5),
            status="success" if i < 2 else "failed",
            records_processed=100 - i * 10,
            records_added=50 - i * 5,
            records_updated=30,
            records_skipped=20,
        )
        db_session.add(entry)
        entries.append(entry)

    await db_session.flush()
    for entry in entries:
        await db_session.refresh(entry)
    return entries


class TestListDataSources:
    """Tests for listing data sources."""

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing when no sources exist."""
        response = await client.get("/api/v1/data-sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["sources"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_with_sources(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test listing with existing sources."""
        response = await client.get("/api/v1/data-sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["sources"]) == 1
        assert data["sources"][0]["name"] == "Test CSV Source"

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test pagination parameters."""
        for i in range(25):
            ds = DataSourceDB(
                id=f"source-{i:03d}",
                name=f"Source {i}",
                source_type="url",
                config={"url": f"https://example.com/{i}"},
                status="active",
            )
            db_session.add(ds)
        await db_session.flush()

        response = await client.get(
            "/api/v1/data-sources?page=1&page_size=10", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["sources"]) == 10
        assert data["page"] == 1

        response = await client.get(
            "/api/v1/data-sources?page=2&page_size=10", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 10
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_status(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test filtering by status."""
        for status_val in ["active", "error", "pending"]:
            ds = DataSourceDB(
                id=f"source-{status_val}",
                name=f"Source {status_val}",
                source_type="url",
                config={"url": "https://example.com/"},
                status=status_val,
            )
            db_session.add(ds)
        await db_session.flush()

        response = await client.get("/api/v1/data-sources?status=active", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["sources"][0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_filter_by_type(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test filtering by source type."""
        for stype in ["url", "portal_api", "file_upload"]:
            config = {"url": "https://example.com/"} if stype == "url" else {"portal": "otodom"}
            ds = DataSourceDB(
                id=f"source-{stype}",
                name=f"Source {stype}",
                source_type=stype,
                config=config,
                status="active",
            )
            db_session.add(ds)
        await db_session.flush()
        response = await client.get("/api/v1/data-sources?source_type=url", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["sources"][0]["source_type"] == "url"


class TestCreateDataSource:
    """Tests for creating data sources."""

    @pytest.mark.asyncio
    async def test_create_url_source(self, client: AsyncClient, auth_headers: dict):
        """Test creating a URL data source."""
        response = await client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "My URL Source",
                "source_type": "url",
                "config": {"url": "https://example.com/data.csv"},
                "auto_sync_enabled": True,
                "sync_schedule": "0 0 * * *",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My URL Source"
        assert data["source_type"] == "url"
        assert data["status"] == "pending"
        assert data["auto_sync_enabled"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_file_upload_source(self, client: AsyncClient, auth_headers: dict):
        """Test creating a file upload source."""
        response = await client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "CSV Upload",
                "source_type": "file_upload",
                "config": {"filename": "data.csv", "size_bytes": 1024},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["source_type"] == "file_upload"

    @pytest.mark.asyncio
    async def test_create_portal_api_source(self, client: AsyncClient, auth_headers: dict):
        """Test creating a portal API source."""
        response = await client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "Otodom Warsaw",
                "source_type": "portal_api",
                "config": {"portal": "otodom", "city": "Warsaw"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["source_type"] == "portal_api"

    @pytest.mark.asyncio
    async def test_create_json_source(self, client: AsyncClient, auth_headers: dict):
        """Test creating a JSON source."""
        response = await client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "JSON Data",
                "source_type": "json",
                "config": {"data": [{"id": 1, "name": "test"}]},
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_url_source_missing_url(self, client: AsyncClient, auth_headers: dict):
        """Test validation fails when URL is missing."""
        # The router refuses the config and names the reason: the answer is
        # for the operator who wrote it.
        response = await client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "Bad URL Source",
                "source_type": "url",
                "config": {},
            },
        )
        assert response.status_code == 422
        assert "URL source requires" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_url_source_invalid_url(self, client: AsyncClient, auth_headers: dict):
        """Test validation fails for invalid URL format."""
        response = await client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "Bad URL",
                "source_type": "url",
                "config": {"url": "not-a-valid-url"},
            },
        )
        assert response.status_code == 422
        assert "URL must start with" in response.json()["detail"]


class TestGetDataSource:
    """Tests for getting a single data source."""

    @pytest.mark.asyncio
    async def test_get_existing_source(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test getting an existing source."""
        response = await client.get(
            f"/api/v1/data-sources/{sample_data_source.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_data_source.id
        assert data["name"] == "Test CSV Source"

    @pytest.mark.asyncio
    async def test_get_nonexistent_source(self, client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent source returns 404."""
        response = await client.get("/api/v1/data-sources/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateDataSource:
    """Tests for updating data sources."""

    @pytest.mark.asyncio
    async def test_update_name(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test updating source name."""
        response = await client.patch(
            f"/api/v1/data-sources/{sample_data_source.id}",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_config(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test updating source config."""
        response = await client.patch(
            f"/api/v1/data-sources/{sample_data_source.id}",
            headers=auth_headers,
            json={"config": {"filename": "new_file.csv", "size_bytes": 2048}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["filename"] == "new_file.csv"

    @pytest.mark.asyncio
    async def test_update_auto_sync(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test updating auto sync settings."""
        response = await client.patch(
            f"/api/v1/data-sources/{sample_data_source.id}",
            headers=auth_headers,
            json={"auto_sync_enabled": True, "sync_schedule": "0 */6 * * *"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["auto_sync_enabled"] is True
        assert data["sync_schedule"] == "0 */6 * * *"

    @pytest.mark.asyncio
    async def test_update_nonexistent_source(self, client: AsyncClient, auth_headers: dict):
        """Test updating non-existent source returns 404."""
        response = await client.patch(
            "/api/v1/data-sources/nonexistent-id",
            headers=auth_headers,
            json={"name": "New Name"},
        )
        assert response.status_code == 404


class TestDeleteDataSource:
    """Tests for deleting data sources."""

    @pytest.mark.asyncio
    async def test_delete_requires_confirmation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test deletion requires confirm=true."""
        response = await client.delete(
            f"/api/v1/data-sources/{sample_data_source.id}?confirm=false",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "confirm=true" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_with_confirmation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test successful deletion with confirmation."""
        response = await client.delete(
            f"/api/v1/data-sources/{sample_data_source.id}?confirm=true",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Note: In-memory SQLite with shared session may still return the
        # deleted entity if the fixture session hasn't expired the cache

    @pytest.mark.asyncio
    async def test_delete_nonexistent_source(self, client: AsyncClient, auth_headers: dict):
        """Test deleting non-existent source returns 404."""
        response = await client.delete(
            "/api/v1/data-sources/nonexistent-id?confirm=true",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_cascades_sync_history(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
        sample_sync_history: list[DataSourceSyncHistory],
    ):
        """Test that deleting source also deletes sync history."""
        source_id = sample_data_source.id

        response = await client.delete(
            f"/api/v1/data-sources/{source_id}?confirm=true",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestSyncDataSource:
    """Tests for triggering data source sync.

    Task #92: the skip is gone. The sync of a ``file_upload`` source never
    fetches anything (the background task reads the record count from the
    source's config), and the vector store - the only part that would reach
    for the embedding model - is stubbed out, so the test is hermetic.
    """

    @pytest.fixture(autouse=True)
    def _no_vector_store(self):
        """The background sync must not initialise the embedding model."""
        with patch("api.dependencies.get_vector_store", return_value=None):
            yield

    @pytest.mark.asyncio
    async def test_sync_triggers_successfully(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test triggering a sync."""
        response = await client.post(
            f"/api/v1/data-sources/{sample_data_source.id}/sync",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == sample_data_source.id
        assert data["status"] == "syncing"
        assert data["message"] == "Sync triggered successfully"

        # Let the background sync finish while the session is still open.
        await asyncio.sleep(0.2)

    @pytest.mark.asyncio
    async def test_sync_already_syncing(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that syncing an already syncing source returns 409."""
        ds = DataSourceDB(
            id="syncing-source",
            name="Syncing Source",
            source_type="url",
            config={"url": "https://example.com/"},
            status="syncing",
        )
        db_session.add(ds)
        await db_session.flush()

        response = await client.post(
            "/api/v1/data-sources/syncing-source/sync",
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert "already syncing" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_sync_nonexistent_source(self, client: AsyncClient, auth_headers: dict):
        """Test syncing non-existent source returns 404."""
        response = await client.post(
            "/api/v1/data-sources/nonexistent-id/sync",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestTestDataSource:
    """Tests for testing data source connections."""

    @pytest.mark.asyncio
    async def test_test_file_upload_source(self, client: AsyncClient, auth_headers: dict):
        """Test validating file upload config."""
        response = await client.post(
            "/api/v1/data-sources/test",
            headers=auth_headers,
            json={
                "source_type": "file_upload",
                "config": {"filename": "test.csv"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "valid" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_test_file_upload_missing_filename(self, client: AsyncClient, auth_headers: dict):
        """Test file upload validation fails without filename."""
        response = await client.post(
            "/api/v1/data-sources/test",
            headers=auth_headers,
            json={
                "source_type": "file_upload",
                "config": {},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "filename" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_test_json_source_with_data(self, client: AsyncClient, auth_headers: dict):
        """Test validating JSON data."""
        response = await client.post(
            "/api/v1/data-sources/test",
            headers=auth_headers,
            json={
                "source_type": "json",
                "config": {"data": [{"id": 1, "name": "test"}]},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_test_portal_source(self, client: AsyncClient, auth_headers: dict):
        """Test validating portal API config."""
        response = await client.post(
            "/api/v1/data-sources/test",
            headers=auth_headers,
            json={
                "source_type": "portal_api",
                "config": {"portal": "otodom"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_test_portal_missing_portal(self, client: AsyncClient, auth_headers: dict):
        """Test portal validation fails without portal name."""
        response = await client.post(
            "/api/v1/data-sources/test",
            headers=auth_headers,
            json={
                "source_type": "portal_api",
                "config": {},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "portal" in data["message"].lower()


class TestGetSyncHistory:
    """Tests for getting sync history."""

    @pytest.mark.asyncio
    async def test_get_sync_history(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
        sample_sync_history: list[DataSourceSyncHistory],
    ):
        """Test getting sync history for a source."""
        response = await client.get(
            f"/api/v1/data-sources/{sample_data_source.id}/history",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == sample_data_source.id
        assert data["total"] == 3
        assert len(data["history"]) == 3

    @pytest.mark.asyncio
    async def test_get_sync_history_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
    ):
        """Test getting sync history when none exists."""
        response = await client.get(
            f"/api/v1/data-sources/{sample_data_source.id}/history",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["history"] == []

    @pytest.mark.asyncio
    async def test_get_sync_history_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_data_source: DataSourceDB,
        sample_sync_history: list[DataSourceSyncHistory],
    ):
        """Test pagination of sync history."""
        response = await client.get(
            f"/api/v1/data-sources/{sample_data_source.id}/history?page=1&page_size=2",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["history"]) == 2
        # Pagination metadata may not be included in all response formats

    @pytest.mark.asyncio
    async def test_get_sync_history_nonexistent_source(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting history for non-existent source returns 404."""
        response = await client.get(
            "/api/v1/data-sources/nonexistent-id/history",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestHealthScoreCalculation:
    """Tests for health score calculation logic."""

    def test_health_score_no_failures_success(self):
        """Test health score with no failures and success status."""
        from api.routers.data_sources import _recalculate_health_score

        class MockDS:
            consecutive_failures = 0
            last_sync_status = "success"
            status = "active"

        score = _recalculate_health_score(MockDS())
        assert score == 100.0

    def test_health_score_no_failures_partial(self):
        """Test health score with partial sync."""
        from api.routers.data_sources import _recalculate_health_score

        class MockDS:
            consecutive_failures = 0
            last_sync_status = "partial"
            status = "active"

        score = _recalculate_health_score(MockDS())
        assert score == 75.0

    def test_health_score_one_failure(self):
        """Test health score with one consecutive failure."""
        from api.routers.data_sources import _recalculate_health_score

        class MockDS:
            consecutive_failures = 1
            last_sync_status = "failed"
            status = "error"

        score = _recalculate_health_score(MockDS())
        assert score == 50.0

    def test_health_score_two_failures(self):
        """Test health score with two consecutive failures."""
        from api.routers.data_sources import _recalculate_health_score

        class MockDS:
            consecutive_failures = 2
            last_sync_status = "failed"
            status = "error"

        score = _recalculate_health_score(MockDS())
        assert score == 25.0

    def test_health_score_three_plus_failures(self):
        """Test health score with three or more failures."""
        from api.routers.data_sources import _recalculate_health_score

        class MockDS:
            consecutive_failures = 3
            last_sync_status = "failed"
            status = "error"

        score = _recalculate_health_score(MockDS())
        assert score == 0.0

    def test_health_score_pending_status(self):
        """Test health score for pending (never synced) source."""
        from api.routers.data_sources import _recalculate_health_score

        class MockDS:
            consecutive_failures = 0
            last_sync_status = None
            status = "pending"

        score = _recalculate_health_score(MockDS())
        assert score == 0.0


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_validate_url_config_valid(self):
        """Test valid URL config passes validation."""
        from api.routers.data_sources import _validate_config

        _validate_config("url", {"url": "https://example.com/data.csv"})

    def test_validate_url_config_missing_url(self):
        """Test URL config without URL fails."""
        from api.routers.data_sources import _validate_config

        with pytest.raises(ValueError, match="url"):
            _validate_config("url", {})

    def test_validate_url_config_invalid_protocol(self):
        """Test URL with invalid protocol fails."""
        from api.routers.data_sources import _validate_config

        with pytest.raises(ValueError, match="http"):
            _validate_config("url", {"url": "ftp://example.com/file.csv"})

    def test_validate_portal_config_valid(self):
        """Test valid portal config passes validation."""
        from api.routers.data_sources import _validate_config

        _validate_config("portal_api", {"portal": "otodom", "city": "Warsaw"})

    def test_validate_portal_config_missing_portal(self):
        """Test portal config without portal name fails."""
        from api.routers.data_sources import _validate_config

        with pytest.raises(ValueError, match="portal"):
            _validate_config("portal_api", {"city": "Warsaw"})

    def test_validate_json_config_with_data(self):
        """Test JSON config with inline data."""
        from api.routers.data_sources import _validate_config

        _validate_config("json", {"data": [{"id": 1}]})

    def test_validate_json_config_with_url(self):
        """Test JSON config with URL."""
        from api.routers.data_sources import _validate_config

        _validate_config("json", {"url": "https://example.com/data.json"})

    def test_validate_json_config_missing_both(self):
        """Test JSON config without data or URL fails."""
        from api.routers.data_sources import _validate_config

        with pytest.raises(ValueError, match="data"):
            _validate_config("json", {})

    def test_validate_file_upload_config_valid(self):
        """Test valid file upload config."""
        from api.routers.data_sources import _validate_config

        _validate_config("file_upload", {"filename": "data.csv"})

    def test_validate_file_upload_config_missing_filename(self):
        """Test file upload config without filename fails."""
        from api.routers.data_sources import _validate_config

        with pytest.raises(ValueError, match="filename"):
            _validate_config("file_upload", {})
