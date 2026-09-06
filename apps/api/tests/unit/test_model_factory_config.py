from unittest.mock import MagicMock, patch

import pytest

from models.provider_factory import ModelProviderFactory, get_model_display_info
from models.providers.base import ModelCapability, ModelInfo, ModelProvider, PricingInfo


@pytest.fixture
def mock_settings():
    ModelProviderFactory.clear_cache()
    with patch("models.provider_factory.settings") as mock:
        mock.openai_api_key = "test-openai-key"
        mock.anthropic_api_key = "test-anthropic-key"
        mock.default_temperature = 0.7
        mock.default_max_tokens = 1000
        # _PROVIDER_KEY_MAP is evaluated at class-definition time, so we must
        # also patch it to reflect the mocked settings values.
        with patch.dict(
            ModelProviderFactory._PROVIDER_KEY_MAP,
            {
                "openai": mock.openai_api_key,
                "anthropic": mock.anthropic_api_key,
            },
        ):
            yield mock
    ModelProviderFactory.clear_cache()


def test_get_provider_injects_api_key(mock_settings):
    # Get provider without config
    # We use real OpenAIProvider here, which is fine as it's lightweight
    provider = ModelProviderFactory.get_provider("openai", use_cache=False)

    # Check if api_key was injected into config
    assert provider.config.get("api_key") == "test-openai-key"


def test_get_provider_manual_config_overrides_settings(mock_settings):
    custom_config = {"api_key": "custom-key"}
    provider = ModelProviderFactory.get_provider("openai", config=custom_config, use_cache=False)

    assert provider.config.get("api_key") == "custom-key"


def test_create_model_uses_defaults(mock_settings):
    # Mock provider instance
    mock_provider_instance = MagicMock()

    # Mock the provider class constructor
    mock_provider_class = MagicMock(return_value=mock_provider_instance)

    # Patch the registry. The factory's lazy-load path also looks up
    # the module in _PROVIDER_MODULES before resolving a class, so
    # both need to be patched for the mock to win.
    with patch.dict(
        ModelProviderFactory._PROVIDER_MODULES, {"openai": "fake.module"}, clear=True
    ), patch.dict(
        ModelProviderFactory._PROVIDERS, {"openai": mock_provider_class}
    ):
        # Call create_model without temp/tokens
        ModelProviderFactory.create_model("gpt-4o", provider_name="openai")

        # Verify create_model was called on provider with defaults from settings
        mock_provider_instance.create_model.assert_called_once()
        call_kwargs = mock_provider_instance.create_model.call_args.kwargs

        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 1000


def test_create_model_manual_overrides_defaults(mock_settings):
    mock_provider_instance = MagicMock()
    mock_provider_class = MagicMock(return_value=mock_provider_instance)

    with patch.dict(
        ModelProviderFactory._PROVIDER_MODULES, {"openai": "fake.module"}, clear=True
    ), patch.dict(
        ModelProviderFactory._PROVIDERS, {"openai": mock_provider_class}
    ):
        # Call create_model WITH explicit temp/tokens
        ModelProviderFactory.create_model(
            "gpt-4o", provider_name="openai", temperature=0.2, max_tokens=500
        )

        mock_provider_instance.create_model.assert_called_once()
        call_kwargs = mock_provider_instance.create_model.call_args.kwargs

        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 500


class _StubProvider(ModelProvider):
    def __init__(self, config=None, *, name: str = "stub", is_local: bool = False):
        super().__init__(config=config)
        self._name = name
        self._is_local = is_local
        self._models: list[ModelInfo] = []
        self._validate_result: tuple[bool, str | None] = (True, None)

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._name.upper()

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def is_local(self) -> bool:
        return self._is_local

    def list_models(self) -> list[ModelInfo]:
        return list(self._models)

    def create_model(
        self,
        model_id: str,
        temperature: float = 0.0,
        max_tokens=None,
        streaming: bool = True,
        **kwargs,
    ):
        return MagicMock(name=f"model:{model_id}")

    def validate_connection(self) -> tuple[bool, str | None]:
        return self._validate_result


def test_get_provider_unknown_provider_raises_value_error(mock_settings):
    ModelProviderFactory.clear_cache()
    with pytest.raises(ValueError) as excinfo:
        ModelProviderFactory.get_provider("unknown-provider", use_cache=False)
    assert "Unknown provider" in str(excinfo.value)


def test_get_provider_uses_cache_when_config_none(mock_settings):
    ModelProviderFactory.clear_cache()
    stub_ctor = MagicMock(return_value=_StubProvider(config={"api_key": "k"}, name="p1"))
    # The factory checks _PROVIDER_MODULES first (lazy-load registry);
    # the test's mock provider needs to be registered in both dicts.
    with patch.dict(ModelProviderFactory._PROVIDER_MODULES, {"p1": "fake.module"}, clear=True), \
         patch.dict(ModelProviderFactory._PROVIDERS, {"p1": stub_ctor}, clear=True):
        p_first = ModelProviderFactory.get_provider("p1", use_cache=True)
        p_second = ModelProviderFactory.get_provider("p1", use_cache=True)
        assert p_first is p_second
        assert stub_ctor.call_count == 1


def test_get_provider_bypasses_cache_when_config_provided(mock_settings):
    ModelProviderFactory.clear_cache()
    stub_ctor = MagicMock(side_effect=lambda config=None: _StubProvider(config=config, name="p1"))
    with patch.dict(ModelProviderFactory._PROVIDER_MODULES, {"p1": "fake.module"}, clear=True), \
         patch.dict(ModelProviderFactory._PROVIDERS, {"p1": stub_ctor}, clear=True):
        p_cached = ModelProviderFactory.get_provider("p1", use_cache=True)
        p_new = ModelProviderFactory.get_provider("p1", config={"api_key": "other"}, use_cache=True)
        assert p_new is not p_cached
        assert stub_ctor.call_count == 2


def test_list_all_models_skips_unavailable_when_requested(mock_settings):
    ModelProviderFactory.clear_cache()
    provider_ok = _StubProvider(name="ok")
    provider_ok._models = [
        ModelInfo(
            id="m1",
            display_name="Model 1",
            provider_name="ok",
            context_window=1000,
            capabilities=[ModelCapability.STREAMING],
        )
    ]
    provider_ok._validate_result = (True, None)

    provider_bad = _StubProvider(name="bad")
    provider_bad._models = [
        ModelInfo(id="m2", display_name="Model 2", provider_name="bad", context_window=1000)
    ]
    provider_bad._validate_result = (False, "nope")

    def _get_provider(name: str, *args, **kwargs):
        return provider_ok if name == "ok" else provider_bad

    with patch.object(ModelProviderFactory, "list_providers", return_value=["ok", "bad"]):
        with patch.object(ModelProviderFactory, "get_provider", side_effect=_get_provider):
            models = ModelProviderFactory.list_all_models(include_unavailable=False)
    assert [m.id for m in models] == ["m1"]


def test_get_model_by_id_returns_provider_and_info(mock_settings):
    ModelProviderFactory.clear_cache()
    provider = _StubProvider(name="p1")
    provider._models = [ModelInfo(id="m1", display_name="M1", provider_name="p1", context_window=1)]

    with patch.object(ModelProviderFactory, "list_providers", return_value=["p1"]):
        with patch.object(ModelProviderFactory, "get_provider", return_value=provider):
            result = ModelProviderFactory.get_model_by_id("m1")
    assert result is not None
    resolved_provider, model_info = result
    assert resolved_provider is provider
    assert model_info.id == "m1"


def test_create_model_auto_detect_raises_when_not_found(mock_settings):
    ModelProviderFactory.clear_cache()
    with patch.object(ModelProviderFactory, "get_model_by_id", return_value=None):
        with pytest.raises(ValueError) as excinfo:
            ModelProviderFactory.create_model("missing-model", provider_name=None)
    assert "not found" in str(excinfo.value).lower()


def test_create_model_auto_detect_uses_detected_provider(mock_settings):
    ModelProviderFactory.clear_cache()
    provider = MagicMock()
    provider.create_model.return_value = MagicMock()
    model_info = ModelInfo(id="m1", display_name="M1", provider_name="p1", context_window=1)
    with patch.object(ModelProviderFactory, "get_model_by_id", return_value=(provider, model_info)):
        ModelProviderFactory.create_model(
            "m1", provider_name=None, temperature=0.3, max_tokens=50, streaming=False
        )
    provider.create_model.assert_called_once()
    call_kwargs = provider.create_model.call_args.kwargs
    assert call_kwargs["model_id"] == "m1"
    assert call_kwargs["temperature"] == 0.3
    assert call_kwargs["max_tokens"] == 50
    assert call_kwargs["streaming"] is False


def test_get_available_providers_returns_status_and_errors(mock_settings):
    ModelProviderFactory.clear_cache()
    ok = _StubProvider(name="ok")
    ok._validate_result = (True, None)

    def _get_provider(name: str, *args, **kwargs):
        if name == "ok":
            return ok
        raise RuntimeError("boom")

    with patch.object(ModelProviderFactory, "list_providers", return_value=["ok", "bad"]):
        with patch.object(ModelProviderFactory, "get_provider", side_effect=_get_provider):
            results = ModelProviderFactory.get_available_providers()

    assert ("ok", True, None) in results
    bad_entry = [r for r in results if r[0] == "bad"][0]
    assert bad_entry[1] is False
    assert "boom" in (bad_entry[2] or "")


def test_register_provider_requires_modelprovider_subclass(mock_settings):
    ModelProviderFactory.clear_cache()
    with pytest.raises(TypeError):
        ModelProviderFactory.register_provider("x", object)  # type: ignore[arg-type]


def test_register_provider_adds_provider_and_clears_instance_cache(mock_settings):
    ModelProviderFactory.clear_cache()
    stub_ctor = MagicMock(return_value=_StubProvider(name="custom"))
    with patch.dict(ModelProviderFactory._PROVIDER_MODULES, {"custom": "fake.module"}, clear=True), \
         patch.dict(ModelProviderFactory._PROVIDERS, {"custom": stub_ctor}, clear=True):
        cached = ModelProviderFactory.get_provider("custom", use_cache=True)
        assert cached is ModelProviderFactory._instances["custom"]

        class _CustomProvider(_StubProvider):
            pass

        ModelProviderFactory.register_provider("custom", _CustomProvider)
        assert "custom" in ModelProviderFactory._PROVIDERS
        assert "custom" not in ModelProviderFactory._instances


def test_clear_cache_removes_cached_instances(mock_settings):
    ModelProviderFactory.clear_cache()
    stub_ctor = MagicMock(return_value=_StubProvider(name="p1"))
    with patch.dict(ModelProviderFactory._PROVIDER_MODULES, {"p1": "fake.module"}, clear=True), \
         patch.dict(ModelProviderFactory._PROVIDERS, {"p1": stub_ctor}, clear=True):
        ModelProviderFactory.get_provider("p1", use_cache=True)
        assert "p1" in ModelProviderFactory._instances
        ModelProviderFactory.clear_cache()
        assert ModelProviderFactory._instances == {}


def test_get_model_display_info_formats_pricing_and_capabilities():
    model_info = ModelInfo(
        id="m1",
        display_name="M1",
        provider_name="p1",
        context_window=100000,
        pricing=PricingInfo(input_price_per_1m=1.0, output_price_per_1m=2.0, currency="USD"),
        capabilities=[ModelCapability.STREAMING, ModelCapability.VISION],
        description="desc",
        recommended_for=["general"],
    )
    info = get_model_display_info(model_info)
    assert info["id"] == "m1"
    assert info["provider"] == "p1"
    assert info["context"] == "100,000 tokens"
    assert "streaming" in info["capabilities"]
    assert "vision" in info["capabilities"]
    assert "$" in info["cost"]
    assert info["description"] == "desc"
    assert info["recommended_for"] == ["general"]


def test_get_provider_injects_anthropic_api_key(mock_settings):
    provider = ModelProviderFactory.get_provider("anthropic", use_cache=False)
    assert provider.config.get("api_key") == "test-anthropic-key"


def test_get_provider_injects_google_api_key(mock_settings):
    mock_settings.google_api_key = "test-google-key"
    with patch.dict(ModelProviderFactory._PROVIDER_KEY_MAP, {"google": "test-google-key"}):
        provider = ModelProviderFactory.get_provider("google", use_cache=False)
    assert provider.config.get("api_key") == "test-google-key"


def test_get_provider_injects_grok_api_key(mock_settings):
    mock_settings.grok_api_key = "test-grok-key"
    with patch.dict(ModelProviderFactory._PROVIDER_KEY_MAP, {"grok": "test-grok-key"}):
        provider = ModelProviderFactory.get_provider("grok", use_cache=False)
    assert provider.config.get("api_key") == "test-grok-key"


def test_get_provider_injects_deepseek_api_key(mock_settings):
    mock_settings.deepseek_api_key = "test-deepseek-key"
    with patch.dict(ModelProviderFactory._PROVIDER_KEY_MAP, {"deepseek": "test-deepseek-key"}):
        provider = ModelProviderFactory.get_provider("deepseek", use_cache=False)
    assert provider.config.get("api_key") == "test-deepseek-key"


def test_list_all_models_handles_provider_exception(mock_settings):
    ModelProviderFactory.clear_cache()
    provider_ok = _StubProvider(name="ok")
    provider_ok._models = [
        ModelInfo(
            id="m1",
            display_name="Model 1",
            provider_name="ok",
            context_window=1000,
            capabilities=[ModelCapability.STREAMING],
        )
    ]
    provider_ok._validate_result = (True, None)

    provider_bad = _StubProvider(name="bad")
    provider_bad._models = [
        ModelInfo(id="m2", display_name="Model 2", provider_name="bad", context_window=1000)
    ]

    def _get_provider(name: str, *args, **kwargs):
        if name == "ok":
            return provider_ok
        raise RuntimeError("Provider load failed")

    with patch.object(ModelProviderFactory, "list_providers", return_value=["ok", "bad"]):
        with patch.object(ModelProviderFactory, "get_provider", side_effect=_get_provider):
            models = ModelProviderFactory.list_all_models(include_unavailable=True)
    assert [m.id for m in models] == ["m1"]


def test_get_model_by_id_handles_provider_exception(mock_settings):
    ModelProviderFactory.clear_cache()

    def _get_provider(name: str, *args, **kwargs):
        raise RuntimeError("Provider init failed")

    with patch.object(ModelProviderFactory, "list_providers", return_value=["p1"]):
        with patch.object(ModelProviderFactory, "get_provider", side_effect=_get_provider):
            result = ModelProviderFactory.get_model_by_id("m1")
    assert result is None


def test_get_model_display_info_without_pricing():
    model_info = ModelInfo(
        id="local-model",
        display_name="Local Model",
        provider_name="ollama",
        context_window=4000,
        pricing=None,
        capabilities=[ModelCapability.STREAMING],
    )
    info = get_model_display_info(model_info)
    assert info["id"] == "local-model"
    assert info["cost"] == "Free (local)"
