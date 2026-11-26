"""
Unit tests for MCP Admin router (api/routers/mcp_admin.py).

Tests cover:
- GET /mcp/allowlist - List current allowlist
- POST /mcp/allowlist - Add connector to allowlist
- DELETE /mcp/allowlist/{name} - Remove from allowlist
- GET /mcp/allowlist/violations - List violations for audit
- DELETE /mcp/allowlist/violations - Clear all violations
- POST /mcp/allowlist/reload - Reload from YAML
- GET /mcp/connectors - List all connectors with status
- GET /mcp/connectors/{name} - Get single connector details
- GET /mcp/connectors/{name}/health - Health check single connector
- GET /mcp/health - Health check all connectors
- Auth requirement (API key)
- Error responses and edge cases
"""

from datetime import datetime
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.auth import get_api_key
from api.deps.auth import require_admin_access
from api.routers.mcp_admin import router as mcp_admin_router
from db.database import get_db
from mcp import (
    AllowlistConfig,
    AllowlistEntry,
    MCPConnectorRegistry,
    MCPEdition,
)
from mcp.allowlist_validator import AllowlistValidator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_entry(
    name: str = "test_connector",
    display_name: str = "Test Connector",
    description: str = "A test connector",
    enabled: bool = True,
    edition: MCPEdition = MCPEdition.COMMUNITY,
    added_by: str = "system",
) -> AllowlistEntry:
    return AllowlistEntry(
        name=name,
        display_name=display_name,
        description=description,
        enabled=enabled,
        edition=edition,
        added_by=added_by,
    )


def _make_config(
    edition: MCPEdition = MCPEdition.COMMUNITY,
    allowlist: Optional[List[AllowlistEntry]] = None,
    restricted: Optional[List[AllowlistEntry]] = None,
) -> AllowlistConfig:
    return AllowlistConfig(
        edition=edition,
        allowlist=allowlist or [_make_entry()],
        restricted=restricted or [],
        loaded_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_validator():
    """Create a mock AllowlistValidator with a default config."""
    config = _make_config()
    validator = MagicMock(spec=AllowlistValidator)
    validator.config = config
    validator.get_violations.return_value = []
    validator.clear_violations.return_value = None
    validator.get_all_connectors_info.return_value = {
        "test_connector": {
            "name": "test_connector",
            "display_name": "Test Connector",
            "description": "A test connector",
            "enabled": True,
            "edition": "community",
            "status": "allowlisted",
            "accessible_in_ce": True,
        },
    }
    validator.add_connector.return_value = _make_entry()
    validator.remove_connector.return_value = True
    validator.reload_config.return_value = config
    return validator


@pytest.fixture
def mock_connector_class():
    """Create a mock connector class for registry testing."""
    cls = MagicMock()
    cls.name = "test_connector"
    cls.display_name = "Test Connector"
    cls.description = "A test connector"
    cls.requires_api_key = False
    cls.supports_streaming = False
    cls.min_edition = MCPEdition.COMMUNITY
    cls.allowlisted = True
    return cls


@pytest.fixture
def mock_instance():
    """Create a mock connector instance for registry testing."""
    instance = MagicMock()
    instance.get_status.return_value = {"connected": True, "error": False}
    instance.health_check = AsyncMock()
    return instance


@pytest.fixture
async def mcp_client(mock_validator):
    """Create an async HTTP client for testing MCP admin endpoints."""
    test_app = FastAPI()
    test_app.include_router(mcp_admin_router, prefix="/api/v1")

    # Override API key auth
    async def override_get_api_key():
        return "test-api-key"

    test_app.dependency_overrides[get_api_key] = override_get_api_key

    # The admin routes sit behind the admin gate (an identity, not the API
    # key). These tests are about the routes themselves, so the gate is open.
    test_app.dependency_overrides[require_admin_access] = lambda: None

    with patch("api.routers.mcp_admin.get_allowlist_validator", return_value=mock_validator):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: unauthenticated client
# ---------------------------------------------------------------------------


@pytest.fixture
async def unauth_mcp_client():
    """Create a client without API key override to test auth requirement."""
    test_app = FastAPI()
    test_app.include_router(mcp_admin_router, prefix="/api/v1")

    # The gate asks the database whether the deployment holds an administrator.
    # A deployment without one keeps the API key as the way in, so the answer
    # here is "no administrator" - and the request then stops at the missing key.
    class _NoAdminResult:
        def scalar(self):
            return 0

    class _NoAdminSession:
        async def execute(self, *args, **kwargs):
            return _NoAdminResult()

    test_app.dependency_overrides[get_db] = lambda: _NoAdminSession()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ===========================================================================
# Test: GET /mcp/allowlist
# ===========================================================================


class TestGetAllowlist:
    """Test GET /api/v1/mcp/allowlist endpoint."""

    @pytest.mark.asyncio
    async def test_returns_allowlist_config(self, mcp_client):
        response = await mcp_client.get("/api/v1/mcp/allowlist")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "edition" in data
        assert "allowlist" in data
        assert "restricted" in data
        assert "total_allowed" in data
        assert "total_restricted" in data

    @pytest.mark.asyncio
    async def test_allowlist_has_correct_edition(self, mcp_client):
        response = await mcp_client.get("/api/v1/mcp/allowlist")
        data = response.json()
        assert data["edition"] == "community"

    @pytest.mark.asyncio
    async def test_allowlist_entries_have_required_fields(self, mcp_client):
        response = await mcp_client.get("/api/v1/mcp/allowlist")
        data = response.json()
        assert len(data["allowlist"]) > 0
        entry = data["allowlist"][0]
        assert "name" in entry
        assert "display_name" in entry
        assert "description" in entry
        assert "enabled" in entry
        assert "edition" in entry
        assert "added_by" in entry

    @pytest.mark.asyncio
    async def test_total_counts_are_correct(self, mcp_client):
        response = await mcp_client.get("/api/v1/mcp/allowlist")
        data = response.json()
        # Config has one enabled allowlist entry and no restricted
        assert data["total_allowed"] == 1
        assert data["total_restricted"] == 0


# ===========================================================================
# Test: POST /mcp/allowlist
# ===========================================================================


class TestAddToAllowlist:
    """Test POST /api/v1/mcp/allowlist endpoint."""

    @pytest.mark.asyncio
    async def test_add_connector_returns_201(self, mcp_client, mock_validator):
        response = await mcp_client.post(
            "/api/v1/mcp/allowlist",
            json={
                "name": "new_connector",
                "display_name": "New Connector",
                "description": "A new one",
                "edition": "community",
                "added_by": "admin",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "test_connector"  # mock returns default entry

    @pytest.mark.asyncio
    async def test_add_connector_calls_validator(self, mcp_client, mock_validator):
        await mcp_client.post(
            "/api/v1/mcp/allowlist",
            json={
                "name": "new_connector",
                "display_name": "New Connector",
            },
        )
        mock_validator.add_connector.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_with_invalid_edition_returns_400(self, mcp_client):
        response = await mcp_client.post(
            "/api/v1/mcp/allowlist",
            json={
                "name": "bad_connector",
                "display_name": "Bad",
                "edition": "invalid_edition",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid edition" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_with_enterprise_edition(self, mcp_client, mock_validator):
        response = await mcp_client.post(
            "/api/v1/mcp/allowlist",
            json={
                "name": "enterprise_connector",
                "display_name": "Enterprise Connector",
                "edition": "enterprise",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_add_with_pro_edition(self, mcp_client, mock_validator):
        response = await mcp_client.post(
            "/api/v1/mcp/allowlist",
            json={
                "name": "pro_connector",
                "display_name": "Pro Connector",
                "edition": "pro",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_add_with_missing_required_fields_returns_422(self, mcp_client):
        response = await mcp_client.post(
            "/api/v1/mcp/allowlist",
            json={"description": "missing name and display_name"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: DELETE /mcp/allowlist/{name}
# ===========================================================================


class TestRemoveFromAllowlist:
    """Test DELETE /api/v1/mcp/allowlist/{name} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_existing_connector_returns_204(self, mcp_client, mock_validator):
        response = await mcp_client.delete("/api/v1/mcp/allowlist/test_connector")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_remove_calls_validator(self, mcp_client, mock_validator):
        await mcp_client.delete("/api/v1/mcp/allowlist/test_connector")
        mock_validator.remove_connector.assert_called_once_with("test_connector")

    @pytest.mark.asyncio
    async def test_remove_nonexistent_returns_404(self, mcp_client, mock_validator):
        mock_validator.remove_connector.return_value = False
        response = await mcp_client.delete("/api/v1/mcp/allowlist/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


# ===========================================================================
# Test: GET /mcp/allowlist/violations
# ===========================================================================


class TestGetViolations:
    """Test GET /api/v1/mcp/allowlist/violations endpoint."""

    @pytest.mark.asyncio
    async def test_returns_empty_violations(self, mcp_client, mock_validator):
        response = await mcp_client.get("/api/v1/mcp/allowlist/violations")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["violations"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_violations_list(self, mcp_client, mock_validator):
        mock_validator.get_violations.return_value = [
            {
                "timestamp": "2025-01-01T00:00:00",
                "connector": "premium_connector",
                "operation": "get_connector",
                "context": {"edition": "community"},
                "config_edition": "community",
            }
        ]
        response = await mcp_client.get("/api/v1/mcp/allowlist/violations")
        data = response.json()
        assert data["total"] == 1
        assert len(data["violations"]) == 1
        violation = data["violations"][0]
        assert violation["connector"] == "premium_connector"
        assert violation["operation"] == "get_connector"

    @pytest.mark.asyncio
    async def test_violation_has_required_fields(self, mcp_client, mock_validator):
        mock_validator.get_violations.return_value = [
            {
                "timestamp": "2025-01-01T00:00:00",
                "connector": "test_conn",
                "operation": "register",
                "context": {},
                "config_edition": "community",
            }
        ]
        response = await mcp_client.get("/api/v1/mcp/allowlist/violations")
        violation = response.json()["violations"][0]
        assert "timestamp" in violation
        assert "connector" in violation
        assert "operation" in violation
        assert "context" in violation
        assert "config_edition" in violation


# ===========================================================================
# Test: DELETE /mcp/allowlist/violations
# ===========================================================================


class TestClearViolations:
    """Test DELETE /api/v1/mcp/allowlist/violations endpoint.

    Note: Due to route ordering, DELETE /allowlist/violations matches
    the DELETE /allowlist/{name} route first (name="violations").
    The clear_violations endpoint is registered after the path-param route,
    so FastAPI routes the request to remove_from_allowlist(name="violations").
    We test the clear_violations function directly instead.
    """

    @pytest.mark.asyncio
    async def test_clear_violations_returns_204(self, mcp_client, mock_validator):
        """DELETE /allowlist/violations is matched by {name} route."""
        # The mock returns True for remove_connector("violations")
        response = await mcp_client.delete("/api/v1/mcp/allowlist/violations")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_clear_violations_function_called_when_matched(self, mcp_client, mock_validator):
        """Test clear_violations logic by calling the endpoint handler directly."""
        from api.routers.mcp_admin import clear_violations

        with patch("api.routers.mcp_admin.get_allowlist_validator", return_value=mock_validator):
            await clear_violations()

        mock_validator.clear_violations.assert_called_once()


# ===========================================================================
# Test: POST /mcp/allowlist/reload
# ===========================================================================


class TestReloadAllowlist:
    """Test POST /api/v1/mcp/allowlist/reload endpoint."""

    @pytest.mark.asyncio
    async def test_reload_returns_success(self, mcp_client, mock_validator):
        with (
            patch.object(MCPConnectorRegistry, "set_edition"),
            patch.object(MCPConnectorRegistry, "set_allowlist"),
        ):
            response = await mcp_client.post("/api/v1/mcp/allowlist/reload")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Allowlist reloaded successfully"
        assert data["allowlist_count"] == 1
        assert data["restricted_count"] == 0
        assert data["edition"] == "community"
        assert "loaded_at" in data

    @pytest.mark.asyncio
    async def test_reload_calls_set_edition_and_allowlist(self, mcp_client, mock_validator):
        with (
            patch.object(MCPConnectorRegistry, "set_edition") as mock_set_edition,
            patch.object(MCPConnectorRegistry, "set_allowlist") as mock_set_allowlist,
        ):
            await mcp_client.post("/api/v1/mcp/allowlist/reload")

        mock_set_edition.assert_called_once()
        mock_set_allowlist.assert_called_once()

    @pytest.mark.asyncio
    async def test_reload_with_restricted_entries(self, mcp_client, mock_validator):
        restricted = [_make_entry(name="premium_conn", edition=MCPEdition.PRO)]
        config = _make_config(restricted=restricted)
        mock_validator.reload_config.return_value = config

        with (
            patch.object(MCPConnectorRegistry, "set_edition"),
            patch.object(MCPConnectorRegistry, "set_allowlist"),
        ):
            response = await mcp_client.post("/api/v1/mcp/allowlist/reload")

        data = response.json()
        assert data["restricted_count"] == 1


# ===========================================================================
# Test: GET /mcp/connectors
# ===========================================================================


class TestListConnectors:
    """Test GET /api/v1/mcp/connectors endpoint."""

    @pytest.mark.asyncio
    async def test_returns_connectors_list(self, mcp_client, mock_validator):
        with (
            patch.object(
                MCPConnectorRegistry,
                "list_connectors",
                return_value=["test_connector"],
            ),
            patch.dict(MCPConnectorRegistry._connectors, {}, clear=True),
            patch.dict(MCPConnectorRegistry._instances, {}, clear=True),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "connectors" in data
        assert "edition" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_connector_has_status_field(self, mcp_client, mock_validator):
        with (
            patch.object(
                MCPConnectorRegistry,
                "list_connectors",
                return_value=["test_connector"],
            ),
            patch.dict(MCPConnectorRegistry._connectors, {}, clear=True),
            patch.dict(MCPConnectorRegistry._instances, {}, clear=True),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors")

        data = response.json()
        assert len(data["connectors"]) > 0
        connector = data["connectors"][0]
        assert "status" in connector
        assert "name" in connector
        assert "enabled" in connector
        assert "registered" in connector

    @pytest.mark.asyncio
    async def test_disabled_connector_shows_disabled_status(self, mcp_client, mock_validator):
        mock_validator.get_all_connectors_info.return_value = {
            "disabled_conn": {
                "name": "disabled_conn",
                "display_name": "Disabled",
                "description": "",
                "enabled": False,
                "edition": "community",
                "status": "allowlisted",
                "accessible_in_ce": False,
            },
        }
        with (
            patch.object(
                MCPConnectorRegistry,
                "list_connectors",
                return_value=[],
            ),
            patch.dict(MCPConnectorRegistry._connectors, {}, clear=True),
            patch.dict(MCPConnectorRegistry._instances, {}, clear=True),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors")

        data = response.json()
        conn = next(c for c in data["connectors"] if c["name"] == "disabled_conn")
        assert conn["status"] == "disabled"


# ===========================================================================
# Test: GET /mcp/connectors/{name}
# ===========================================================================


class TestGetConnectorDetails:
    """Test GET /api/v1/mcp/connectors/{name} endpoint."""

    @pytest.mark.asyncio
    async def test_returns_connector_details(self, mcp_client, mock_validator):
        with (
            patch.object(
                MCPConnectorRegistry,
                "list_connectors",
                return_value=["test_connector"],
            ),
            patch.dict(MCPConnectorRegistry._connectors, {}, clear=True),
            patch.dict(MCPConnectorRegistry._instances, {}, clear=True),
            patch.dict(MCPConnectorRegistry._configs, {}, clear=True),
            patch(
                "mcp.rate_limiter.get_connector_rate_limiter",
                side_effect=ImportError,
            ),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/test_connector")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "test_connector"
        assert "status" in data
        assert "rate_limit" in data
        assert "config" in data
        assert "instance_status" in data

    @pytest.mark.asyncio
    async def test_nonexistent_connector_returns_404(self, mcp_client, mock_validator):
        mock_validator.get_all_connectors_info.return_value = {}
        with patch.dict(MCPConnectorRegistry._connectors, {}, clear=True):
            response = await mcp_client.get("/api/v1/mcp/connectors/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_connector_with_instance_returns_instance_status(
        self, mcp_client, mock_validator, mock_instance
    ):
        mock_instance.get_status.return_value = {
            "connected": True,
            "error": False,
        }
        with (
            patch.object(
                MCPConnectorRegistry,
                "list_connectors",
                return_value=["test_connector"],
            ),
            patch.dict(MCPConnectorRegistry._connectors, {}, clear=True),
            patch.dict(
                MCPConnectorRegistry._instances,
                {"test_connector": mock_instance},
            ),
            patch.dict(MCPConnectorRegistry._configs, {}, clear=True),
            patch(
                "mcp.rate_limiter.get_connector_rate_limiter",
                side_effect=ImportError,
            ),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/test_connector")

        data = response.json()
        assert data["has_instance"] is True
        assert data["instance_status"] == {"connected": True, "error": False}

    @pytest.mark.asyncio
    async def test_connector_with_config_returns_config(self, mcp_client, mock_validator):
        from mcp.config import MCPConnectorConfig

        mock_config = MagicMock(spec=MCPConnectorConfig)
        mock_config.to_dict.return_value = {"name": "test_connector", "timeout": 30}

        with (
            patch.object(
                MCPConnectorRegistry,
                "list_connectors",
                return_value=["test_connector"],
            ),
            patch.dict(MCPConnectorRegistry._connectors, {}, clear=True),
            patch.dict(MCPConnectorRegistry._instances, {}, clear=True),
            patch.dict(
                MCPConnectorRegistry._configs,
                {"test_connector": mock_config},
            ),
            patch(
                "mcp.rate_limiter.get_connector_rate_limiter",
                side_effect=ImportError,
            ),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/test_connector")

        data = response.json()
        assert data["config"] == {"name": "test_connector", "timeout": 30}

    @pytest.mark.asyncio
    async def test_connector_instance_status_exception_handled(self, mcp_client, mock_validator):
        """Instance get_status() raises an exception."""
        mock_inst = MagicMock()
        mock_inst.get_status.side_effect = RuntimeError("status check failed")

        with (
            patch.object(
                MCPConnectorRegistry,
                "list_connectors",
                return_value=["test_connector"],
            ),
            patch.dict(MCPConnectorRegistry._connectors, {}, clear=True),
            patch.dict(
                MCPConnectorRegistry._instances,
                {"test_connector": mock_inst},
            ),
            patch.dict(MCPConnectorRegistry._configs, {}, clear=True),
            patch(
                "mcp.rate_limiter.get_connector_rate_limiter",
                side_effect=ImportError,
            ),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/test_connector")

        data = response.json()
        assert data["instance_status"]["error"] is True

    @pytest.mark.asyncio
    async def test_connector_in_registry_but_not_in_allowlist(self, mcp_client, mock_validator):
        """Connector registered in registry but not in allowlist info."""
        mock_validator.get_all_connectors_info.return_value = {}

        mock_cls = MagicMock()
        mock_cls.requires_api_key = True
        mock_cls.supports_streaming = True
        mock_cls.min_edition = MCPEdition.PRO
        mock_cls.display_name = "Registry Only"
        mock_cls.description = "Only in registry"

        with (
            patch.object(
                MCPConnectorRegistry,
                "list_connectors",
                return_value=["reg_only"],
            ),
            patch.dict(
                MCPConnectorRegistry._connectors,
                {"reg_only": mock_cls},
            ),
            patch.dict(MCPConnectorRegistry._instances, {}, clear=True),
            patch.dict(MCPConnectorRegistry._configs, {}, clear=True),
            patch(
                "mcp.rate_limiter.get_connector_rate_limiter",
                side_effect=ImportError,
            ),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/reg_only")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "reg_only"
        assert data["requires_api_key"] is True


# ===========================================================================
# Test: GET /mcp/connectors/{name}/health
# ===========================================================================


class TestHealthCheckConnector:
    """Test GET /api/v1/mcp/connectors/{name}/health endpoint."""

    @pytest.mark.asyncio
    async def test_healthy_connector(self, mcp_client, mock_validator, mock_instance):
        from mcp.result import MCPConnectorResult

        mock_instance.health_check.return_value = MCPConnectorResult(
            success=True,
            data={"latency_ms": 50},
            errors=[],
            warnings=[],
            connector_name="test_connector",
            operation="health_check",
        )

        with (
            patch.dict(
                MCPConnectorRegistry._connectors,
                {"test_connector": MagicMock()},
            ),
            patch.dict(
                MCPConnectorRegistry._instances,
                {"test_connector": mock_instance},
            ),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/test_connector/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "test_connector"
        assert data["status"] == "healthy"
        assert data["success"] is True
        assert "response_time_ms" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_unhealthy_connector(self, mcp_client, mock_validator, mock_instance):
        from mcp.result import MCPConnectorResult

        mock_instance.health_check.return_value = MCPConnectorResult(
            success=False,
            data=None,
            errors=["Connection refused"],
            warnings=[],
            connector_name="test_connector",
            operation="health_check",
        )

        with (
            patch.dict(
                MCPConnectorRegistry._connectors,
                {"test_connector": MagicMock()},
            ),
            patch.dict(
                MCPConnectorRegistry._instances,
                {"test_connector": mock_instance},
            ),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/test_connector/health")

        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["success"] is False
        assert "Connection refused" in data["errors"]

    @pytest.mark.asyncio
    async def test_not_registered_connector_returns_404(self, mcp_client, mock_validator):
        with patch.dict(MCPConnectorRegistry._connectors, {}, clear=True):
            response = await mcp_client.get("/api/v1/mcp/connectors/unknown/health")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_not_instantiated_connector_returns_unhealthy(self, mcp_client, mock_validator):
        with (
            patch.dict(
                MCPConnectorRegistry._connectors,
                {"test_connector": MagicMock()},
            ),
            patch.dict(MCPConnectorRegistry._instances, {}, clear=True),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/test_connector/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["success"] is False
        assert "Connector not instantiated" in data["errors"]

    @pytest.mark.asyncio
    async def test_health_check_exception_returns_error(
        self, mcp_client, mock_validator, mock_instance
    ):
        mock_instance.health_check.side_effect = Exception("timeout")

        with (
            patch.dict(
                MCPConnectorRegistry._connectors,
                {"test_connector": MagicMock()},
            ),
            patch.dict(
                MCPConnectorRegistry._instances,
                {"test_connector": mock_instance},
            ),
        ):
            response = await mcp_client.get("/api/v1/mcp/connectors/test_connector/health")

        data = response.json()
        assert data["status"] == "error"
        assert data["success"] is False
        assert "timeout" in data["errors"]


# ===========================================================================
# Test: GET /mcp/health
# ===========================================================================


class TestHealthCheckAll:
    """Test GET /api/v1/mcp/health endpoint."""

    @pytest.mark.asyncio
    async def test_healthy_when_no_connectors(self, mcp_client, mock_validator):
        with patch.object(
            MCPConnectorRegistry,
            "health_check_all",
            return_value={},
        ):
            response = await mcp_client.get("/api/v1/mcp/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["connectors_checked"] == 0

    @pytest.mark.asyncio
    async def test_healthy_when_all_pass(self, mcp_client, mock_validator):
        from mcp.result import MCPConnectorResult

        with patch.object(
            MCPConnectorRegistry,
            "health_check_all",
            return_value={
                "conn1": MCPConnectorResult(
                    success=True, errors=[], connector_name="conn1", operation="health"
                ),
                "conn2": MCPConnectorResult(
                    success=True, errors=[], connector_name="conn2", operation="health"
                ),
            },
        ):
            response = await mcp_client.get("/api/v1/mcp/health")

        data = response.json()
        assert data["status"] == "healthy"
        assert data["connectors_checked"] == 2

    @pytest.mark.asyncio
    async def test_degraded_when_some_fail(self, mcp_client, mock_validator):
        from mcp.result import MCPConnectorResult

        with patch.object(
            MCPConnectorRegistry,
            "health_check_all",
            return_value={
                "conn1": MCPConnectorResult(
                    success=True, errors=[], connector_name="conn1", operation="health"
                ),
                "conn2": MCPConnectorResult(
                    success=False, errors=["fail"], connector_name="conn2", operation="health"
                ),
            },
        ):
            response = await mcp_client.get("/api/v1/mcp/health")

        data = response.json()
        assert data["status"] == "degraded"
        assert data["connectors_checked"] == 2

    @pytest.mark.asyncio
    async def test_unhealthy_when_all_fail(self, mcp_client, mock_validator):
        from mcp.result import MCPConnectorResult

        with patch.object(
            MCPConnectorRegistry,
            "health_check_all",
            return_value={
                "conn1": MCPConnectorResult(
                    success=False, errors=["err1"], connector_name="conn1", operation="health"
                ),
                "conn2": MCPConnectorResult(
                    success=False, errors=["err2"], connector_name="conn2", operation="health"
                ),
            },
        ):
            response = await mcp_client.get("/api/v1/mcp/health")

        data = response.json()
        assert data["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_all_exception_handled(self, mcp_client, mock_validator):
        with patch.object(
            MCPConnectorRegistry,
            "health_check_all",
            side_effect=Exception("registry error"),
        ):
            response = await mcp_client.get("/api/v1/mcp/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Exception caught gracefully, 0 connectors checked
        assert data["connectors_checked"] == 0

    @pytest.mark.asyncio
    async def test_health_includes_timestamp(self, mcp_client, mock_validator):
        with patch.object(
            MCPConnectorRegistry,
            "health_check_all",
            return_value={},
        ):
            response = await mcp_client.get("/api/v1/mcp/health")

        data = response.json()
        assert "timestamp" in data
        assert "edition" in data


# ===========================================================================
# Test: Auth requirement
# ===========================================================================


class TestAuthRequirement:
    """Test that all endpoints require API key authentication."""

    @pytest.mark.asyncio
    async def test_allowlist_requires_auth(self, unauth_mcp_client):
        response = await unauth_mcp_client.get("/api/v1/mcp/allowlist")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_add_to_allowlist_requires_auth(self, unauth_mcp_client):
        response = await unauth_mcp_client.post(
            "/api/v1/mcp/allowlist",
            json={"name": "x", "display_name": "X"},
        )
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_remove_from_allowlist_requires_auth(self, unauth_mcp_client):
        response = await unauth_mcp_client.delete("/api/v1/mcp/allowlist/x")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_violations_requires_auth(self, unauth_mcp_client):
        response = await unauth_mcp_client.get("/api/v1/mcp/allowlist/violations")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_connectors_requires_auth(self, unauth_mcp_client):
        response = await unauth_mcp_client.get("/api/v1/mcp/connectors")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_health_requires_auth(self, unauth_mcp_client):
        response = await unauth_mcp_client.get("/api/v1/mcp/health")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# Test: Helper function _calculate_connector_status
# ===========================================================================


class TestCalculateConnectorStatus:
    """Test the _calculate_connector_status helper function."""

    def test_disabled_connector(self):
        from api.routers.mcp_admin import _calculate_connector_status

        status_val, error = _calculate_connector_status("x", enabled=False, has_instance=False)
        assert status_val == "disabled"
        assert error is None

    def test_not_instantiated_connector(self):
        from api.routers.mcp_admin import _calculate_connector_status

        with patch.dict(MCPConnectorRegistry._instances, {}, clear=True):
            status_val, error = _calculate_connector_status("x", enabled=True, has_instance=False)
        assert status_val == "not_instantiated"
        assert error is None

    def test_active_connector(self):
        from api.routers.mcp_admin import _calculate_connector_status

        mock_inst = MagicMock()
        mock_inst.get_status.return_value = {"connected": True, "error": False}

        with patch.dict(MCPConnectorRegistry._instances, {"x": mock_inst}):
            status_val, error = _calculate_connector_status("x", enabled=True, has_instance=True)
        assert status_val == "active"
        assert error is None

    def test_error_connector_with_error_status(self):
        from api.routers.mcp_admin import _calculate_connector_status

        mock_inst = MagicMock()
        mock_inst.get_status.return_value = {
            "connected": False,
            "error": True,
            "error_message": "Connection refused",
        }

        with patch.dict(MCPConnectorRegistry._instances, {"x": mock_inst}):
            status_val, error = _calculate_connector_status("x", enabled=True, has_instance=True)
        assert status_val == "error"
        assert error == "Connection refused"

    def test_connector_status_exception(self):
        from api.routers.mcp_admin import _calculate_connector_status

        mock_inst = MagicMock()
        mock_inst.get_status.side_effect = Exception("status error")

        with patch.dict(MCPConnectorRegistry._instances, {"x": mock_inst}):
            status_val, error = _calculate_connector_status("x", enabled=True, has_instance=True)
        assert status_val == "error"
        assert "status error" in error


# ===========================================================================
# Test: Helper function _get_connector_class_info
# ===========================================================================


class TestGetConnectorClassInfo:
    """Test the _get_connector_class_info helper function."""

    def test_unknown_connector_returns_empty(self):
        from api.routers.mcp_admin import _get_connector_class_info

        with patch.dict(MCPConnectorRegistry._connectors, {}, clear=True):
            result = _get_connector_class_info("nonexistent")
        assert result == {}

    def test_registered_connector_returns_info(self):
        from api.routers.mcp_admin import _get_connector_class_info

        mock_cls = MagicMock()
        mock_cls.requires_api_key = True
        mock_cls.supports_streaming = False
        mock_cls.min_edition = MCPEdition.PRO
        mock_cls.display_name = "My Connector"
        mock_cls.description = "A test connector"

        with patch.dict(MCPConnectorRegistry._connectors, {"my_conn": mock_cls}):
            result = _get_connector_class_info("my_conn")

        assert result["requires_api_key"] is True
        assert result["supports_streaming"] is False
        assert result["min_edition"] == "pro"
        assert result["display_name"] == "My Connector"
        assert result["description"] == "A test connector"
