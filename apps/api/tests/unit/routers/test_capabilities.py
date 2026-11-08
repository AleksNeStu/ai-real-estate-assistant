"""
Tests for the deployment capabilities endpoint.

Task #34: the frontend must not offer what the deployment cannot serve, so
the backend has to publish the answer.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routers import capabilities


def _settings(**overrides):
    """A settings stub with the fields the capability builder reads."""
    defaults = {
        "auth_jwt_enabled": False,
        "auth_oauth_google_enabled": False,
        "auth_oauth_apple_enabled": False,
        "google_client_id": None,
        "google_client_secret": None,
        "apple_client_id": None,
        "apple_team_id": None,
        "demo_mode": True,
        "default_provider": "zai",
        "sentry_dsn": None,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


@pytest.fixture
async def capabilities_client():
    app = FastAPI()
    app.include_router(capabilities.router, prefix="/api/v1")
    app.state.email_enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestBuildCapabilities:
    """The builder is pure — it only reads the settings."""

    def test_oauth_is_off_without_configuration(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"] == {"google": False, "apple": False}

    def test_a_provider_needs_both_the_flag_and_the_credentials(self):
        # The flag is on but no client id was configured: the endpoint would
        # answer 500, so the capability must stay off.
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(auth_oauth_google_enabled=True),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"]["google"] is False

    def test_a_fully_configured_provider_is_reported_as_available(self):
        with patch.object(
            capabilities,
            "get_settings",
            return_value=_settings(
                auth_oauth_google_enabled=True,
                google_client_id="id",
                google_client_secret="secret",  # pragma: allowlist secret
            ),
        ):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["auth"]["oauth"]["google"] is True
        assert result["auth"]["oauth"]["apple"] is False

    def test_a_dummy_mail_service_is_reported_as_disabled(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert result["email"] == {"enabled": False, "provider": "dummy"}

    def test_a_configured_mail_service_is_reported_as_enabled(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=True)

        assert result["email"] == {"enabled": True, "provider": "smtp"}

    def test_error_tracking_follows_the_configured_dsn(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            assert (
                capabilities.build_capabilities(email_enabled=False)["observability"][
                    "error_tracking"
                ]
                is False
            )

        with patch.object(
            capabilities, "get_settings", return_value=_settings(sentry_dsn="https://key@sentry/1")
        ):
            assert (
                capabilities.build_capabilities(email_enabled=False)["observability"][
                    "error_tracking"
                ]
                is True
            )


class TestCapabilitiesEndpoint:
    """The endpoint reads the mail state the startup recorded."""

    @pytest.mark.asyncio
    async def test_endpoint_reports_the_startup_mail_state(self, capabilities_client):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get("/api/v1/capabilities")

        assert response.status_code == 200
        body = response.json()
        assert body["email"]["enabled"] is False
        assert body["auth"]["oauth"]["google"] is False
        assert "llm" in body
        assert "observability" in body

    @pytest.mark.asyncio
    async def test_endpoint_needs_no_api_key(self, capabilities_client):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get("/api/v1/capabilities")

        assert response.status_code == 200
