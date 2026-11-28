import types

import pytest
from fastapi import HTTPException

import api.dependencies as deps
from config.settings import settings
from models.provider_factory import ModelProviderFactory


class FakeProvider:
    def __init__(self, config=None):
        self.config = config or {}
        self._models = [
            types.SimpleNamespace(id="model-a"),
            types.SimpleNamespace(id="model-b"),
        ]
        self.created = []

    def list_models(self):
        return self._models

    def create_model(self, model_id, temperature, max_tokens, **kwargs):
        self.created.append(
            dict(model_id=model_id, temperature=temperature, max_tokens=max_tokens, kwargs=kwargs)
        )
        return types.SimpleNamespace(stream=True, model_id=model_id)


@pytest.fixture(autouse=True)
def _clear_factory_cache():
    from api.dependencies import clear_llm_cache

    clear_llm_cache()
    yield
    clear_llm_cache()


async def test_get_llm_uses_default_provider_and_first_model(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None
    fake = FakeProvider()
    monkeypatch.setattr(ModelProviderFactory, "_PROVIDERS", {"openai": lambda config=None: fake})
    monkeypatch.setattr(
        ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
    )
    llm = await deps.get_llm()
    assert getattr(llm, "model_id", None) == "model-a"
    assert fake.created and fake.created[0]["model_id"] == "model-a"
    assert "provider_name" not in fake.created[0]["kwargs"]


async def test_get_llm_raises_when_no_models(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None
    fake = FakeProvider()
    fake._models = []
    monkeypatch.setattr(
        ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
    )
    with pytest.raises(RuntimeError):
        _ = await deps.get_llm()


async def test_get_llm_uses_user_model_preferences(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None

    fake = FakeProvider()
    monkeypatch.setattr(
        ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
    )

    class _Prefs:
        preferred_provider = "openai"
        preferred_model = "model-b"

    class _Mgr:
        def get_preferences(self, user_email: str):
            assert user_email == "u1@example.com"
            return _Prefs()

    monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _Mgr())
    llm = await deps.get_llm(proven_email="u1@example.com")
    assert getattr(llm, "model_id", None) == "model-b"
    assert fake.created and fake.created[0]["model_id"] == "model-b"


async def test_get_llm_falls_back_when_preferred_model_fails(monkeypatch):
    settings.default_provider = "ollama"
    settings.default_model = "model-a"

    created: list[dict] = []

    class FailingProvider(FakeProvider):
        def create_model(self, model_id, temperature, max_tokens, **kwargs):
            raise RuntimeError("bad model")

    class WorkingProvider(FakeProvider):
        def create_model(self, model_id, temperature, max_tokens, **kwargs):
            created.append({"model_id": model_id})
            return types.SimpleNamespace(model_id=model_id)

    failing = FailingProvider()
    working = WorkingProvider()

    def _get_provider(name, config=None, use_cache=True):
        return failing if name == "openai" else working

    monkeypatch.setattr(ModelProviderFactory, "get_provider", _get_provider)

    class _Prefs:
        preferred_provider = "openai"
        preferred_model = "bad"

    class _Mgr:
        def get_preferences(self, user_email: str):
            return _Prefs()

    monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _Mgr())
    llm = await deps.get_llm(proven_email="u1@example.com")
    assert getattr(llm, "model_id", None) == "model-a"
    assert created and created[0]["model_id"] == "model-a"


async def test_get_llm_falls_back_to_ollama_when_primary_provider_fails_and_ollama_running(
    monkeypatch,
):
    settings.default_provider = "openai"
    settings.default_model = None
    settings.ollama_default_model = "llama3.2:3b"

    class PrimaryProvider(FakeProvider):
        def create_model(self, model_id, temperature, max_tokens, **kwargs):
            raise RuntimeError("primary down")

    class OllamaProvider(FakeProvider):
        def validate_connection(self):
            return True, None

    primary = PrimaryProvider()
    ollama = OllamaProvider()

    def _get_provider(name, config=None, use_cache=True):
        if name == "ollama":
            return ollama
        return primary

    monkeypatch.setattr(ModelProviderFactory, "get_provider", _get_provider)

    llm = await deps.get_llm()
    assert getattr(llm, "model_id", None) == "llama3.2:3b"
    assert ollama.created and ollama.created[0]["model_id"] == "llama3.2:3b"


def test_create_llm_with_resolved_model_id_uses_ollama_default_model_when_missing(monkeypatch):
    settings.default_temperature = 0.0
    settings.default_max_tokens = 4096
    settings.ollama_default_model = "llama3.2:3b"

    class OllamaProvider(FakeProvider):
        def list_models(self):
            raise AssertionError(
                "list_models should not be called when ollama_default_model is set"
            )

    ollama = OllamaProvider()
    monkeypatch.setattr(
        ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: ollama
    )

    llm, resolved_model = deps._create_llm_with_resolved_model_id("ollama", None)
    assert resolved_model == "llama3.2:3b"
    assert getattr(llm, "model_id", None) == "llama3.2:3b"


async def test_get_optional_llm_returns_none_on_error(monkeypatch):
    async def _fail(proven_email=None):
        raise RuntimeError("no llm")

    monkeypatch.setattr(deps, "get_llm", _fail)
    assert await deps.get_optional_llm() is None


async def test_get_optional_llm_returns_llm_when_available(monkeypatch):
    async def _ok(proven_email=None):
        return types.SimpleNamespace(model_id="m1")

    monkeypatch.setattr(deps, "get_llm", _ok)
    llm = await deps.get_optional_llm()
    assert getattr(llm, "model_id", None) == "m1"


def test_parse_rag_qa_request_uses_body_payload():
    payload = deps.RagQaRequest(question="q1", top_k=3, provider="openai", model="m1")
    out = deps.parse_rag_qa_request(payload=payload)
    assert out.question == "q1"
    assert out.top_k == 3
    assert out.provider == "openai"
    assert out.model == "m1"


def test_parse_rag_qa_request_rejects_empty_question():
    with pytest.raises(HTTPException) as exc:
        _ = deps.parse_rag_qa_request(payload=None, question="   ")
    assert exc.value.status_code == 400


def test_parse_rag_qa_request_builds_from_query_params():
    out = deps.parse_rag_qa_request(
        payload=None,
        question="q2",
        top_k=2,
        provider="ollama",
        model=None,
    )
    assert out.question == "q2"
    assert out.top_k == 2
    assert out.provider == "ollama"
    assert out.model is None


def test_get_optional_llm_with_details_uses_explicit_overrides(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None
    fake = FakeProvider()
    monkeypatch.setattr(
        ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
    )
    llm, provider, model = deps.get_optional_llm_with_details(
        proven_email=None,
        provider_override="openai",
        model_override="model-b",
    )
    assert getattr(llm, "model_id", None) == "model-b"
    assert provider == "openai"
    assert model == "model-b"


def test_get_optional_llm_with_details_ignores_preferences_on_exception(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None
    fake = FakeProvider()
    monkeypatch.setattr(
        ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
    )

    class _Mgr:
        def get_preferences(self, user_email: str):
            raise RuntimeError("prefs down")

    monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _Mgr())

    llm, provider, model = deps.get_optional_llm_with_details(
        proven_email="u1@example.com",
        provider_override=None,
        model_override=None,
    )
    assert getattr(llm, "model_id", None) == "model-a"
    assert provider == "openai"
    assert model == "model-a"


def test_get_optional_llm_with_details_uses_preferred_provider_when_model_override_only(
    monkeypatch,
):
    settings.default_provider = "openai"
    settings.default_model = None

    fake = FakeProvider()
    monkeypatch.setattr(
        ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
    )

    class _Prefs:
        preferred_provider = "ollama"
        preferred_model = None

    class _Mgr:
        def get_preferences(self, user_email: str):
            assert user_email == "u1@example.com"
            return _Prefs()

    monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _Mgr())

    llm, provider, model = deps.get_optional_llm_with_details(
        proven_email="u1@example.com",
        provider_override=None,
        model_override="model-b",
    )
    assert getattr(llm, "model_id", None) == "model-b"
    assert provider == "ollama"
    assert model == "model-b"


def test_get_optional_llm_with_details_returns_none_on_explicit_failure(monkeypatch):
    class FailingProvider(FakeProvider):
        def create_model(self, model_id, temperature, max_tokens, **kwargs):
            raise RuntimeError("bad model")

    settings.default_provider = "openai"
    settings.default_model = None
    failing = FailingProvider()
    monkeypatch.setattr(
        ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: failing
    )

    llm, provider, model = deps.get_optional_llm_with_details(
        proven_email=None,
        provider_override="openai",
        model_override="model-b",
    )
    assert llm is None
    assert provider == "openai"
    assert model == "model-b"


def test_get_optional_llm_with_details_falls_back_when_preferred_model_fails(monkeypatch):
    settings.default_provider = "ollama"
    settings.default_model = "model-a"

    class FailingProvider(FakeProvider):
        def create_model(self, model_id, temperature, max_tokens, **kwargs):
            raise RuntimeError("bad model")

    failing = FailingProvider()
    working = FakeProvider()

    def _get_provider(name, config=None, use_cache=True):
        return failing if name == "openai" else working

    monkeypatch.setattr(ModelProviderFactory, "get_provider", _get_provider)

    class _Prefs:
        preferred_provider = "openai"
        preferred_model = "bad"

    class _Mgr:
        def get_preferences(self, user_email: str):
            return _Prefs()

    monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _Mgr())

    llm, provider, model = deps.get_optional_llm_with_details(
        proven_email="u1@example.com",
        provider_override=None,
        model_override=None,
    )
    assert getattr(llm, "model_id", None) == "model-a"
    assert provider == "ollama"
    assert model == "model-a"
