"""The identity that reaches a preference is the one the request proved.

Task #156. A browser may put any address in ``X-User-Email`` - the web app
reads it from ``localStorage`` - so the header is an assertion, not an
identity. These tests are the guard for the rule:

- a request that proves an identity gets that account's preferences;
- a request that proves nothing gets the deployment default;
- the header never selects another account, in either direction.
"""

import types
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request

import api.dependencies as deps
from api.dependencies import get_vector_store
from api.deps.auth import get_proven_user_email
from api.main import app
from config.settings import get_settings

client = TestClient(app)


@contextmanager
def _proven_identity(email):
    """The identity the request proves. None is an anonymous request."""
    previous = app.dependency_overrides.get(get_proven_user_email)
    app.dependency_overrides[get_proven_user_email] = lambda: email
    try:
        yield
    finally:
        # The override lives on the shared application: what was there
        # before this request goes back, or nothing does.
        if previous is None:
            app.dependency_overrides.pop(get_proven_user_email, None)
        else:
            app.dependency_overrides[get_proven_user_email] = previous


class _FakeProvider:
    """A provider that records the model it was asked to create."""

    def __init__(self):
        self.created = []

    def list_models(self):
        return [types.SimpleNamespace(id="default-a"), types.SimpleNamespace(id="victim-b")]

    def create_model(self, model_id, temperature, max_tokens, **kwargs):
        self.created.append({"model_id": model_id})
        return types.SimpleNamespace(model_id=model_id)


class _FakeStore:
    def get_retriever(self):
        return object()


class _FakeAgent:
    def process_query(self, message):
        return {"answer": "ok", "source_documents": []}


def _ask_chat(provider, headers, identity):
    """One chat request, with the identity the request proves."""
    with (
        patch("api.dependencies.ModelProviderFactory.get_provider", lambda *a, **k: provider),
        patch("api.routers.chat.create_hybrid_agent", lambda **k: _FakeAgent()),
    ):
        app.dependency_overrides[get_vector_store] = lambda: _FakeStore()
        try:
            with _proven_identity(identity):
                return client.post(
                    "/api/v1/chat",
                    json={"message": "hello", "stream": False},
                    headers=headers,
                )
        finally:
            app.dependency_overrides = {}


def test_a_header_cannot_select_another_accounts_preference(tmp_path):
    """The header names somebody else. Their preference is not applied."""
    from models.user_model_preferences import UserModelPreferencesManager

    manager = UserModelPreferencesManager(storage_path=str(tmp_path))
    manager.update_preferences(
        "victim@example.com", preferred_provider="openai", preferred_model="victim-b"
    )

    asked_for = []
    original = manager.get_preferences

    def _record(email):
        asked_for.append(email)
        return original(email)

    manager.get_preferences = _record

    provider = _FakeProvider()
    key = get_settings().api_access_key

    with patch("models.user_model_preferences.MODEL_PREFS_MANAGER", manager):
        response = _ask_chat(
            provider,
            {"X-API-Key": key, "X-User-Email": "victim@example.com"},
            "attacker@example.com",
        )

    assert response.status_code == 200
    assert provider.created
    # The victim's model was never created, and their store was never read.
    assert provider.created[0]["model_id"] != "victim-b"
    assert "victim@example.com" not in asked_for


def test_the_proven_identity_gets_its_own_preference(tmp_path):
    """The mirror case: the header agrees with the token, and it applies."""
    from models.user_model_preferences import UserModelPreferencesManager

    manager = UserModelPreferencesManager(storage_path=str(tmp_path))
    manager.update_preferences(
        "owner@example.com", preferred_provider="openai", preferred_model="victim-b"
    )

    provider = _FakeProvider()
    key = get_settings().api_access_key

    with patch("models.user_model_preferences.MODEL_PREFS_MANAGER", manager):
        response = _ask_chat(
            provider,
            {"X-API-Key": key, "X-User-Email": "owner@example.com"},
            "owner@example.com",
        )

    assert response.status_code == 200
    assert provider.created and provider.created[0]["model_id"] == "victim-b"


def test_an_anonymous_request_gets_the_deployment_default(tmp_path):
    """No token, a header naming somebody: the default, not their model."""
    from models.user_model_preferences import UserModelPreferencesManager

    manager = UserModelPreferencesManager(storage_path=str(tmp_path))
    manager.update_preferences(
        "victim@example.com", preferred_provider="openai", preferred_model="victim-b"
    )

    asked_for = []
    original = manager.get_preferences

    def _record(email):
        asked_for.append(email)
        return original(email)

    manager.get_preferences = _record

    provider = _FakeProvider()
    key = get_settings().api_access_key

    with patch("models.user_model_preferences.MODEL_PREFS_MANAGER", manager):
        response = _ask_chat(
            provider,
            {"X-API-Key": key, "X-User-Email": "victim@example.com"},
            None,
        )

    assert response.status_code == 200
    assert provider.created
    assert provider.created[0]["model_id"] != "victim-b"
    assert "victim@example.com" not in asked_for


def test_an_anonymous_request_is_still_answered(tmp_path):
    """The public route keeps answering: no identity is not an error."""
    from models.user_model_preferences import UserModelPreferencesManager

    manager = UserModelPreferencesManager(storage_path=str(tmp_path))
    provider = _FakeProvider()
    key = get_settings().api_access_key

    with patch("models.user_model_preferences.MODEL_PREFS_MANAGER", manager):
        response = _ask_chat(provider, {"X-API-Key": key}, None)

    assert response.status_code == 200


async def test_the_resolver_reads_the_row_behind_the_token():
    """The resolver itself takes the address from the user, not a header."""
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    user = types.SimpleNamespace(email="owner@example.com")

    assert await get_proven_user_email(request, user) == "owner@example.com"
    # The audit middleware reads the actor from here.
    assert request.state.user_email == "owner@example.com"


async def test_the_resolver_answers_nothing_for_an_anonymous_request():
    """No user, no identity - and nothing is written to the request."""
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})

    assert await get_proven_user_email(request, None) is None
    assert not hasattr(request.state, "user_email")


async def test_the_task_preference_is_read_for_the_proven_identity(monkeypatch):
    """The per-task preference is looked up with the proven address."""
    from models.user_model_preferences import UserModelPreferencesManager

    provider = _FakeProvider()
    monkeypatch.setattr(deps.ModelProviderFactory, "get_provider", lambda *args, **kwargs: provider)

    class _Session:
        """A session that answers the user lookup with one id."""

        def __init__(self):
            self.queries = []

        async def execute(self, query):
            self.queries.append(query)
            return types.SimpleNamespace(scalar_one_or_none=lambda: "user-1")

    class _Preference:
        is_active = True
        provider = "openai"
        model_name = "task-b"

    class _Service:
        def __init__(self, session):
            self.session = session

        async def get_preference_by_task(self, user_id, task_type):
            assert user_id == "user-1"
            assert task_type == "chat"
            return _Preference()

    session = _Session()
    monkeypatch.setattr(deps, "ModelPreferenceService", _Service)

    with patch.object(
        deps.user_model_preferences,
        "MODEL_PREFS_MANAGER",
        UserModelPreferencesManager(storage_path=""),
    ):
        llm = await deps.get_llm_for_task("chat", proven_email="owner@example.com", session=session)

    assert session.queries, "the user lookup never ran"
    assert provider.created and provider.created[0]["model_id"] == "task-b"
    assert getattr(llm, "model_id", None) == "task-b"
