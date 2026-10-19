"""Tests for api.routers.settings module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routers import settings as settings_mod

_test_app = FastAPI()
_test_app.include_router(settings_mod.router)


def _make_user(user_id="user-1", email="test@test.com"):
    user = MagicMock()
    user.id = user_id
    user.email = email
    return user


def _make_prefs(**overrides):
    defaults = dict(
        price_alerts_enabled=True,
        new_listings_enabled=True,
        saved_search_enabled=True,
        market_updates_enabled=True,
        alert_frequency="instant",
        email_enabled=True,
        push_enabled=False,
        in_app_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        price_drop_threshold=5.0,
        daily_digest_time="09:00",
        weekly_digest_day="monday",
        expert_mode=False,
        marketing_emails=False,
        unsubscribe_token="tok-123",
        unsubscribed_at=None,
        unsubscribed_types=[],
    )
    defaults.update(overrides)
    prefs = MagicMock()
    for k, v in defaults.items():
        setattr(prefs, k, v)
    return prefs


class TestResolveUserEmail:
    def test_from_query(self):
        assert settings_mod._resolve_user_email("a@b.com", None) == "a@b.com"

    def test_from_header(self):
        assert settings_mod._resolve_user_email(None, "a@b.com") == "a@b.com"

    def test_query_priority(self):
        assert settings_mod._resolve_user_email("query@b.com", "header@b.com") == "query@b.com"

    def test_header_fallback(self):
        assert settings_mod._resolve_user_email(None, "header@b.com") == "header@b.com"

    def test_missing_raises_400(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            settings_mod._resolve_user_email(None, None)
        assert exc_info.value.status_code == 400

    def test_whitespace_stripped(self):
        assert settings_mod._resolve_user_email("  a@b.com  ", None) == "a@b.com"


class TestGetNotificationSettings:
    @pytest.mark.asyncio
    async def test_get_settings_success(self):
        user = _make_user()
        prefs = _make_prefs()
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.UserRepository") as mock_user_repo_cls,
            patch("api.routers.settings.NotificationPreferenceRepository") as mock_prefs_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_prefs_repo = MagicMock()
            mock_prefs_repo.get_or_create = AsyncMock(return_value=prefs)
            mock_prefs_repo_cls.return_value = mock_prefs_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/notifications?user_email=test@test.com")
                assert resp.status_code == 200
                data = resp.json()
                assert data["email_enabled"] is True
                assert data["alert_frequency"] == "instant"

    @pytest.mark.asyncio
    async def test_get_settings_user_not_found(self):
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.UserRepository") as mock_user_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=None)
            mock_user_repo_cls.return_value = mock_user_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/notifications?user_email=nobody@test.com")
                assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_settings_via_header(self):
        user = _make_user()
        prefs = _make_prefs()
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.UserRepository") as mock_user_repo_cls,
            patch("api.routers.settings.NotificationPreferenceRepository") as mock_prefs_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_prefs_repo = MagicMock()
            mock_prefs_repo.get_or_create = AsyncMock(return_value=prefs)
            mock_prefs_repo_cls.return_value = mock_prefs_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get(
                    "/settings/notifications",
                    headers={"X-User-Email": "test@test.com"},
                )
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_settings_no_email_400(self):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/settings/notifications")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_settings_internal_error(self):
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.UserRepository") as mock_user_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_email = AsyncMock(side_effect=RuntimeError("DB error"))
            mock_user_repo_cls.return_value = mock_user_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/notifications?user_email=test@test.com")
                assert resp.status_code == 500


class TestUpdateNotificationSettings:
    @pytest.mark.asyncio
    async def test_update_settings_success(self):
        user = _make_user()
        prefs = _make_prefs()
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.UserRepository") as mock_user_repo_cls,
            patch("api.routers.settings.NotificationPreferenceRepository") as mock_prefs_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_prefs_repo = MagicMock()
            mock_prefs_repo.get_or_create = AsyncMock(return_value=prefs)
            mock_prefs_repo.update = AsyncMock()
            mock_prefs_repo_cls.return_value = mock_prefs_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.put(
                    "/settings/notifications?user_email=test@test.com",
                    json={"email_enabled": False},
                )
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_settings_user_not_found(self):
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.UserRepository") as mock_user_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=None)
            mock_user_repo_cls.return_value = mock_user_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.put(
                    "/settings/notifications?user_email=nobody@test.com",
                    json={"email_enabled": True},
                )
                assert resp.status_code == 404


class TestSendNotificationPreview:
    @pytest.mark.asyncio
    async def test_preview_success(self):
        user = _make_user()
        prefs = _make_prefs(email_enabled=True)
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.UserRepository") as mock_user_repo_cls,
            patch("api.routers.settings.NotificationPreferenceRepository") as mock_prefs_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_prefs_repo = MagicMock()
            mock_prefs_repo.get_or_create = AsyncMock(return_value=prefs)
            mock_prefs_repo_cls.return_value = mock_prefs_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/settings/notifications/preview?user_email=test@test.com",
                    json={"channel": "email", "notification_type": "price_alert"},
                )
                assert resp.status_code == 200
                assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_preview_disabled_channel(self):
        user = _make_user()
        prefs = _make_prefs(push_enabled=False)
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.UserRepository") as mock_user_repo_cls,
            patch("api.routers.settings.NotificationPreferenceRepository") as mock_prefs_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_user_repo

            mock_prefs_repo = MagicMock()
            mock_prefs_repo.get_or_create = AsyncMock(return_value=prefs)
            mock_prefs_repo_cls.return_value = mock_prefs_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/settings/notifications/preview?user_email=test@test.com",
                    json={"channel": "push", "notification_type": "price_alert"},
                )
                assert resp.status_code == 200
                assert resp.json()["success"] is False


class TestUnsubscribeByToken:
    @pytest.mark.asyncio
    async def test_unsubscribe_all(self):
        prefs = _make_prefs()
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.NotificationPreferenceRepository") as mock_prefs_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_prefs_repo = MagicMock()
            mock_prefs_repo.get_by_unsubscribe_token = AsyncMock(return_value=prefs)
            mock_prefs_repo.unsubscribe_all = AsyncMock()
            mock_prefs_repo_cls.return_value = mock_prefs_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post("/settings/notifications/unsubscribe/tok-123")
                assert resp.status_code == 200
                assert resp.json()["unsubscribed_all"] is True

    @pytest.mark.asyncio
    async def test_unsubscribe_specific_type(self):
        prefs = _make_prefs()
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.NotificationPreferenceRepository") as mock_prefs_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_prefs_repo = MagicMock()
            mock_prefs_repo.get_by_unsubscribe_token = AsyncMock(return_value=prefs)
            mock_prefs_repo.unsubscribe_type = AsyncMock()
            mock_prefs_repo_cls.return_value = mock_prefs_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/settings/notifications/unsubscribe/tok-123?notification_type=marketing"
                )
                assert resp.status_code == 200
                assert resp.json()["unsubscribed_type"] == "marketing"

    @pytest.mark.asyncio
    async def test_unsubscribe_invalid_token(self):
        with (
            patch("api.routers.settings.get_db_context") as mock_db_ctx,
            patch("api.routers.settings.NotificationPreferenceRepository") as mock_prefs_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_prefs_repo = MagicMock()
            mock_prefs_repo.get_by_unsubscribe_token = AsyncMock(return_value=None)
            mock_prefs_repo_cls.return_value = mock_prefs_repo

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post("/settings/notifications/unsubscribe/bad-token")
                assert resp.status_code == 404


class TestListModelCatalog:
    @pytest.mark.asyncio
    async def test_list_catalog(self):
        mock_provider = MagicMock()
        mock_provider.name = "openai"
        mock_provider.display_name = "OpenAI"
        mock_provider.is_local = False
        mock_provider.requires_api_key = True

        mock_model_info = MagicMock()
        mock_model_info.id = "gpt-4"
        mock_model_info.display_name = "GPT-4"
        mock_model_info.provider_name = "openai"
        mock_model_info.context_window = 8192
        mock_model_info.pricing = MagicMock(
            input_price_per_1m=30.0,
            output_price_per_1m=60.0,
            currency="USD",
        )
        mock_model_info.capabilities = []
        mock_model_info.description = "Test model"
        mock_model_info.recommended_for = ["chat"]
        mock_provider.list_models.return_value = [mock_model_info]

        with patch("api.routers.settings.ModelProviderFactory") as mock_factory:
            mock_factory.list_providers.return_value = ["openai"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/models")
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 1
                assert data[0]["name"] == "openai"
                assert len(data[0]["models"]) == 1

    @pytest.mark.asyncio
    async def test_list_catalog_local_provider(self):
        mock_provider = MagicMock()
        mock_provider.name = "ollama"
        mock_provider.display_name = "Ollama"
        mock_provider.is_local = True
        mock_provider.requires_api_key = False
        mock_provider.validate_connection.return_value = (True, None)
        mock_provider.list_available_models.return_value = ["llama3"]
        mock_provider.list_models.return_value = []

        with patch("api.routers.settings.ModelProviderFactory") as mock_factory:
            mock_factory.list_providers.return_value = ["ollama"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/models")
                assert resp.status_code == 200
                data = resp.json()
                assert data[0]["runtime_available"] is True
                assert data[0]["available_models"] == ["llama3"]

    @pytest.mark.asyncio
    async def test_list_catalog_no_pricing(self):
        mock_provider = MagicMock()
        mock_provider.name = "test"
        mock_provider.display_name = "Test"
        mock_provider.is_local = False
        mock_provider.requires_api_key = False

        mock_model_info = MagicMock()
        mock_model_info.id = "m1"
        mock_model_info.display_name = "M1"
        mock_model_info.provider_name = "test"
        mock_model_info.context_window = 4096
        mock_model_info.pricing = None
        mock_model_info.capabilities = []
        mock_model_info.description = ""
        mock_model_info.recommended_for = []
        mock_provider.list_models.return_value = [mock_model_info]

        with patch("api.routers.settings.ModelProviderFactory") as mock_factory:
            mock_factory.list_providers.return_value = ["test"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/models")
                assert resp.status_code == 200


class TestTestRuntime:
    @pytest.mark.asyncio
    async def test_runtime_success(self):
        mock_provider = MagicMock()
        mock_provider.is_local = True
        mock_provider.validate_connection.return_value = (True, None)
        mock_provider.list_available_models.return_value = ["model-1"]

        with patch("api.routers.settings.ModelProviderFactory") as mock_factory:
            mock_factory.list_providers.return_value = ["ollama"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/test-runtime?provider=ollama")
                assert resp.status_code == 200
                assert resp.json()["runtime_available"] is True

    @pytest.mark.asyncio
    async def test_runtime_unknown_provider(self):
        with patch("api.routers.settings.ModelProviderFactory") as mock_factory:
            mock_factory.list_providers.return_value = ["openai"]

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/test-runtime?provider=unknown")
                assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_runtime_accepts_remote_provider(self):
        """Phase D.6 (2026-10-20): remote providers are now probeable
        through ``/settings/test-runtime``. Pre-D.6 this test asserted
        the endpoint rejected non-local providers with HTTP 400; the
        contract is now "accept any provider and return the
        ``validate_connection`` verdict"."""
        mock_provider = MagicMock()
        mock_provider.is_local = False
        mock_provider.validate_connection.return_value = (True, None)
        mock_provider.list_available_models.return_value = None

        with patch("api.routers.settings.ModelProviderFactory") as mock_factory:
            mock_factory.list_providers.return_value = ["openai"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/test-runtime?provider=openai")
                assert resp.status_code == 200
                body = resp.json()
                assert body["provider"] == "openai"
                assert body["is_local"] is False
                assert body["runtime_available"] is True

    @pytest.mark.asyncio
    async def test_runtime_connection_failure(self):
        mock_provider = MagicMock()
        mock_provider.is_local = True
        mock_provider.validate_connection.return_value = (False, "Connection refused")
        mock_provider.list_available_models.return_value = None

        with patch("api.routers.settings.ModelProviderFactory") as mock_factory:
            mock_factory.list_providers.return_value = ["ollama"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/test-runtime?provider=ollama")
                assert resp.status_code == 200
                assert resp.json()["runtime_available"] is False
                assert resp.json()["runtime_error"] == "Connection refused"


class TestModelPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences(self):
        mock_prefs = MagicMock()
        mock_prefs.preferred_provider = "openai"
        mock_prefs.preferred_model = "gpt-4"

        with patch("api.routers.settings.user_model_preferences") as mock_um:
            mock_um.MODEL_PREFS_MANAGER.get_preferences.return_value = mock_prefs

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/settings/model-preferences?user_email=test@test.com")
                assert resp.status_code == 200
                assert resp.json()["preferred_provider"] == "openai"

    @pytest.mark.asyncio
    async def test_update_preferences(self):
        mock_existing = MagicMock()
        mock_existing.preferred_provider = "openai"
        mock_existing.preferred_model = "gpt-4"

        mock_updated = MagicMock()
        mock_updated.preferred_provider = "anthropic"
        mock_updated.preferred_model = "claude-3"

        mock_provider = MagicMock()
        mock_model = MagicMock()
        mock_model.id = "claude-3"
        mock_provider.list_models.return_value = [mock_model]

        with (
            patch("api.routers.settings.user_model_preferences") as mock_um,
            patch("api.routers.settings.ModelProviderFactory") as mock_factory,
        ):
            mock_um.MODEL_PREFS_MANAGER.get_preferences.return_value = mock_existing
            mock_um.MODEL_PREFS_MANAGER.update_preferences.return_value = mock_updated
            mock_factory.list_providers.return_value = ["anthropic"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.put(
                    "/settings/model-preferences?user_email=test@test.com",
                    json={"preferred_provider": "anthropic", "preferred_model": "claude-3"},
                )
                assert resp.status_code == 200
                assert resp.json()["preferred_provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_update_clear_provider(self):
        mock_existing = MagicMock()
        mock_existing.preferred_provider = "openai"
        mock_existing.preferred_model = "gpt-4"

        mock_updated = MagicMock()
        mock_updated.preferred_provider = None
        mock_updated.preferred_model = None

        with patch("api.routers.settings.user_model_preferences") as mock_um:
            mock_um.MODEL_PREFS_MANAGER.get_preferences.return_value = mock_existing
            mock_um.MODEL_PREFS_MANAGER.update_preferences.return_value = mock_updated

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.put(
                    "/settings/model-preferences?user_email=test@test.com",
                    json={"preferred_provider": "", "preferred_model": ""},
                )
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_model_without_provider_400(self):
        mock_existing = MagicMock()
        mock_existing.preferred_provider = None
        mock_existing.preferred_model = None

        with patch("api.routers.settings.user_model_preferences") as mock_um:
            mock_um.MODEL_PREFS_MANAGER.get_preferences.return_value = mock_existing

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.put(
                    "/settings/model-preferences?user_email=test@test.com",
                    json={"preferred_model": "gpt-4"},
                )
                assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_unknown_provider_400(self):
        mock_existing = MagicMock()
        mock_existing.preferred_provider = None
        mock_existing.preferred_model = None

        with (
            patch("api.routers.settings.user_model_preferences") as mock_um,
            patch("api.routers.settings.ModelProviderFactory") as mock_factory,
        ):
            mock_um.MODEL_PREFS_MANAGER.get_preferences.return_value = mock_existing
            mock_factory.list_providers.return_value = ["openai"]

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.put(
                    "/settings/model-preferences?user_email=test@test.com",
                    json={"preferred_provider": "nonexistent"},
                )
                assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_unknown_model_400(self):
        mock_existing = MagicMock()
        mock_existing.preferred_provider = None
        mock_existing.preferred_model = None

        mock_provider = MagicMock()
        mock_provider.list_models.return_value = [MagicMock(id="gpt-4")]

        with (
            patch("api.routers.settings.user_model_preferences") as mock_um,
            patch("api.routers.settings.ModelProviderFactory") as mock_factory,
        ):
            mock_um.MODEL_PREFS_MANAGER.get_preferences.return_value = mock_existing
            mock_factory.list_providers.return_value = ["openai"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.put(
                    "/settings/model-preferences?user_email=test@test.com",
                    json={"preferred_provider": "openai", "preferred_model": "nonexistent"},
                )
                assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_keeps_existing_model(self):
        mock_existing = MagicMock()
        mock_existing.preferred_provider = "openai"
        mock_existing.preferred_model = "gpt-4"

        mock_updated = MagicMock()
        mock_updated.preferred_provider = "openai"
        mock_updated.preferred_model = "gpt-4"

        mock_provider = MagicMock()
        mock_model = MagicMock()
        mock_model.id = "gpt-4"
        mock_provider.list_models.return_value = [mock_model]

        with (
            patch("api.routers.settings.user_model_preferences") as mock_um,
            patch("api.routers.settings.ModelProviderFactory") as mock_factory,
        ):
            mock_um.MODEL_PREFS_MANAGER.get_preferences.return_value = mock_existing
            mock_um.MODEL_PREFS_MANAGER.update_preferences.return_value = mock_updated
            mock_factory.list_providers.return_value = ["openai"]
            mock_factory.get_provider.return_value = mock_provider

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.put(
                    "/settings/model-preferences?user_email=test@test.com",
                    json={"preferred_provider": "openai"},
                )
                assert resp.status_code == 200
