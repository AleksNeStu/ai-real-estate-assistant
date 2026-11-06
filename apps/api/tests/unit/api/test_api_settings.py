from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# Mock API Key
HEADERS = {"X-API-Key": "test-key", "X-User-Email": "u1@example.com"}
HEADERS_NO_USER = {"X-API-Key": "test-key"}


def _make_mock_prefs(**overrides):
    """Create a mock NotificationPreferenceDB-like object."""
    defaults = dict(
        price_alerts_enabled=True,
        new_listings_enabled=True,
        saved_search_enabled=True,
        market_updates_enabled=False,
        alert_frequency="weekly",
        email_enabled=True,
        push_enabled=False,
        in_app_enabled=True,
        quiet_hours_start=None,
        quiet_hours_end=None,
        price_drop_threshold=5.0,
        daily_digest_time="09:00",
        weekly_digest_day="monday",
        expert_mode=True,
        marketing_emails=False,
        unsubscribe_token="tok-123",
        unsubscribed_at=None,
        unsubscribed_types=None,
    )
    defaults.update(overrides)
    prefs = MagicMock()
    for k, v in defaults.items():
        setattr(prefs, k, v)
    return prefs


def _mock_db_context(mock_user, mock_prefs):
    """Build a mock get_db_context that yields a session with repos."""
    mock_session = AsyncMock()

    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)

    mock_prefs_repo = AsyncMock()
    mock_prefs_repo.get_or_create = AsyncMock(return_value=mock_prefs)
    mock_prefs_repo.update = AsyncMock(return_value=mock_prefs)

    @asynccontextmanager
    async def _ctx():
        # Patch repo constructors inside the context
        with (
            patch("api.routers.settings.UserRepository", return_value=mock_user_repo),
            patch(
                "api.routers.settings.NotificationPreferenceRepository",
                return_value=mock_prefs_repo,
            ),
        ):
            yield mock_session

    return _ctx, mock_user_repo, mock_prefs_repo


@patch("api.auth.get_settings")
def test_get_settings(mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_user = MagicMock()
    mock_user.id = "user-1"
    mock_prefs = _make_mock_prefs()

    ctx, _, _ = _mock_db_context(mock_user, mock_prefs)

    with patch("api.routers.settings.get_db_context", ctx):
        response = client.get("/api/v1/settings/notifications", headers=HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["alert_frequency"] == "weekly"
    assert data["expert_mode"] is True
    assert data["marketing_emails"] is False


@patch("api.auth.get_settings")
def test_update_settings(mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_user = MagicMock()
    mock_user.id = "user-1"
    mock_prefs = _make_mock_prefs()

    ctx, _, mock_prefs_repo = _mock_db_context(mock_user, mock_prefs)

    payload = {
        "alert_frequency": "daily",
        "expert_mode": True,
        "marketing_emails": True,
    }

    with patch("api.routers.settings.get_db_context", ctx):
        response = client.put("/api/v1/settings/notifications", json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert mock_prefs_repo.update.called


@patch("api.auth.get_settings")
def test_settings_query_user_email_overrides_header(mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_user = MagicMock()
    mock_user.id = "user-2"
    mock_prefs = _make_mock_prefs()

    ctx, mock_user_repo, _ = _mock_db_context(mock_user, mock_prefs)

    with patch("api.routers.settings.get_db_context", ctx):
        response = client.get(
            "/api/v1/settings/notifications?user_email=u2@example.com",
            headers=HEADERS,
        )

    assert response.status_code == 200
    mock_user_repo.get_by_email.assert_called_once_with("u2@example.com")


@patch("api.auth.get_settings")
def test_get_settings_missing_user_email_returns_400(mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    response = client.get("/api/v1/settings/notifications", headers=HEADERS_NO_USER)

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing user email"


@patch("api.auth.get_settings")
def test_update_settings_missing_user_email_returns_400(mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    response = client.put(
        "/api/v1/settings/notifications",
        json={
            "alert_frequency": "daily",
            "expert_mode": False,
            "marketing_emails": False,
        },
        headers=HEADERS_NO_USER,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing user email"


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_list_model_catalog(mock_get_settings, mock_factory):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["openai", "ollama"]

    openai_provider = MagicMock()
    openai_provider.name = "openai"
    openai_provider.display_name = "OpenAI"
    openai_provider.is_local = False
    openai_provider.requires_api_key = True

    cap_streaming = MagicMock()
    cap_streaming.value = "streaming"

    pricing = MagicMock()
    pricing.input_price_per_1m = 2.5
    pricing.output_price_per_1m = 10.0
    pricing.currency = "USD"

    openai_model = MagicMock()
    openai_model.id = "gpt-4o"
    openai_model.display_name = "GPT-4o"
    openai_model.provider_name = "OpenAI"
    openai_model.context_window = 128000
    openai_model.pricing = pricing
    openai_model.capabilities = [cap_streaming]
    openai_model.description = "desc"
    openai_model.recommended_for = ["general"]
    openai_provider.list_models.return_value = [openai_model]

    ollama_provider = MagicMock()
    ollama_provider.name = "ollama"
    ollama_provider.display_name = "Ollama"
    ollama_provider.is_local = True
    ollama_provider.requires_api_key = False

    ollama_model = MagicMock()
    ollama_model.id = "llama3.2:3b"
    ollama_model.display_name = "Llama 3.2 3B"
    ollama_model.provider_name = "Ollama"
    ollama_model.context_window = 128000
    ollama_model.pricing = None
    ollama_model.capabilities = []
    ollama_model.description = None
    ollama_model.recommended_for = []
    ollama_provider.list_models.return_value = [ollama_model]
    ollama_provider.list_available_models.return_value = ["llama3.2:3b"]
    ollama_provider.validate_connection.return_value = (True, None)

    def _get_provider(name):
        return openai_provider if name == "openai" else ollama_provider

    mock_factory.get_provider.side_effect = _get_provider

    response = client.get("/api/v1/settings/models", headers=HEADERS_NO_USER)
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "openai"
    assert data[0]["requires_api_key"] is True
    assert data[0]["is_local"] is False
    assert data[0]["models"][0]["id"] == "gpt-4o"
    assert data[0]["models"][0]["pricing"]["input_price_per_1m"] == 2.5
    assert "streaming" in data[0]["models"][0]["capabilities"]

    assert data[1]["name"] == "ollama"
    assert data[1]["requires_api_key"] is False
    assert data[1]["is_local"] is True
    assert data[1]["runtime_available"] is True
    assert data[1]["available_models"] == ["llama3.2:3b"]
    assert data[1]["runtime_error"] is None
    assert data[1]["models"][0]["pricing"] is None


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_list_model_catalog_includes_runtime_error_for_local_provider(
    mock_get_settings, mock_factory
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["ollama"]

    ollama_provider = MagicMock()
    ollama_provider.name = "ollama"
    ollama_provider.display_name = "Ollama"
    ollama_provider.is_local = True
    ollama_provider.requires_api_key = False
    ollama_provider.list_models.return_value = []
    ollama_provider.validate_connection.return_value = (False, "Could not connect to Ollama")

    mock_factory.get_provider.return_value = ollama_provider

    response = client.get("/api/v1/settings/models", headers=HEADERS_NO_USER)
    assert response.status_code == 200

    data = response.json()
    assert data == [
        {
            "name": "ollama",
            "display_name": "Ollama",
            "is_local": True,
            "requires_api_key": False,
            "models": [],
            "runtime_available": False,
            "available_models": [],
            "runtime_error": "Could not connect to Ollama",
        }
    ]


@patch("api.auth.get_settings")
def test_get_settings_returns_500_on_unhandled_error(mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    # get_db_context raises RuntimeError -> caught as 500
    @asynccontextmanager
    async def _failing_ctx():
        raise RuntimeError("boom")
        yield  # noqa: unreachable

    with patch("api.routers.settings.get_db_context", _failing_ctx):
        response = client.get("/api/v1/settings/notifications", headers=HEADERS)
    assert response.status_code == 500
    assert response.json()["detail"] == "boom"


@patch("api.auth.get_settings")
def test_update_settings_returns_500_on_unhandled_error(mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    @asynccontextmanager
    async def _failing_ctx():
        raise RuntimeError("boom")
        yield  # noqa: unreachable

    with patch("api.routers.settings.get_db_context", _failing_ctx):
        response = client.put(
            "/api/v1/settings/notifications",
            json={
                "alert_frequency": "daily",
                "expert_mode": False,
                "marketing_emails": False,
            },
            headers=HEADERS,
        )
    assert response.status_code == 500
    assert response.json()["detail"] == "boom"


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_list_model_catalog_returns_500_on_error(mock_get_settings, mock_factory):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings
    mock_factory.list_providers.side_effect = RuntimeError("boom")

    response = client.get("/api/v1/settings/models", headers=HEADERS_NO_USER)
    assert response.status_code == 500
    assert response.json()["detail"] == "boom"


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_test_runtime_unknown_provider_returns_400_unknown_value(mock_get_settings, mock_factory):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings
    mock_factory.list_providers.return_value = ["ollama"]

    response = client.get("/api/v1/settings/test-runtime?provider=nope", headers=HEADERS_NO_USER)
    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown provider: nope"


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_test_runtime_remote_provider_accepted_when_connection_valid(
    mock_get_settings, mock_factory
):
    """Phase D.6 (2026-10-20): remote providers are now probeable
    through ``/settings/test-runtime``. Pre-D.6 this test asserted the
    endpoint rejected remote providers with HTTP 400; the contract is
    now "accept any provider and return the ``validate_connection``
    verdict"."""
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings
    mock_factory.list_providers.return_value = ["openai"]

    provider = MagicMock()
    provider.is_local = False
    provider.validate_connection.return_value = (True, None)
    provider.list_available_models.return_value = None
    mock_factory.get_provider.return_value = provider

    response = client.get("/api/v1/settings/test-runtime?provider=openai", headers=HEADERS_NO_USER)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["is_local"] is False
    assert data["runtime_available"] is True
    assert data["runtime_error"] is None


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_test_runtime_returns_status_and_available_models(mock_get_settings, mock_factory):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings
    mock_factory.list_providers.return_value = ["ollama"]

    provider = MagicMock()
    provider.is_local = True
    provider.validate_connection.return_value = (True, None)
    provider.list_available_models.return_value = ["llama3.3:8b", "mistral:7b"]
    mock_factory.get_provider.return_value = provider

    response = client.get("/api/v1/settings/test-runtime?provider=ollama", headers=HEADERS_NO_USER)
    assert response.status_code == 200
    assert response.json() == {
        "provider": "ollama",
        "is_local": True,
        "runtime_available": True,
        "available_models": ["llama3.3:8b", "mistral:7b"],
        "runtime_error": None,
    }


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_test_runtime_unknown_provider_returns_400(mock_get_settings, mock_factory):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["ollama"]

    response = client.get("/api/v1/settings/test-runtime?provider=unknown", headers=HEADERS_NO_USER)
    assert response.status_code == 400
    assert "Unknown provider" in response.json()["detail"]


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_test_runtime_remote_provider_reports_validation_failure(mock_get_settings, mock_factory):
    """Phase D.6: when ``validate_connection()`` reports a failure on a
    remote provider (e.g. invalid API key), the endpoint returns HTTP
    200 with ``runtime_available=False`` and the failure message —
    same shape as the local-provider failure path."""
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["openai"]
    openai_provider = MagicMock()
    openai_provider.is_local = False
    openai_provider.validate_connection.return_value = (False, "Invalid API key")
    openai_provider.list_available_models.return_value = None
    mock_factory.get_provider.return_value = openai_provider

    response = client.get("/api/v1/settings/test-runtime?provider=openai", headers=HEADERS_NO_USER)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["is_local"] is False
    assert data["runtime_available"] is False
    assert data["runtime_error"] == "Invalid API key"


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_test_runtime_local_provider_returns_runtime_fields(mock_get_settings, mock_factory):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["ollama"]
    ollama_provider = MagicMock()
    ollama_provider.is_local = True
    ollama_provider.validate_connection.return_value = (True, None)
    ollama_provider.list_available_models.return_value = ["llama3.3:8b"]
    mock_factory.get_provider.return_value = ollama_provider

    response = client.get("/api/v1/settings/test-runtime?provider=ollama", headers=HEADERS_NO_USER)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "ollama"
    assert data["is_local"] is True
    assert data["runtime_available"] is True
    assert data["available_models"] == ["llama3.3:8b"]
    assert data["runtime_error"] is None


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.auth.get_settings")
def test_get_model_preferences(mock_get_settings, mock_model_prefs_manager):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_prefs = MagicMock()
    mock_prefs.preferred_provider = "openai"
    mock_prefs.preferred_model = "gpt-4o"
    mock_model_prefs_manager.get_preferences.return_value = mock_prefs

    response = client.get("/api/v1/settings/model-preferences", headers=HEADERS)
    assert response.status_code == 200
    mock_model_prefs_manager.get_preferences.assert_called_once_with("u1@example.com")
    data = response.json()
    assert data["preferred_provider"] == "openai"
    assert data["preferred_model"] == "gpt-4o"


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_update_model_preferences_validates_provider_and_model(
    mock_get_settings, mock_factory, mock_model_prefs_manager
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["openai"]
    provider = MagicMock()
    model = MagicMock()
    model.id = "gpt-4o"
    provider.list_models.return_value = [model]
    mock_factory.get_provider.return_value = provider

    existing = MagicMock()
    existing.preferred_provider = None
    existing.preferred_model = None
    mock_model_prefs_manager.get_preferences.return_value = existing

    updated = MagicMock()
    updated.preferred_provider = "openai"
    updated.preferred_model = "gpt-4o"
    mock_model_prefs_manager.update_preferences.return_value = updated

    response = client.put(
        "/api/v1/settings/model-preferences",
        json={"preferred_provider": "openai", "preferred_model": "gpt-4o"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["preferred_provider"] == "openai"
    assert response.json()["preferred_model"] == "gpt-4o"


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.auth.get_settings")
def test_update_model_preferences_requires_provider_when_setting_model(
    mock_get_settings, mock_model_prefs_manager
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    existing = MagicMock()
    existing.preferred_provider = None
    existing.preferred_model = None
    mock_model_prefs_manager.get_preferences.return_value = existing

    response = client.put(
        "/api/v1/settings/model-preferences",
        json={"preferred_model": "gpt-4o"},
        headers=HEADERS,
    )
    assert response.status_code == 400
    assert "preferred_provider is required" in response.json()["detail"]


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.auth.get_settings")
def test_get_model_preferences_missing_user_email_returns_400(
    mock_get_settings, mock_model_prefs_manager
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    response = client.get("/api/v1/settings/model-preferences", headers=HEADERS_NO_USER)
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing user email"
    assert not mock_model_prefs_manager.get_preferences.called


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.auth.get_settings")
def test_get_model_preferences_returns_400_on_value_error(
    mock_get_settings, mock_model_prefs_manager
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_model_prefs_manager.get_preferences.side_effect = ValueError("bad email")
    response = client.get("/api/v1/settings/model-preferences", headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["detail"] == "bad email"


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_update_model_preferences_rejects_unknown_provider(
    mock_get_settings, mock_factory, mock_model_prefs_manager
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["openai"]
    existing = MagicMock()
    existing.preferred_provider = None
    existing.preferred_model = None
    mock_model_prefs_manager.get_preferences.return_value = existing

    response = client.put(
        "/api/v1/settings/model-preferences",
        json={"preferred_provider": "anthropic"},
        headers=HEADERS,
    )
    assert response.status_code == 400
    assert "Unknown provider" in response.json()["detail"]


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_update_model_preferences_rejects_unknown_model_for_provider(
    mock_get_settings, mock_factory, mock_model_prefs_manager
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["openai"]
    provider = MagicMock()
    model = MagicMock()
    model.id = "gpt-4o"
    provider.list_models.return_value = [model]
    mock_factory.get_provider.return_value = provider

    existing = MagicMock()
    existing.preferred_provider = None
    existing.preferred_model = None
    mock_model_prefs_manager.get_preferences.return_value = existing

    response = client.put(
        "/api/v1/settings/model-preferences",
        json={"preferred_provider": "openai", "preferred_model": "not-a-model"},
        headers=HEADERS,
    )
    assert response.status_code == 400
    assert "Unknown model" in response.json()["detail"]


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_update_model_preferences_preserves_existing_model_when_provider_set_and_model_omitted(
    mock_get_settings, mock_factory, mock_model_prefs_manager
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["openai"]
    provider = MagicMock()
    model = MagicMock()
    model.id = "gpt-4o"
    provider.list_models.return_value = [model]
    mock_factory.get_provider.return_value = provider

    existing = MagicMock()
    existing.preferred_provider = "openai"
    existing.preferred_model = "gpt-4o"
    mock_model_prefs_manager.get_preferences.return_value = existing

    updated = MagicMock()
    updated.preferred_provider = "openai"
    updated.preferred_model = "gpt-4o"
    mock_model_prefs_manager.update_preferences.return_value = updated

    response = client.put(
        "/api/v1/settings/model-preferences",
        json={"preferred_provider": "openai"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["preferred_model"] == "gpt-4o"


@patch("api.routers.settings.user_model_preferences.MODEL_PREFS_MANAGER")
@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_update_model_preferences_clears_provider_and_model_on_empty_provider(
    mock_get_settings, mock_factory, mock_model_prefs_manager
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["openai"]

    existing = MagicMock()
    existing.preferred_provider = "openai"
    existing.preferred_model = "gpt-4o"
    mock_model_prefs_manager.get_preferences.return_value = existing

    updated = MagicMock()
    updated.preferred_provider = None
    updated.preferred_model = None
    mock_model_prefs_manager.update_preferences.return_value = updated

    response = client.put(
        "/api/v1/settings/model-preferences",
        json={"preferred_provider": ""},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["preferred_provider"] is None
    assert response.json()["preferred_model"] is None


@patch("api.routers.settings.ModelProviderFactory")
@patch("api.auth.get_settings")
def test_list_model_catalog_local_provider_runtime_unavailable_sets_flags(
    mock_get_settings, mock_factory
):
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings

    mock_factory.list_providers.return_value = ["ollama"]

    ollama_provider = MagicMock()
    ollama_provider.name = "ollama"
    ollama_provider.display_name = "Ollama"
    ollama_provider.is_local = True
    ollama_provider.requires_api_key = False
    ollama_provider.list_models.return_value = []
    ollama_provider.validate_connection.return_value = (False, "Could not connect to Ollama")
    mock_factory.get_provider.return_value = ollama_provider

    response = client.get("/api/v1/settings/models", headers=HEADERS_NO_USER)
    assert response.status_code == 200
    data = response.json()
    assert data[0]["runtime_available"] is False
    assert data[0]["available_models"] == []
