from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from config.settings import get_settings

client = TestClient(app)


@patch("api.routers.settings.ModelProviderFactory")
def test_settings_test_runtime_integration_returns_payload(mock_factory):
    settings = get_settings()
    key = settings.api_access_key

    mock_factory.list_providers.return_value = ["ollama"]

    provider = MagicMock()
    provider.is_local = True
    provider.validate_connection.return_value = (True, None)
    provider.list_available_models.return_value = ["llama3.3:8b"]
    mock_factory.get_provider.return_value = provider

    r = client.get("/api/v1/settings/test-runtime?provider=ollama", headers={"X-API-Key": key})
    assert r.status_code == 200
    assert r.json() == {
        "provider": "ollama",
        "is_local": True,
        "runtime_available": True,
        "available_models": ["llama3.3:8b"],
        "runtime_error": None,
    }


@patch("api.routers.settings.ModelProviderFactory")
def test_settings_test_runtime_integration_probes_remote_provider(mock_factory):
    """Phase D.6: any registered provider (local or remote) is now
    probeable. Pre-2026-10-19 this test asserted the endpoint
    rejected remote providers with HTTP 400; after D.6 the endpoint
    accepts them and returns the ``validate_connection()`` verdict.
    """
    settings = get_settings()
    key = settings.api_access_key

    mock_factory.list_providers.return_value = ["openai"]

    provider = MagicMock()
    provider.is_local = False
    provider.validate_connection.return_value = (True, None)
    provider.list_available_models.return_value = None
    mock_factory.get_provider.return_value = provider

    r = client.get("/api/v1/settings/test-runtime?provider=openai", headers={"X-API-Key": key})
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "openai"
    assert body["is_local"] is False
    assert body["runtime_available"] is True
    assert body["runtime_error"] is None


@patch("api.routers.settings.ModelProviderFactory")
def test_settings_test_runtime_integration_remote_validation_failure(mock_factory):
    """Phase D.6: when ``validate_connection()`` reports a failure on a
    remote provider (e.g. invalid API key), the endpoint returns HTTP
    200 with ``runtime_available=False`` and the failure message —
    same shape as the local-provider failure path."""
    settings = get_settings()
    key = settings.api_access_key

    mock_factory.list_providers.return_value = ["openai"]

    provider = MagicMock()
    provider.is_local = False
    provider.validate_connection.return_value = (False, "Invalid API key")
    provider.list_available_models.return_value = None
    mock_factory.get_provider.return_value = provider

    r = client.get("/api/v1/settings/test-runtime?provider=openai", headers={"X-API-Key": key})
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "openai"
    assert body["is_local"] is False
    assert body["runtime_available"] is False
    assert body["runtime_error"] == "Invalid API key"
