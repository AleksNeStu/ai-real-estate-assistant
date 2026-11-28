"""The identity that reaches a preference is the one the request proved.

Task #156, at the integration level. The unit suite replaces the resolver
with a stub, so it never runs the code that decides who the caller is. These
tests let the real resolver run: only ``get_optional_user`` - the step that
turns a token into a user row - is replaced, and everything above it is the
production path.

The contract on trial:

- a request that proves an identity gets that account's preferences;
- the header it carries never selects another account;
- a request that proves nothing gets the deployment default;
- the account-scoped helpers take the same proven identity.
"""

import types
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import api.dependencies as deps
from api.dependencies import get_vector_store
from api.deps.auth import get_optional_user, get_proven_user_email
from api.main import app
from config.settings import get_settings

client = TestClient(app)


@contextmanager
def _proven_account(email):
    """The request proves this account. The resolver above it stays real."""
    previous_user = app.dependency_overrides.get(get_optional_user)
    previous_resolver = app.dependency_overrides.get(get_proven_user_email)
    # A resolver stub left over from another module would answer instead of
    # the real one, and the real one is the thing under trial.
    app.dependency_overrides.pop(get_proven_user_email, None)
    app.dependency_overrides[get_optional_user] = lambda: types.SimpleNamespace(email=email)
    try:
        yield
    finally:
        for dependency, previous in (
            (get_optional_user, previous_user),
            (get_proven_user_email, previous_resolver),
        ):
            if previous is None:
                app.dependency_overrides.pop(dependency, None)
            else:
                app.dependency_overrides[dependency] = previous


class _FakeProvider:
    """A provider that records the model it was asked to create."""

    def __init__(self):
        self.created = []

    def list_models(self):
        return [types.SimpleNamespace(id="default-a"), types.SimpleNamespace(id="owner-b")]

    def create_model(self, model_id, temperature, max_tokens, **kwargs):
        self.created.append({"model_id": model_id})
        return types.SimpleNamespace(model_id=model_id)


class _FakeStore:
    def get_retriever(self):
        return object()

    def get_properties_by_ids(self, property_ids):
        from langchain_core.documents import Document

        return [
            Document(
                page_content="a",
                metadata={"id": "p1", "city": "Krakow", "price": 100000, "rooms": 2},
            )
        ]


class _FakeAgent:
    def process_query(self, message):
        return {"answer": "ok", "source_documents": []}


@pytest.fixture
def preferences(tmp_path):
    """A preference store that knows two accounts."""
    from models.user_model_preferences import UserModelPreferencesManager

    manager = UserModelPreferencesManager(storage_path=str(tmp_path))
    manager.update_preferences(
        "owner@example.com", preferred_provider="openai", preferred_model="owner-b"
    )
    manager.update_preferences(
        "victim@example.com", preferred_provider="openai", preferred_model="victim-b"
    )
    with patch("models.user_model_preferences.MODEL_PREFS_MANAGER", manager):
        yield manager


def test_a_proven_account_reads_its_own_preference(preferences):
    """The real resolver runs, and the account it proves gets the model."""
    provider = _FakeProvider()
    key = get_settings().api_access_key

    with (
        patch("api.dependencies.ModelProviderFactory.get_provider", lambda *a, **k: provider),
        patch("api.routers.chat.create_hybrid_agent", lambda **k: _FakeAgent()),
    ):
        app.dependency_overrides[get_vector_store] = lambda: _FakeStore()
        try:
            with _proven_account("owner@example.com"):
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "hello", "stream": False},
                    headers={"X-API-Key": key},
                )
        finally:
            app.dependency_overrides = {}

    assert response.status_code == 200
    assert provider.created and provider.created[0]["model_id"] == "owner-b"


def test_the_header_never_selects_another_account(preferences):
    """The header names somebody else. Their model is not created."""
    provider = _FakeProvider()
    key = get_settings().api_access_key

    with (
        patch("api.dependencies.ModelProviderFactory.get_provider", lambda *a, **k: provider),
        patch("api.routers.chat.create_hybrid_agent", lambda **k: _FakeAgent()),
    ):
        app.dependency_overrides[get_vector_store] = lambda: _FakeStore()
        try:
            with _proven_account("owner@example.com"):
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "hello", "stream": False},
                    headers={"X-API-Key": key, "X-User-Email": "victim@example.com"},
                )
        finally:
            app.dependency_overrides = {}

    assert response.status_code == 200
    assert provider.created
    assert provider.created[0]["model_id"] != "victim-b"


def test_the_listing_generator_reads_the_proven_identity(preferences):
    """The tools route resolves the model the same way."""
    provider = _FakeProvider()
    key = get_settings().api_access_key

    with patch("api.dependencies.ModelProviderFactory.get_provider", lambda *a, **k: provider):
        app.dependency_overrides[get_vector_store] = lambda: _FakeStore()
        try:
            with _proven_account("owner@example.com"):
                client.post(
                    "/api/v1/tools/generate-listing",
                    json={"property_id": "p1"},
                    headers={"X-API-Key": key, "X-User-Email": "victim@example.com"},
                )
        finally:
            app.dependency_overrides = {}

    assert provider.created, "the listing generator never resolved a model"
    assert provider.created[0]["model_id"] != "victim-b"


def test_the_rag_route_reads_the_proven_identity(preferences):
    """The RAG route resolves its model the same way."""
    provider = _FakeProvider()
    key = get_settings().api_access_key

    with patch("api.dependencies.ModelProviderFactory.get_provider", lambda *a, **k: provider):
        try:
            with _proven_account("owner@example.com"):
                client.post(
                    "/api/v1/rag/qa",
                    json={"question": "hello", "top_k": 3},
                    headers={"X-API-Key": key, "X-User-Email": "victim@example.com"},
                )
        finally:
            app.dependency_overrides = {}

    assert provider.created, "the RAG route never resolved a model"
    assert provider.created[0]["model_id"] != "victim-b"


class _Session:
    """A session that answers the user lookup with one id."""

    def __init__(self, user_id="user-1"):
        self.user_id = user_id
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        return types.SimpleNamespace(scalar_one_or_none=lambda: self.user_id)


class _Preference:
    is_active = True
    provider = "openai"
    model_name = "task-b"


class _Service:
    def __init__(self, session):
        self.session = session

    async def get_preference_by_task(self, user_id, task_type):
        return _Preference()


async def test_the_task_scoped_helper_uses_the_proven_identity(preferences, monkeypatch):
    """The per-task lookup runs on the proven address, and only on it."""
    provider = _FakeProvider()
    monkeypatch.setattr(deps.ModelProviderFactory, "get_provider", lambda *a, **k: provider)
    monkeypatch.setattr(deps, "ModelPreferenceService", _Service)

    session = _Session()
    llm = await deps.get_llm_for_task("chat", proven_email="owner@example.com", session=session)

    assert session.queries, "the user lookup never ran"
    assert provider.created and provider.created[0]["model_id"] == "task-b"
    assert getattr(llm, "model_id", None) == "task-b"


async def test_the_optional_task_scoped_helper_uses_the_proven_identity(preferences, monkeypatch):
    """The tolerant wrapper takes the same identity."""
    provider = _FakeProvider()
    monkeypatch.setattr(deps.ModelProviderFactory, "get_provider", lambda *a, **k: provider)
    monkeypatch.setattr(deps, "ModelPreferenceService", _Service)

    session = _Session()
    llm = await deps.get_optional_llm_for_task(
        "chat", proven_email="owner@example.com", session=session
    )

    assert session.queries, "the user lookup never ran"
    assert provider.created and provider.created[0]["model_id"] == "task-b"
    assert getattr(llm, "model_id", None) == "task-b"
