"""The four demo flags, the catalogue numbers and the outbound click.

The demo was one flag for four things. These tests pin what each flag now
means, so the split cannot quietly change the behaviour of a deployment that
set DEMO_MODE and nothing else.
"""

import os
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import auth as auth_deps
from api.routers import analytics_outbound, catalogue
from config.settings import AppSettings, _demo_env_flag
from db.database import get_db

FLAG_ENV_VARS = (
    "DEMO_MODE",
    "DEMO_DATA_MODE",
    "DEMO_LLM_MODE",
    "DEMO_API_KEY_BYPASS",
    "DEMO_USER_BYPASS",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """No demo flag in the environment unless a test says so."""
    for name in FLAG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def settings_with_env(env: dict[str, str]) -> AppSettings:
    """Settings built from an environment."""
    for name in FLAG_ENV_VARS:
        os.environ.pop(name, None)
    os.environ.update(env)
    try:
        return AppSettings()
    finally:
        for name in FLAG_ENV_VARS:
            os.environ.pop(name, None)


class TestDemoFlags:
    def test_without_any_flag_everything_is_off(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = AppSettings()
        assert settings.demo_data_mode is False
        assert settings.demo_llm_mode is False
        assert settings.demo_api_key_bypass is False
        assert settings.demo_user_bypass is False

    def test_demo_mode_carries_all_four(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("DEMO_MODE", "true")
        settings = AppSettings()
        assert settings.demo_data_mode is True
        assert settings.demo_llm_mode is True
        assert settings.demo_api_key_bypass is True
        assert settings.demo_user_bypass is True

    def test_one_flag_can_leave_the_others_alone(self, clean_env: pytest.MonkeyPatch) -> None:
        """The point of the split: a real model, a real catalogue, a real sign-in."""
        clean_env.setenv("DEMO_MODE", "true")
        clean_env.setenv("DEMO_LLM_MODE", "false")
        clean_env.setenv("DEMO_USER_BYPASS", "false")
        settings = AppSettings()
        assert settings.demo_data_mode is True
        assert settings.demo_api_key_bypass is True
        assert settings.demo_llm_mode is False
        assert settings.demo_user_bypass is False

    def test_the_helper_reads_the_own_flag_first(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("DEMO_MODE", "true")
        clean_env.setenv("DEMO_DATA_MODE", "false")
        assert _demo_env_flag("DEMO_DATA_MODE") is False
        assert _demo_env_flag("DEMO_LLM_MODE") is True


class TestTheMockFollowsTheLlmFlag:
    """The mock answer belongs to the LLM flag alone.

    The demo runs with DEMO_MODE=true - the seeded catalogue and the
    API-key bypass - and DEMO_LLM_MODE=false, so a real model answers.
    The factory that builds the model read DEMO_MODE directly, so the mock
    won and the deployment answered every question with the canned text.
    """

    @staticmethod
    def _stub_provider(monkeypatch: pytest.MonkeyPatch) -> None:
        from types import SimpleNamespace

        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        class StubProvider:
            def list_models(self):
                return [SimpleNamespace(id="stub-model")]

            def create_model(self, model_id, **kwargs):
                return FakeListChatModel(responses=["stub"])

        monkeypatch.setattr(
            "api.dependencies.ModelProviderFactory.get_provider",
            staticmethod(lambda provider_name, *args, **kwargs: StubProvider()),
        )

    def test_the_real_provider_wins_when_the_llm_flag_is_off(
        self, clean_env: pytest.MonkeyPatch, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from api import dependencies

        self._stub_provider(monkeypatch)
        monkeypatch.setattr(dependencies.settings, "demo_llm_mode", False)
        dependencies._create_llm_with_resolved_model_id.cache_clear()
        try:
            llm, model_id = dependencies._create_llm_with_resolved_model_id("stub", None)
        finally:
            dependencies._create_llm_with_resolved_model_id.cache_clear()

        assert model_id == "stub-model"
        assert "Mock" not in type(llm).__name__

    def test_the_mock_answers_when_the_llm_flag_is_on(
        self, clean_env: pytest.MonkeyPatch, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from api import dependencies

        self._stub_provider(monkeypatch)
        monkeypatch.setattr(dependencies.settings, "demo_llm_mode", True)
        dependencies._create_llm_with_resolved_model_id.cache_clear()
        try:
            llm, model_id = dependencies._create_llm_with_resolved_model_id("stub", None)
        finally:
            dependencies._create_llm_with_resolved_model_id.cache_clear()

        assert model_id == "demo-mock"
        assert "Mock" in type(llm).__name__


class TestTokenPriority:
    @pytest.mark.asyncio
    async def test_a_real_token_beats_the_demo_user(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A visitor who signed in is that account, even on a demo deployment."""

        class _SignedInUser:
            id = "user-123"
            email = "signed-in@example.com"

        signed_in = _SignedInUser()

        async def fake_extract_token(*args, **kwargs):
            return "a-real-token"

        async def fake_user_from_token(token, session):
            assert token == "a-real-token"
            return signed_in, "a-real-token"

        monkeypatch.setattr(auth_deps, "_extract_token", fake_extract_token)
        monkeypatch.setattr(auth_deps, "_get_user_from_token", fake_user_from_token)
        monkeypatch.setattr(auth_deps, "_get_demo_user", lambda: "the-demo-user")

        from config.settings import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "demo_user_bypass", True, raising=False)

        class _Request:
            headers: dict[str, str] = {}

        user = await auth_deps.get_current_user(
            request=_Request(),  # type: ignore[arg-type]
            access_token=None,
            credentials=None,
            session=AsyncMock(),
        )

        assert user is signed_in

    @pytest.mark.asyncio
    async def test_without_a_token_the_demo_user_answers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_extract_token(*args, **kwargs):
            return None

        monkeypatch.setattr(auth_deps, "_extract_token", fake_extract_token)
        monkeypatch.setattr(auth_deps, "_get_demo_user", lambda: "the-demo-user")

        from config.settings import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "demo_user_bypass", True, raising=False)

        class _Request:
            headers: dict[str, str] = {}

        user = await auth_deps.get_current_user(
            request=_Request(),  # type: ignore[arg-type]
            access_token=None,
            credentials=None,
            session=AsyncMock(),
        )

        assert user == "the-demo-user"


class TestCatalogueStats:
    @pytest.mark.asyncio
    async def test_the_shape_of_the_answer(self, db_session: AsyncSession) -> None:
        """An empty catalogue answers with zeros, not with an error."""
        test_app = FastAPI()
        test_app.include_router(catalogue.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        test_app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/catalogue/stats")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"total", "agents", "cities", "currencies"}
        assert payload["total"] >= 0
        assert payload["agents"] >= 0
        assert isinstance(payload["cities"], list)
        assert isinstance(payload["currencies"], list)


class TestOutboundClick:
    @pytest.mark.asyncio
    async def test_the_click_is_recorded(self, db_session: AsyncSession) -> None:
        test_app = FastAPI()
        test_app.include_router(analytics_outbound.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        test_app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analytics/outbound",
                json={
                    "target": "propvector",
                    "slot": "exit_card",
                    "campaign": "propvector",
                    "visitor_id": "test-visitor",
                },
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_the_click_is_bounded(self, db_session: AsyncSession) -> None:
        """An unbounded string is not accepted."""
        test_app = FastAPI()
        test_app.include_router(analytics_outbound.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        test_app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analytics/outbound",
                json={"target": "x" * 5000},
            )

        assert response.status_code == 422


class TestConsentAtRegistration:
    @pytest.mark.asyncio
    async def test_the_moment_of_the_agreement_is_recorded(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A visitor who agreed to the processing of their data says so, and the moment is kept."""
        from api.routers import auth_jwt
        from db.user_repos import UserRepository

        monkeypatch.setattr(
            auth_jwt.get_settings(), "auth_registration_enabled", True, raising=False
        )
        monkeypatch.setattr(
            auth_jwt.get_settings(), "auth_email_verification_required", False, raising=False
        )

        test_app = FastAPI()
        test_app.include_router(auth_jwt.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        test_app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "consented@example.com",
                    "password": "AStrong-Password-42",  # pragma: allowlist secret
                    "consent_given": True,
                },
            )

        assert response.status_code == 201, response.text

        user = await UserRepository(db_session).get_by_email("consented@example.com")
        assert user is not None
        assert user.gdpr_consent_at is not None
