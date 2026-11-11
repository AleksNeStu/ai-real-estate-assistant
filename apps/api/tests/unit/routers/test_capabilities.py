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
from db.database import get_db


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

    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
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


class TestBuildMetadata:
    """The build is published to a privileged caller and to nobody else."""

    @pytest.mark.asyncio
    async def test_an_ordinary_caller_is_told_nothing_about_the_build(
        self, capabilities_client, monkeypatch
    ):
        monkeypatch.setenv("BUILD_SHA", "abc123")
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        monkeypatch.delenv("ADMIN_IPS", raising=False)

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get("/api/v1/capabilities")

        assert response.status_code == 200
        assert "build" not in response.json()

    @pytest.mark.asyncio
    async def test_a_listed_address_is_told_which_build_it_is_talking_to(
        self, capabilities_client, monkeypatch
    ):
        monkeypatch.setenv("ADMIN_IPS", "203.0.113.7")
        monkeypatch.setenv("BUILD_SHA", "abc123")
        monkeypatch.setenv("BUILD_AT", "2026-11-11T02:00:00Z")
        monkeypatch.setenv("DEPLOY_RUN_ID", "4242")
        monkeypatch.setenv("BUILD_REPO", "someone/some-repo")

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get(
                "/api/v1/capabilities", headers={"x-forwarded-for": "203.0.113.7"}
            )

        assert response.status_code == 200
        build = response.json()["build"]
        assert build["sha"] == "abc123"
        assert build["built_at"] == "11.11.2026 02:00"
        assert build["deploy_run_id"] == "4242"
        assert build["commit_url"].endswith("/some-repo/commit/abc123")
        assert build["deploy_url"].endswith("/some-repo/actions/runs/4242")

    @pytest.mark.asyncio
    async def test_an_address_that_is_not_on_the_list_is_told_nothing(
        self, capabilities_client, monkeypatch
    ):
        monkeypatch.setenv("ADMIN_IPS", "203.0.113.7")
        monkeypatch.setenv("BUILD_SHA", "abc123")

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get(
                "/api/v1/capabilities", headers={"x-forwarded-for": "198.51.100.4"}
            )

        assert response.status_code == 200
        assert "build" not in response.json()

    @pytest.mark.asyncio
    async def test_a_privileged_caller_without_a_build_is_told_no_build(
        self, capabilities_client, monkeypatch
    ):
        # The list is there, the deployment does not say which build it runs:
        # there is nothing to show, and nothing broken.
        monkeypatch.setenv("ADMIN_IPS", "203.0.113.7")
        for name in ("BUILD_SHA", "BUILD_AT", "DEPLOY_RUN_ID"):
            monkeypatch.delenv(name, raising=False)

        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get(
                "/api/v1/capabilities", headers={"x-forwarded-for": "203.0.113.7"}
            )

        assert response.status_code == 200
        assert "build" not in response.json()

    @pytest.mark.asyncio
    async def test_an_unusable_token_does_not_break_the_endpoint(self, capabilities_client):
        # The endpoint is public and the landing page asks it on every visit.
        # A stale cookie must not turn it into a 401.
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            response = await capabilities_client.get(
                "/api/v1/capabilities", cookies={"access_token": "not-a-token"}
            )

        assert response.status_code == 200

    def test_the_builder_leaves_the_build_out_when_there_is_none(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False)

        assert "build" not in result

    def test_the_builder_publishes_the_build_it_is_given(self):
        with patch.object(capabilities, "get_settings", return_value=_settings()):
            result = capabilities.build_capabilities(email_enabled=False, build={"sha": "abc123"})

        assert result["build"] == {"sha": "abc123"}
