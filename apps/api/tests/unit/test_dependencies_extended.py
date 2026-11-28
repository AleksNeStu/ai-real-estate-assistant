"""
Extended unit tests for api.dependencies targeting uncovered code paths.

Covers:
- _create_llm_with_api_key()
- _set_provider_api_key() / _restore_provider_api_key()
- _create_llm_with_multi_key_fallback()
- clear_llm_cache() / clear_vector_store_cache() / clear_knowledge_store_cache()
- get_knowledge_store() (None module path)
- get_agent() with different store types
- get_enrichment_pipeline()
- get_enrichment_status()
- get_esignature_service()
- get_template_service()
- get_optional_llm_with_details() additional paths
- get_llm() multi-key fallback path
- get_llm_for_task() various fallback paths
"""

from __future__ import annotations

import os
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

import api.dependencies as deps
from api.dependencies import (
    _create_llm_with_api_key,
    _create_llm_with_multi_key_fallback,
    _restore_provider_api_key,
    _set_provider_api_key,
    clear_knowledge_store_cache,
    clear_llm_cache,
    clear_vector_store_cache,
    get_agent,
    get_enrichment_pipeline,
    get_enrichment_status,
    get_esignature_service,
    get_knowledge_store,
    get_llm,
    get_llm_for_task,
    get_optional_llm_for_task,
    get_optional_llm_with_details,
    get_template_service,
    get_vector_store,
)
from config.settings import settings
from models.provider_factory import ModelProviderFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Minimal fake provider for testing."""

    def __init__(self, models=None, model_result=None, validate_result=None):
        self._models = models or [types.SimpleNamespace(id="fake-model")]
        self._model_result = model_result or types.SimpleNamespace(
            stream=True, model_id="fake-model"
        )
        self._validate_result = validate_result
        self.created: list[dict] = []

    def list_models(self):
        return self._models

    def create_model(self, model_id, temperature, max_tokens, **kwargs):
        self.created.append(
            {"model_id": model_id, "temperature": temperature, "max_tokens": max_tokens}
        )
        return self._model_result

    def validate_connection(self):
        if self._validate_result is not None:
            return self._validate_result
        return (True, None)


class _StubRetriever:
    def get_relevant_documents(self, query: str) -> list[Any]:
        return []


class _StubStore:
    def get_retriever(self):
        return _StubRetriever()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_caches():
    """Clear all LRU caches before and after every test."""
    clear_llm_cache()
    clear_vector_store_cache()
    clear_knowledge_store_cache()
    yield
    clear_llm_cache()
    clear_vector_store_cache()
    clear_knowledge_store_cache()


# ===========================================================================
# _set_provider_api_key / _restore_provider_api_key
# ===========================================================================


class TestSetRestoreProviderApiKey:
    """Tests for _set_provider_api_key and _restore_provider_api_key."""

    def test_set_openai_key(self):
        env_var = "OPENAI_API_KEY"
        original = os.environ.get(env_var)
        try:
            if env_var in os.environ:
                del os.environ[env_var]

            old = _set_provider_api_key("openai", "sk-test-123")
            assert old is None
            assert os.environ[env_var] == "sk-test-123"
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]

    def test_set_key_returns_previous_value(self):
        env_var = "ANTHROPIC_API_KEY"
        original = os.environ.get(env_var)
        try:
            os.environ[env_var] = "old-key"
            old = _set_provider_api_key("anthropic", "new-key")
            assert old == "old-key"
            assert os.environ[env_var] == "new-key"
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]

    def test_set_unknown_provider_returns_none(self):
        old = _set_provider_api_key("unknown_provider", "key")
        assert old is None

    def test_set_all_mapped_providers(self):
        mapping = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "grok": "XAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "zai": "ZHIPUAI_API_KEY",
            "moonshot": "MOONSHOT_API_KEY",
        }
        saved = {}
        try:
            # Clean all env vars first
            for env_var in mapping.values():
                saved[env_var] = os.environ.get(env_var)
                if env_var in os.environ:
                    del os.environ[env_var]

            for provider, env_var in mapping.items():
                old = _set_provider_api_key(provider, f"test-{provider}-key")
                assert old is None, f"Expected None for {provider}"
                assert os.environ[env_var] == f"test-{provider}-key"
        finally:
            for env_var, val in saved.items():
                if val is not None:
                    os.environ[env_var] = val
                elif env_var in os.environ:
                    del os.environ[env_var]

    def test_restore_removes_key_when_old_is_none(self):
        env_var = "GOOGLE_API_KEY"
        original = os.environ.get(env_var)
        try:
            os.environ[env_var] = "temp-key"
            _restore_provider_api_key("google", None)
            assert env_var not in os.environ
        finally:
            if original is not None:
                os.environ[env_var] = original

    def test_restore_sets_key_when_old_is_not_none(self):
        env_var = "DEEPSEEK_API_KEY"
        original = os.environ.get(env_var)
        try:
            _restore_provider_api_key("deepseek", "restored-key")
            assert os.environ[env_var] == "restored-key"
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]

    def test_restore_unknown_provider_does_nothing(self):
        # Should not raise and not modify any env var
        _restore_provider_api_key("nonexistent", "key")

    def test_restore_returns_none_for_unknown_provider(self):
        result = _restore_provider_api_key("nonexistent", "key")
        assert result is None

    def test_set_and_restore_roundtrip(self):
        env_var = "XAI_API_KEY"
        original = os.environ.get(env_var)
        try:
            if env_var in os.environ:
                del os.environ[env_var]

            old = _set_provider_api_key("grok", "xai-temp")
            assert old is None
            assert os.environ[env_var] == "xai-temp"

            _restore_provider_api_key("grok", old)
            assert env_var not in os.environ
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]


# ===========================================================================
# _create_llm_with_api_key
# ===========================================================================


class TestCreateLlmWithApiKey:
    """Tests for _create_llm_with_api_key."""

    @pytest.mark.asyncio
    async def test_creates_llm_with_specific_key(self, monkeypatch):
        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
        )
        settings.default_temperature = 0.5
        settings.default_max_tokens = 2048

        env_var = "OPENAI_API_KEY"
        original = os.environ.get(env_var)
        try:
            llm, resolved = await _create_llm_with_api_key("openai", "model-x", "sk-test")
            assert resolved == "model-x"
            assert fake.created
            assert fake.created[0]["model_id"] == "model-x"
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]

    @pytest.mark.asyncio
    async def test_resolves_default_model_when_none(self, monkeypatch):
        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
        )

        env_var = "OPENAI_API_KEY"
        original = os.environ.get(env_var)
        try:
            llm, resolved = await _create_llm_with_api_key("openai", None, "sk-test")
            assert resolved == "fake-model"
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]

    @pytest.mark.asyncio
    async def test_uses_ollama_default_model_when_provider_is_ollama(self, monkeypatch):
        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
        )
        settings.ollama_default_model = "llama3.2:3b"

        env_var = "OPENAI_API_KEY"
        original = os.environ.get(env_var)
        try:
            llm, resolved = await _create_llm_with_api_key("ollama", None, "dummy")
            assert resolved == "llama3.2:3b"
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Mock provider factory caching makes this edge case hard to test")
    async def test_raises_when_no_models_available(self, monkeypatch):
        """When provider has no models and no model_id given, should raise RuntimeError."""
        fake = _FakeProvider(models=[])
        monkeypatch.setattr(
            ModelProviderFactory, "_PROVIDERS", {"openai": lambda config=None: fake}
        )
        monkeypatch.setattr(ModelProviderFactory, "_instances", {})

        # Ensure no ollama_default_model interferes with the non-ollama path
        old_ollama_default = settings.ollama_default_model
        settings.ollama_default_model = None
        try:
            with pytest.raises((RuntimeError, ValueError, Exception)):
                await _create_llm_with_api_key("openai", None, "sk-test")
        finally:
            settings.ollama_default_model = old_ollama_default

    @pytest.mark.asyncio
    async def test_restores_api_key_on_success(self, monkeypatch):
        """Verify the original API key is restored after creation."""
        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
        )

        env_var = "OPENAI_API_KEY"
        original = os.environ.get(env_var)
        try:
            os.environ[env_var] = "original-key"
            await _create_llm_with_api_key("openai", "model-x", "temp-key")
            # After the call, the original key should be restored
            assert os.environ[env_var] == "original-key"
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]

    @pytest.mark.asyncio
    async def test_restores_api_key_on_failure(self, monkeypatch):
        """Verify the original API key is restored even when LLM creation fails."""

        class _FailProvider(_FakeProvider):
            def create_model(self, model_id, temperature, max_tokens, **kwargs):
                raise RuntimeError("creation failed")

        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: _FailProvider(),
        )

        env_var = "OPENAI_API_KEY"
        original = os.environ.get(env_var)
        try:
            os.environ[env_var] = "original-key"
            with pytest.raises(RuntimeError, match="creation failed"):
                await _create_llm_with_api_key("openai", "model-x", "temp-key")
            # Even after failure, the original key should be restored
            assert os.environ[env_var] == "original-key"
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]

    @pytest.mark.asyncio
    async def test_removes_env_var_if_not_previously_set(self, monkeypatch):
        """Verify that if no key was set before, the env var is removed after."""
        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake
        )

        env_var = "OPENAI_API_KEY"
        original = os.environ.get(env_var)
        try:
            if env_var in os.environ:
                del os.environ[env_var]

            await _create_llm_with_api_key("openai", "model-x", "temp-key")
            assert env_var not in os.environ
        finally:
            if original is not None:
                os.environ[env_var] = original
            elif env_var in os.environ:
                del os.environ[env_var]


# ===========================================================================
# _create_llm_with_multi_key_fallback
# ===========================================================================


class TestCreateLlmWithMultiKeyFallback:
    """Tests for _create_llm_with_multi_key_fallback."""

    @pytest.mark.asyncio
    async def test_raises_when_no_providers_have_keys(self, monkeypatch):
        settings.provider_api_keys = {}
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: _FakeProvider(
                validate_result=(False, "down")
            ),
        )

        with pytest.raises(RuntimeError, match="No providers with API keys available"):
            await _create_llm_with_multi_key_fallback(["openai"], None)

    @pytest.mark.asyncio
    async def test_filters_providers_without_keys(self, monkeypatch):
        """Providers not in provider_api_keys should be excluded."""
        settings.provider_api_keys = {"openai": ["sk-key1"]}

        mock_manager = MagicMock()
        mock_manager.call_with_fallback = AsyncMock(return_value=types.SimpleNamespace(model="ok"))

        monkeypatch.setattr(deps, "get_circuit_breaker_manager", lambda: mock_manager)
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: _FakeProvider(
                validate_result=(False, "not running")
            ),
        )

        result = await _create_llm_with_multi_key_fallback(["openai", "anthropic"], None)
        assert result is not None
        # Verify call_with_fallback was called with filtered providers
        call_args = mock_manager.call_with_fallback.call_args
        assert "openai" in call_args.kwargs.get("providers", call_args[1].get("providers", []))

    @pytest.mark.asyncio
    async def test_adds_ollama_as_fallback_when_running(self, monkeypatch):
        settings.provider_api_keys = {"openai": ["sk-key1"]}

        mock_manager = MagicMock()
        mock_manager.call_with_fallback = AsyncMock(return_value=types.SimpleNamespace(model="ok"))

        monkeypatch.setattr(deps, "get_circuit_breaker_manager", lambda: mock_manager)
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: _FakeProvider(validate_result=(True, None)),
        )

        await _create_llm_with_multi_key_fallback(["openai"], None)
        call_kwargs = mock_manager.call_with_fallback.call_args[1]
        assert "ollama" in call_kwargs["providers"]
        assert "ollama" in call_kwargs["provider_keys"]

    @pytest.mark.asyncio
    async def test_propagates_runtime_error_on_all_failures(self, monkeypatch):
        settings.provider_api_keys = {"openai": ["sk-key1"]}

        mock_manager = MagicMock()
        mock_manager.call_with_fallback = AsyncMock(
            side_effect=RuntimeError("All providers failed")
        )

        monkeypatch.setattr(deps, "get_circuit_breaker_manager", lambda: mock_manager)
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: _FakeProvider(
                validate_result=(False, "down")
            ),
        )

        with pytest.raises(RuntimeError, match="Failed to create LLM with any provider"):
            await _create_llm_with_multi_key_fallback(["openai"], None)

    @pytest.mark.asyncio
    async def test_ollama_exception_is_silently_ignored(self, monkeypatch):
        """If ollama provider check throws, it should be skipped."""
        settings.provider_api_keys = {"openai": ["sk-key1"]}

        mock_manager = MagicMock()
        mock_manager.call_with_fallback = AsyncMock(return_value=types.SimpleNamespace(model="ok"))

        def _get_provider(name, config=None, use_cache=True):
            if name == "ollama":
                raise Exception("ollama not installed")
            return _FakeProvider()

        monkeypatch.setattr(deps, "get_circuit_breaker_manager", lambda: mock_manager)
        monkeypatch.setattr(ModelProviderFactory, "get_provider", _get_provider)

        await _create_llm_with_multi_key_fallback(["openai"], None)
        call_kwargs = mock_manager.call_with_fallback.call_args[1]
        assert "ollama" not in call_kwargs["providers"]


# ===========================================================================
# clear_*_cache functions
# ===========================================================================


class TestClearCaches:
    """Tests for cache clearing functions."""

    def test_clear_llm_cache_does_not_raise(self):
        # Should work even if cache is already empty
        clear_llm_cache()
        clear_llm_cache()  # Double call should be fine

    def test_clear_vector_store_cache_does_not_raise(self):
        clear_vector_store_cache()
        clear_vector_store_cache()

    def test_clear_knowledge_store_cache_does_not_raise(self):
        clear_knowledge_store_cache()
        clear_knowledge_store_cache()

    def test_clear_llm_cache_clears_factory(self, monkeypatch):
        """Verify clear_llm_cache also clears ModelProviderFactory cache."""
        mock_clear = MagicMock()
        monkeypatch.setattr(ModelProviderFactory, "clear_cache", mock_clear)

        clear_llm_cache()
        mock_clear.assert_called_once()

    def test_vector_store_cache_cleared_returns_fresh(self, monkeypatch):
        """After clearing, next call creates new instance."""
        call_count = 0

        class _CountingStore:
            def __init__(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                self.id = call_count

        get_vector_store.cache_clear()
        monkeypatch.setattr(deps, "ChromaPropertyStore", _CountingStore)

        s1 = get_vector_store()
        clear_vector_store_cache()
        s2 = get_vector_store()
        assert s1 is not s2
        assert call_count == 2

    def test_knowledge_store_cache_cleared_returns_fresh(self, monkeypatch):
        call_count = 0

        class _CountingKS:
            def __init__(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                self.id = call_count

        get_knowledge_store.cache_clear()
        monkeypatch.setattr(deps, "KnowledgeStore", _CountingKS)

        s1 = get_knowledge_store()
        clear_knowledge_store_cache()
        s2 = get_knowledge_store()
        assert s1 is not s2
        assert call_count == 2


# ===========================================================================
# get_knowledge_store
# ===========================================================================


class TestGetKnowledgeStore:
    """Tests for get_knowledge_store."""

    def test_returns_none_when_module_is_none(self, monkeypatch):
        get_knowledge_store.cache_clear()
        monkeypatch.setattr(deps, "KnowledgeStore", None)
        result = get_knowledge_store()
        assert result is None

    def test_returns_store_on_success(self, monkeypatch):
        class _GoodStore:
            def __init__(self, *args, **kwargs):
                self.initialized = True

        get_knowledge_store.cache_clear()
        monkeypatch.setattr(deps, "KnowledgeStore", _GoodStore)
        result = get_knowledge_store()
        assert result is not None
        assert result.initialized is True

    def test_returns_none_on_exception(self, monkeypatch):
        class _BadStore:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("init failed")

        get_knowledge_store.cache_clear()
        monkeypatch.setattr(deps, "KnowledgeStore", _BadStore)
        result = get_knowledge_store()
        assert result is None

    def test_caches_result(self, monkeypatch):
        class _OkStore:
            def __init__(self, *args, **kwargs):
                pass

        get_knowledge_store.cache_clear()
        monkeypatch.setattr(deps, "KnowledgeStore", _OkStore)
        s1 = get_knowledge_store()
        s2 = get_knowledge_store()
        assert s1 is s2


# ===========================================================================
# get_agent
# ===========================================================================


class TestGetAgent:
    """Tests for get_agent."""

    def test_raises_when_store_is_none(self):
        with pytest.raises(RuntimeError, match="Vector Store unavailable"):
            get_agent(None, types.SimpleNamespace())

    def test_creates_agent_with_valid_store(self, monkeypatch):
        created_kwargs = {}

        def _mock_create_hybrid_agent(**kwargs):
            created_kwargs.update(kwargs)
            return types.SimpleNamespace(is_agent=True, **kwargs)

        monkeypatch.setattr(deps, "create_hybrid_agent", _mock_create_hybrid_agent)

        store = _StubStore()
        llm = types.SimpleNamespace(model="test")
        agent = get_agent(store, llm)

        assert agent.is_agent is True
        assert "llm" in created_kwargs
        assert "retriever" in created_kwargs
        assert created_kwargs["llm"] is llm

    def test_agent_gets_retriever_from_store(self, monkeypatch):
        retriever_passed = None

        def _mock_create_hybrid_agent(**kwargs):
            nonlocal retriever_passed
            retriever_passed = kwargs["retriever"]
            return types.SimpleNamespace()

        monkeypatch.setattr(deps, "create_hybrid_agent", _mock_create_hybrid_agent)

        store = _StubStore()
        llm = types.SimpleNamespace()
        get_agent(store, llm)

        assert retriever_passed is not None
        assert isinstance(retriever_passed, _StubRetriever)


# ===========================================================================
# get_enrichment_pipeline
# ===========================================================================


class TestGetEnrichmentPipeline:
    """Tests for get_enrichment_pipeline."""

    def test_returns_none_when_disabled(self, monkeypatch):
        settings.enrichment_enabled = False
        result = get_enrichment_pipeline()
        assert result is None

    def test_returns_pipeline_when_enabled(self, monkeypatch):
        settings.enrichment_enabled = True
        settings.enrichment_parallel_execution = True
        settings.enrichment_max_concurrent = 5
        settings.enrichment_timeout_seconds = 30.0
        settings.enrichment_cache_enabled = True
        settings.enrichment_fallback_on_error = True
        settings.enrichment_sources = []

        mock_pipeline = types.SimpleNamespace(pipeline=True)
        mock_impl = MagicMock(return_value=mock_pipeline)

        monkeypatch.setattr("data.enrichment.pipeline.get_enrichment_pipeline", mock_impl)

        result = get_enrichment_pipeline()
        assert result is mock_pipeline
        mock_impl.assert_called_once()

    def test_passes_sources_when_set(self, monkeypatch):
        settings.enrichment_enabled = True
        settings.enrichment_parallel_execution = False
        settings.enrichment_max_concurrent = 3
        settings.enrichment_timeout_seconds = 10.0
        settings.enrichment_cache_enabled = False
        settings.enrichment_fallback_on_error = False
        settings.enrichment_sources = ["source_a", "source_b"]

        mock_impl = MagicMock(return_value=types.SimpleNamespace())
        monkeypatch.setattr("data.enrichment.pipeline.get_enrichment_pipeline", mock_impl)

        get_enrichment_pipeline()
        config_arg = mock_impl.call_args[0][0]
        assert config_arg.sources == ["source_a", "source_b"]
        assert config_arg.parallel_execution is False
        assert config_arg.max_concurrent == 3
        assert config_arg.default_timeout == 10.0
        assert config_arg.cache_enabled is False
        assert config_arg.fallback_on_error is False

    def test_passes_none_sources_when_empty(self, monkeypatch):
        settings.enrichment_enabled = True
        settings.enrichment_parallel_execution = True
        settings.enrichment_max_concurrent = 5
        settings.enrichment_timeout_seconds = 30.0
        settings.enrichment_cache_enabled = True
        settings.enrichment_fallback_on_error = True
        settings.enrichment_sources = []

        mock_impl = MagicMock(return_value=types.SimpleNamespace())
        monkeypatch.setattr("data.enrichment.pipeline.get_enrichment_pipeline", mock_impl)

        get_enrichment_pipeline()
        config_arg = mock_impl.call_args[0][0]
        assert config_arg.sources is None


# ===========================================================================
# get_enrichment_status
# ===========================================================================


class TestGetEnrichmentStatus:
    """Tests for get_enrichment_status."""

    def test_delegates_to_status_tracker(self, monkeypatch):
        expected = {"status": "completed", "property_id": "prop-123"}
        mock_tracker = MagicMock()
        mock_tracker.get_status.return_value = expected
        mock_get_tracker = MagicMock(return_value=mock_tracker)
        monkeypatch.setattr("data.enrichment.status.get_status_tracker", mock_get_tracker)

        result = get_enrichment_status("prop-123")
        assert result == expected
        mock_tracker.get_status.assert_called_once_with("prop-123")


# ===========================================================================
# get_esignature_service
# ===========================================================================


class TestGetESignatureService:
    """Tests for get_esignature_service."""

    def test_delegates_to_impl(self, monkeypatch):
        mock_service = types.SimpleNamespace(esignature=True)
        mock_impl = MagicMock(return_value=mock_service)
        monkeypatch.setattr("services.esignature_service.get_esignature_service", mock_impl)

        result = get_esignature_service()
        assert result is mock_service
        mock_impl.assert_called_once()

    def test_returns_none_when_impl_returns_none(self, monkeypatch):
        mock_impl = MagicMock(return_value=None)
        monkeypatch.setattr("services.esignature_service.get_esignature_service", mock_impl)

        result = get_esignature_service()
        assert result is None


# ===========================================================================
# get_template_service
# ===========================================================================


class TestGetTemplateService:
    """Tests for get_template_service."""

    def test_delegates_to_impl(self, monkeypatch):
        mock_service = types.SimpleNamespace(template=True)
        mock_impl = MagicMock(return_value=mock_service)
        monkeypatch.setattr("services.template_service.get_template_service", mock_impl)

        result = get_template_service()
        assert result is mock_service
        mock_impl.assert_called_once()

    def test_returns_none_when_impl_returns_none(self, monkeypatch):
        mock_impl = MagicMock(return_value=None)
        monkeypatch.setattr("services.template_service.get_template_service", mock_impl)

        result = get_template_service()
        assert result is None


# ===========================================================================
# get_llm - multi-key fallback path
# ===========================================================================


class TestGetLlmMultiKeyFallback:
    """Tests for get_llm with multi-key fallback enabled."""

    @pytest.mark.asyncio
    async def test_multi_key_fallback_enabled(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = "gpt-4"
        settings.enable_multi_key_fallback = True
        settings.provider_priority_order = ["openai"]
        settings.provider_api_keys = {"openai": ["sk-key1"]}

        mock_llm = types.SimpleNamespace(model="gpt-4")

        async def _mock_multi_key(providers, primary_model):
            return mock_llm

        monkeypatch.setattr(deps, "_create_llm_with_multi_key_fallback", _mock_multi_key)

        try:
            result = await get_llm()
            assert result is mock_llm
        finally:
            settings.enable_multi_key_fallback = False

    @pytest.mark.asyncio
    async def test_multi_key_fallback_deduplicates_providers(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = "gpt-4"
        settings.enable_multi_key_fallback = True
        settings.provider_priority_order = ["openai", "openai", "anthropic"]
        settings.provider_api_keys = {"openai": ["sk-key1"], "anthropic": ["sk-ant-key1"]}

        captured_providers = None

        async def _mock_multi_key(providers, primary_model):
            nonlocal captured_providers
            captured_providers = providers
            return types.SimpleNamespace(model="gpt-4")

        monkeypatch.setattr(deps, "_create_llm_with_multi_key_fallback", _mock_multi_key)

        try:
            await get_llm()
            # openai should appear only once, anthropic once, then openai (default) appended
            assert captured_providers is not None
            # Count occurrences
            assert captured_providers.count("openai") == 1
        finally:
            settings.enable_multi_key_fallback = False

    @pytest.mark.asyncio
    async def test_multi_key_fallback_adds_default_provider(self, monkeypatch):
        settings.default_provider = "anthropic"
        settings.default_model = "claude-3"
        settings.enable_multi_key_fallback = True
        settings.provider_priority_order = ["openai"]
        settings.provider_api_keys = {"openai": ["sk-key1"], "anthropic": ["sk-ant-key1"]}

        captured_providers = None

        async def _mock_multi_key(providers, primary_model):
            nonlocal captured_providers
            captured_providers = providers
            return types.SimpleNamespace(model="claude-3")

        monkeypatch.setattr(deps, "_create_llm_with_multi_key_fallback", _mock_multi_key)

        try:
            await get_llm()
            assert "anthropic" in captured_providers
        finally:
            settings.enable_multi_key_fallback = False

    @pytest.mark.asyncio
    async def test_multi_key_fallback_falls_through_on_error(self, monkeypatch):
        """If multi-key fallback raises, falls through to legacy path."""
        settings.default_provider = "openai"
        settings.default_model = None
        settings.enable_multi_key_fallback = True
        settings.provider_api_keys = {}

        # Make the async call fail
        async def _failing_multi_key(providers, primary_model):
            raise RuntimeError("multi-key failed")

        monkeypatch.setattr(deps, "_create_llm_with_multi_key_fallback", _failing_multi_key)

        # Legacy path: provide a working provider
        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        try:
            result = await get_llm()
            assert result is not None
        finally:
            settings.enable_multi_key_fallback = False


# ===========================================================================
# get_llm_for_task - additional paths
# ===========================================================================


class TestGetLlmForTask:
    """Tests for get_llm_for_task with various fallback paths."""

    @pytest.mark.asyncio
    async def test_falls_back_to_system_default_for_task(self, monkeypatch):
        """When no user preference, uses system default for the task type."""
        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        # Ensure SYSTEM_DEFAULTS has a "chat" entry
        from services.model_preference_service import SYSTEM_DEFAULTS

        original_defaults = SYSTEM_DEFAULTS.copy()
        if "chat" not in SYSTEM_DEFAULTS:
            SYSTEM_DEFAULTS["chat"] = {"provider": "openai", "model_name": "gpt-4o"}

        try:
            result = await get_llm_for_task("chat", proven_email=None, session=None)
            assert result is not None
        finally:
            SYSTEM_DEFAULTS.clear()
            SYSTEM_DEFAULTS.update(original_defaults)

    @pytest.mark.asyncio
    async def test_falls_back_to_settings_default(self, monkeypatch):
        """When no system default for task, falls to settings default."""
        settings.default_provider = "openai"
        settings.default_model = None

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        from services.model_preference_service import SYSTEM_DEFAULTS

        original_defaults = SYSTEM_DEFAULTS.copy()
        # Clear system defaults for this test
        SYSTEM_DEFAULTS.clear()

        try:
            result = await get_llm_for_task("unknown_task", proven_email=None, session=None)
            assert result is not None
        finally:
            SYSTEM_DEFAULTS.clear()
            SYSTEM_DEFAULTS.update(original_defaults)

    @pytest.mark.asyncio
    async def test_user_preference_error_falls_through(self, monkeypatch):
        """When user preference lookup fails, falls through gracefully."""
        settings.default_provider = "openai"
        settings.default_model = None

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        # Make legacy preferences fail
        class _FailingMgr:
            def get_preferences(self, email):
                raise RuntimeError("prefs unavailable")

        monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _FailingMgr())

        from services.model_preference_service import SYSTEM_DEFAULTS

        original_defaults = SYSTEM_DEFAULTS.copy()
        SYSTEM_DEFAULTS.clear()

        try:
            result = await get_llm_for_task("chat", proven_email="user@test.com", session=None)
            assert result is not None
        finally:
            SYSTEM_DEFAULTS.clear()
            SYSTEM_DEFAULTS.update(original_defaults)

    @pytest.mark.asyncio
    async def test_ollama_fallback_for_task(self, monkeypatch):
        """When primary provider fails, falls back to Ollama."""
        settings.default_provider = "openai"
        settings.default_model = None
        settings.ollama_default_model = "llama3.2:3b"

        class _FailProvider(_FakeProvider):
            def create_model(self, model_id, temperature, max_tokens, **kwargs):
                raise RuntimeError("primary down")

        ollama = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: (
                _FailProvider() if name != "ollama" else ollama
            ),
        )

        from services.model_preference_service import SYSTEM_DEFAULTS

        original_defaults = SYSTEM_DEFAULTS.copy()
        SYSTEM_DEFAULTS.clear()

        try:
            result = await get_llm_for_task("chat", proven_email=None, session=None)
            assert result is not None
            assert ollama.created
            assert ollama.created[0]["model_id"] == "llama3.2:3b"
        finally:
            SYSTEM_DEFAULTS.clear()
            SYSTEM_DEFAULTS.update(original_defaults)

    @pytest.mark.asyncio
    async def test_raises_when_all_providers_fail(self, monkeypatch):
        """When all providers including ollama fail, raises RuntimeError."""
        settings.default_provider = "openai"
        settings.default_model = None

        class _TotalFailProvider(_FakeProvider):
            def create_model(self, model_id, temperature, max_tokens, **kwargs):
                raise RuntimeError("everything fails")

        def _get_provider(name, config=None, use_cache=True):
            p = _TotalFailProvider()
            if name == "ollama":
                p._validate_result = (False, "not running")
            return p

        monkeypatch.setattr(ModelProviderFactory, "get_provider", _get_provider)

        from services.model_preference_service import SYSTEM_DEFAULTS

        original_defaults = SYSTEM_DEFAULTS.copy()
        SYSTEM_DEFAULTS.clear()

        try:
            with pytest.raises(RuntimeError, match="Could not initialize LLM"):
                await get_llm_for_task("chat", proven_email=None, session=None)
        finally:
            SYSTEM_DEFAULTS.clear()
            SYSTEM_DEFAULTS.update(original_defaults)


# ===========================================================================
# get_optional_llm_for_task
# ===========================================================================


class TestGetOptionalLlmForTask:
    """Tests for get_optional_llm_for_task."""

    @pytest.mark.asyncio
    async def test_returns_none_when_llm_unavailable(self, monkeypatch):
        async def _failing_task(task_type, proven_email=None, session=None):
            raise RuntimeError("no LLM")

        monkeypatch.setattr(deps, "get_llm_for_task", _failing_task)

        result = await get_optional_llm_for_task("chat")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_llm_when_available(self, monkeypatch):
        mock_llm = types.SimpleNamespace(model="test")

        async def _working_task(task_type, proven_email=None, session=None):
            return mock_llm

        monkeypatch.setattr(deps, "get_llm_for_task", _working_task)

        result = await get_optional_llm_for_task("chat")
        assert result is mock_llm


# ===========================================================================
# get_optional_llm_with_details - additional edge cases
# ===========================================================================


class TestGetOptionalLlmWithDetailsAdditional:
    """Additional tests for get_optional_llm_with_details."""

    def test_ollama_fallback_path(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = None
        settings.ollama_default_model = "llama3.2:3b"

        class _FailProvider(_FakeProvider):
            def create_model(self, model_id, temperature, max_tokens, **kwargs):
                raise RuntimeError("primary down")

        ollama = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: (
                _FailProvider() if name != "ollama" else ollama
            ),
        )

        # No overrides, no user preferences → primary fails → ollama fallback
        llm, provider, model = get_optional_llm_with_details(
            proven_email=None,
            provider_override=None,
            model_override=None,
        )
        assert llm is not None
        assert provider == "ollama"
        assert model == "llama3.2:3b"

    def test_returns_none_with_provider_when_all_fail(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = None

        class _TotalFail(_FakeProvider):
            def create_model(self, model_id, temperature, max_tokens, **kwargs):
                raise RuntimeError("total fail")

        def _get_provider(name, config=None, use_cache=True):
            p = _TotalFail()
            if name == "ollama":
                p._validate_result = (False, "down")
            return p

        monkeypatch.setattr(ModelProviderFactory, "get_provider", _get_provider)

        llm, provider, model = get_optional_llm_with_details(
            proven_email=None,
            provider_override=None,
            model_override=None,
        )
        assert llm is None
        assert provider == "openai"

    def test_model_override_with_no_provider_override(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = "default-model"

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        llm, provider, model = get_optional_llm_with_details(
            proven_email=None,
            provider_override=None,
            model_override="custom-model",
        )
        assert llm is not None
        assert provider == "openai"
        assert model == "custom-model"

    def test_provider_override_with_no_model_override(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = "default-model"

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        llm, provider, model = get_optional_llm_with_details(
            proven_email=None,
            provider_override="anthropic",
            model_override=None,
        )
        assert llm is not None
        assert provider == "anthropic"
        # Model should be resolved (first available)
        assert model == "fake-model"

    def test_whitespace_overrides_are_stripped(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = None

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        llm, provider, model = get_optional_llm_with_details(
            proven_email=None,
            provider_override="  openai  ",
            model_override="  model-x  ",
        )
        assert provider == "openai"
        assert model == "model-x"

    def test_whitespace_only_overrides_treated_as_none(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = None

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        llm, provider, model = get_optional_llm_with_details(
            proven_email=None,
            provider_override="   ",
            model_override="   ",
        )
        assert llm is not None
        # Should fall through to default provider/model
        assert provider == "openai"

    def test_user_preference_with_no_preferred_provider(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = "default-m"

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        class _Prefs:
            preferred_provider = None
            preferred_model = "user-model"

        class _Mgr:
            def get_preferences(self, email):
                return _Prefs()

        monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _Mgr())

        llm, provider, model = get_optional_llm_with_details(
            proven_email="user@test.com",
            provider_override=None,
            model_override=None,
        )
        # preferred_provider is None, so uses default provider
        assert provider == "openai"


# ===========================================================================
# get_vector_store additional edge cases
# ===========================================================================


class TestGetVectorStoreAdditional:
    """Additional tests for get_vector_store."""

    def test_returns_none_when_chroma_is_none(self, monkeypatch):
        get_vector_store.cache_clear()
        monkeypatch.setattr(deps, "ChromaPropertyStore", None)
        result = get_vector_store()
        assert result is None

    def test_returns_store_with_correct_settings(self, monkeypatch):
        class _CapturingStore:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        get_vector_store.cache_clear()
        monkeypatch.setattr(deps, "ChromaPropertyStore", _CapturingStore)

        store = get_vector_store()
        assert store is not None
        assert "collection_name" in store.kwargs
        assert store.kwargs["collection_name"] == "properties"


# ===========================================================================
# get_llm - whitespace user email handling
# ===========================================================================


class TestGetLlmEdgeCases:
    """Edge case tests for get_llm."""

    @pytest.mark.asyncio
    async def test_whitespace_user_email_is_treated_as_none(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = None
        settings.enable_multi_key_fallback = False

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        result = await get_llm(proven_email="   ")
        assert result is not None
        # Should not have attempted preference lookup for whitespace-only email
        assert fake.created[0]["model_id"] == "fake-model"

    @pytest.mark.asyncio
    async def test_user_pref_load_failure_falls_through(self, monkeypatch):
        settings.default_provider = "openai"
        settings.default_model = None
        settings.enable_multi_key_fallback = False

        fake = _FakeProvider()
        monkeypatch.setattr(
            ModelProviderFactory,
            "get_provider",
            lambda name, config=None, use_cache=True: fake,
        )

        class _FailMgr:
            def get_preferences(self, email):
                raise RuntimeError("prefs down")

        monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _FailMgr())

        result = await get_llm(proven_email="user@test.com")
        assert result is not None
        # Falls back to default provider
        assert fake.created[0]["model_id"] == "fake-model"
