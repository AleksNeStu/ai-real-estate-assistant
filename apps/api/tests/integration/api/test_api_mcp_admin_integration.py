"""Integration tests for mcp_admin router."""

import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# --- Stub heavy imports before importing the router ---
# The mcp_admin router imports from the `mcp` package which may not be available.
# A stub module takes attributes the real module does not have, so it is
# typed `Any` - mypy reads a module as the set of names it declares.
_mcp_stub: Any = types.ModuleType("mcp")


class _MCPEdition:
    COMMUNITY = "community"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    def __init__(self, value="community"):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, _MCPEdition):
            return self.value == other.value
        return self.value == other

    def __repr__(self):
        return f"MCPEdition({self.value})"


class _AllowlistEntry:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "")
        self.display_name = kwargs.get("display_name", "")
        self.description = kwargs.get("description", "")
        self.enabled = kwargs.get("enabled", True)
        self.edition = kwargs.get("edition", _MCPEdition())
        self.added_at = kwargs.get("added_at", None)
        self.added_by = kwargs.get("added_by", "system")


class _AllowlistConfig:
    def __init__(self, **kwargs):
        self.edition = kwargs.get("edition", _MCPEdition())
        self.allowlist = kwargs.get("allowlist", [])
        self.restricted = kwargs.get("restricted", [])
        self.loaded_at = kwargs.get("loaded_at", None)
        self.config_path = kwargs.get("config_path", None)

    def get_allowlist_names(self):
        return [e.name for e in self.allowlist if e.enabled]


class _MCPConnectorRegistry:
    _instances: dict[str, Any] = {}
    _connectors: dict[str, Any] = {}
    _configs: dict[str, Any] = {}

    @classmethod
    def list_connectors(cls, include_non_accessible=False):
        return list(cls._connectors.keys())

    @classmethod
    def set_edition(cls, edition):
        pass

    @classmethod
    def set_allowlist(cls, names):
        pass

    @classmethod
    async def health_check_all(cls):
        return {}


_mcp_stub.MCPEdition = _MCPEdition
_mcp_stub.AllowlistEntry = _AllowlistEntry
_mcp_stub.AllowlistConfig = _AllowlistConfig
_mcp_stub.MCPConnectorRegistry = _MCPConnectorRegistry
_mcp_stub.get_allowlist_validator = MagicMock()

import sys  # noqa: E402

_mcp_original = sys.modules.get("mcp")
sys.modules["mcp"] = _mcp_stub

from api.auth import get_api_key  # noqa: E402
from api.deps.auth import require_admin_access  # noqa: E402
from api.routers import mcp_admin  # noqa: E402

# Restore original mcp module immediately after importing the router,
# so that subsequent test modules see the real mcp package during collection.
if _mcp_original is not None:
    sys.modules["mcp"] = _mcp_original
else:
    sys.modules.pop("mcp", None)


# Re-stub for each test function scope (restored in fixture below)
@pytest.fixture(autouse=True)
def _isolate_mcp_stub():
    """Stub mcp during each test, restore after to avoid polluting other test files."""
    _saved = sys.modules.get("mcp")
    sys.modules["mcp"] = _mcp_stub
    yield
    if _saved is not None:
        sys.modules["mcp"] = _saved
    else:
        sys.modules.pop("mcp", None)


def _make_validator_mock():
    """Create a mock allowlist validator."""
    validator = MagicMock()

    config = _AllowlistConfig(
        allowlist=[
            _AllowlistEntry(
                name="firecrawl",
                display_name="Firecrawl",
                description="Web scraping",
                edition=_MCPEdition("community"),
            )
        ],
        restricted=[
            _AllowlistEntry(
                name="premium-tool",
                display_name="Premium Tool",
                description="Enterprise only",
                edition=_MCPEdition("enterprise"),
            )
        ],
    )

    validator.config = config
    validator.get_violations.return_value = []
    validator.get_all_connectors_info.return_value = {
        "firecrawl": {
            "display_name": "Firecrawl",
            "description": "Web scraping",
            "enabled": True,
            "edition": "community",
            "accessible_in_ce": True,
        },
    }
    validator.add_connector.return_value = _AllowlistEntry(
        name="new-tool",
        display_name="New Tool",
        description="Test tool",
        edition=_MCPEdition("community"),
    )
    validator.remove_connector.return_value = True
    validator.reload_config.return_value = config

    return validator


@pytest.fixture
def test_app():
    """Create test app with mcp_admin router and mocked auth."""
    app = FastAPI()
    app.include_router(mcp_admin.router, prefix="/api/v1")

    # Override API key check
    async def override_get_api_key():
        return "test-key"

    app.dependency_overrides[get_api_key] = override_get_api_key
    # The operator's routes are gated by an identity; the gate has its own
    # tests. These ones exercise the handlers behind it.
    app.dependency_overrides[require_admin_access] = lambda: None
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestMCPAdminAPI:
    """Integration tests for MCP admin endpoints."""

    @pytest.mark.asyncio
    async def test_get_allowlist(self, client):
        """Gets current allowlist."""
        validator = _make_validator_mock()
        with (
            patch.object(_mcp_stub, "get_allowlist_validator", return_value=validator),
            patch("api.routers.mcp_admin.get_allowlist_validator", return_value=validator),
        ):
            resp = await client.get("/api/v1/mcp/allowlist")
        assert resp.status_code == 200
        data = resp.json()
        assert "allowlist" in data
        assert "restricted" in data
        assert data["edition"] == "community"

    @pytest.mark.asyncio
    async def test_get_violations(self, client):
        """Gets allowlist violations (empty)."""
        validator = _make_validator_mock()
        with patch("api.routers.mcp_admin.get_allowlist_validator", return_value=validator):
            resp = await client.get("/api/v1/mcp/allowlist/violations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["violations"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_remove_from_allowlist(self, client):
        """Removes connector from allowlist."""
        validator = _make_validator_mock()
        with patch("api.routers.mcp_admin.get_allowlist_validator", return_value=validator):
            resp = await client.delete("/api/v1/mcp/allowlist/firecrawl")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_remove_from_allowlist_not_found(self, client):
        """Returns 404 when removing non-existent connector."""
        validator = _make_validator_mock()
        validator.remove_connector.return_value = False
        with patch("api.routers.mcp_admin.get_allowlist_validator", return_value=validator):
            resp = await client.delete("/api/v1/mcp/allowlist/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_connectors(self, client):
        """Lists all connectors with status."""
        validator = _make_validator_mock()
        # Clear registry instances for clean test
        _MCPConnectorRegistry._instances = {}
        _MCPConnectorRegistry._connectors = {}

        with patch("api.routers.mcp_admin.get_allowlist_validator", return_value=validator):
            resp = await client.get("/api/v1/mcp/connectors")
        assert resp.status_code == 200
        data = resp.json()
        assert "connectors" in data
        assert data["edition"] == "community"

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Health check for MCP system."""
        validator = _make_validator_mock()
        _MCPConnectorRegistry._instances = {}

        with patch("api.routers.mcp_admin.get_allowlist_validator", return_value=validator):
            resp = await client.get("/api/v1/mcp/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["connectors_checked"] == 0
