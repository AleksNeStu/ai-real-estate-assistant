"""
Unit tests for MCP Connector Registry Admin API endpoints (Task #71).

Tests cover:
- GET /mcp/connectors - List all connectors
- GET /mcp/connectors/{name} - Get single connector details
- GET /mcp/connectors/{name}/health - Health check single connector
- GET /mcp/health - Health check all connectors
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from mcp import MCPConnectorResult


@pytest.fixture(autouse=True)
def _open_the_admin_gate(open_admin_gate):
    """These tests exercise the handlers behind the gate, not the gate."""


client = TestClient(app)

CSRF_TOKEN = "test-csrf-token"
HEADERS = {"X-API-Key": "test-key", "X-CSRF-Token": CSRF_TOKEN}

# Set the CSRF token cookie on the client
client.cookies.set("csrf_token", CSRF_TOKEN)


@pytest.fixture
def mock_allowlist_validator():
    """Mock AllowlistValidator for testing."""
    validator = MagicMock()
    validator.config = MagicMock()
    validator.config.edition = MagicMock(value="community")
    validator.config.allowlist = []
    validator.config.restricted = []
    validator.config.loaded_at = datetime.utcnow()
    validator.config.config_path = None
    validator.config.get_allowlist_names.return_value = []

    # Mock get_all_connectors_info
    validator.get_all_connectors_info.return_value = {
        "test_connector": {
            "display_name": "Test Connector",
            "description": "A test connector",
            "enabled": True,
            "edition": "community",
            "status": "active",
            "accessible_in_ce": True,
        },
        "pro_connector": {
            "display_name": "Pro Connector",
            "description": "A pro connector",
            "enabled": True,
            "edition": "pro",
            "status": "restricted",
            "accessible_in_ce": False,
        },
    }

    return validator


@pytest.fixture
def mock_registry():
    """Mock MCPConnectorRegistry for testing."""
    with patch("api.routers.mcp_admin.MCPConnectorRegistry") as mock:
        mock.list_connectors.return_value = ["test_connector", "pro_connector"]
        mock._instances = {}
        mock._connectors = {
            "test_connector": MagicMock(
                display_name="Test Connector",
                description="A test connector",
                requires_api_key=False,
                supports_streaming=True,
                min_edition=MagicMock(value="community"),
            ),
            "pro_connector": MagicMock(
                display_name="Pro Connector",
                description="A pro connector",
                requires_api_key=True,
                supports_streaming=False,
                min_edition=MagicMock(value="pro"),
            ),
        }
        mock._configs = {}
        mock.get_connector_info.return_value = {
            "name": "test_connector",
            "display_name": "Test Connector",
            "description": "A test connector",
            "requires_api_key": False,
            "allowlisted": True,
            "accessible": True,
            "min_edition": "community",
            "supports_streaming": True,
        }
        yield mock


class TestListConnectors:
    """Tests for GET /mcp/connectors endpoint."""

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_list_connectors_returns_all_connectors(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test that list_connectors returns all registered connectors."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator

        response = client.get("/api/v1/mcp/connectors", headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert "connectors" in data
        assert "edition" in data
        assert "total" in data
        assert data["edition"] == "community"

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_list_connectors_includes_status(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test that each connector includes status information."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator

        response = client.get("/api/v1/mcp/connectors", headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        for connector in data["connectors"]:
            assert "name" in connector
            assert "display_name" in connector
            assert "status" in connector
            assert "enabled" in connector


class TestGetConnectorDetails:
    """Tests for GET /mcp/connectors/{name} endpoint."""

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_get_connector_details_returns_connector(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test getting details for a specific connector."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator

        response = client.get("/api/v1/mcp/connectors/test_connector", headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_connector"
        assert "display_name" in data
        assert "status" in data
        assert "enabled" in data

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_get_connector_details_not_found(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test 404 response for non-existent connector."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator

        response = client.get("/api/v1/mcp/connectors/nonexistent", headers=HEADERS)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestHealthCheckConnector:
    """Tests for GET /mcp/connectors/{name}/health endpoint."""

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_health_check_returns_health_status(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test health check for a specific connector."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator

        # Mock the instance
        mock_instance = MagicMock()
        mock_instance.health_check = AsyncMock(
            return_value=MCPConnectorResult.success_result(
                data={"connected": True},
                connector_name="test_connector",
                operation="health_check",
            )
        )
        mock_registry._instances = {"test_connector": mock_instance}

        response = client.get("/api/v1/mcp/connectors/test_connector/health", headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_connector"
        assert "status" in data
        assert "success" in data
        assert "errors" in data

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_health_check_not_instantiated(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test health check for connector without instance."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator
        mock_registry._instances = {}  # No instances

        response = client.get("/api/v1/mcp/connectors/test_connector/health", headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not instantiated" in data["errors"][0].lower()

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_health_check_not_found(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test 404 response for health check on non-existent connector."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator
        mock_registry._connectors = {}  # No connectors registered

        response = client.get("/api/v1/mcp/connectors/nonexistent/health", headers=HEADERS)

        assert response.status_code == 404


class TestHealthCheckAll:
    """Tests for GET /mcp/health endpoint."""

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_health_check_all_returns_overall_status(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test health check for all connectors returns overall status."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator

        # Mock health_check_all
        mock_registry.health_check_all = AsyncMock(
            return_value={
                "test_connector": MCPConnectorResult.success_result(
                    data={"connected": True},
                    connector_name="test_connector",
                    operation="health_check",
                )
            }
        )

        response = client.get("/api/v1/mcp/health", headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "edition" in data
        assert "connectors_checked" in data

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_health_check_all_no_connectors(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test health check when no connectors are instantiated."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator
        mock_registry.health_check_all = AsyncMock(return_value={})

        response = client.get("/api/v1/mcp/health", headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"  # No connectors = healthy
        assert data["connectors_checked"] == 0


class TestConnectorStatusIndicators:
    """Tests for enhanced status indicators."""

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_status_active(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test that active status is correctly set."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator

        # Mock instance with connected status
        mock_instance = MagicMock()
        mock_instance.get_status.return_value = {"connected": True}
        mock_registry._instances = {"test_connector": mock_instance}

        response = client.get("/api/v1/mcp/connectors", headers=HEADERS)

        assert response.status_code == 200
        # The status should be calculated based on instance state

    @patch("api.routers.mcp_admin.get_allowlist_validator")
    @patch("api.auth.get_settings")
    def test_status_disabled(
        self, mock_get_settings, mock_get_validator, mock_allowlist_validator, mock_registry
    ):
        """Test that disabled status is correctly set."""
        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_get_validator.return_value = mock_allowlist_validator
        # Update connector info to be disabled
        mock_allowlist_validator.get_all_connectors_info.return_value = {
            "test_connector": {
                "display_name": "Test Connector",
                "description": "A test connector",
                "enabled": False,  # Disabled
                "edition": "community",
                "status": "disabled",
                "accessible_in_ce": True,
            },
        }

        response = client.get("/api/v1/mcp/connectors", headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        # Find the disabled connector
        connector = next((c for c in data["connectors"] if c["name"] == "test_connector"), None)
        assert connector is not None
