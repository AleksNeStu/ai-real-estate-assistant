from unittest.mock import patch

import pytest

from models.provider_factory import ModelProviderFactory


@pytest.fixture
def mock_settings_env():
    with patch("config.settings.os.getenv") as mock_getenv:

        def get_env(key, default=None):
            if key == "OPENAI_API_KEY":
                return "sk-test-openai"
            if key == "ANTHROPIC_API_KEY":
                return "sk-ant-test"
            if key == "GOOGLE_API_KEY":
                return "AIza-test"
            if key == "XAI_API_KEY":
                return "xai-test-key"
            if key == "DEEPSEEK_API_KEY":
                return "sk-deepseek-test"
            return default

        mock_getenv.side_effect = get_env

        # Reload settings or just patch the instance used by factory
        with patch("models.provider_factory.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test-openai"
            mock_settings.anthropic_api_key = "sk-ant-test"
            mock_settings.google_api_key = "AIza-test"
            mock_settings.grok_api_key = "xai-test-key"  # Fixed: was xai_api_key
            mock_settings.deepseek_api_key = "sk-deepseek-test"
            mock_settings.default_temperature = 0.5
            mock_settings.default_max_tokens = 2048
            yield mock_settings


def test_list_all_models_integration(mock_settings_env):
    """
    Test listing all models from all providers without mocking the list_models method.
    This ensures that the list_models code in each provider is executed (coverage).
    """
    ModelProviderFactory.clear_cache()

    # We do NOT mock list_models here, so it executes the real code in providers.
    # Since list_models methods are static (return hardcoded lists), they don't need network.

    all_models = ModelProviderFactory.list_all_models(include_unavailable=True)

    # Verify we got models from multiple providers
    provider_names = {m.provider_name for m in all_models}

    # Check for presence of key providers
    assert "OpenAI" in provider_names or "openai" in provider_names
    assert "Anthropic (Claude)" in provider_names or "anthropic" in provider_names
    assert "Google (Gemini)" in provider_names or "google" in provider_names
    assert "Grok (xAI)" in provider_names or "grok" in provider_names
    assert "DeepSeek" in provider_names or "deepseek" in provider_names
    assert "Ollama (Local)" in provider_names or "ollama" in provider_names

    # Check that we have a significant number of models
    assert len(all_models) >= 10  # We have many models across providers


def test_factory_creates_providers_with_settings(mock_settings_env):
    ModelProviderFactory.clear_cache()

    # Also patch _PROVIDER_KEY_MAP since it captures settings values at class definition time
    test_key_map = {
        "openai": "sk-test-openai",
        "anthropic": "sk-ant-test",
        "google": "AIza-test",
        "grok": "xai-test-key",
        "deepseek": "sk-deepseek-test",
        "openrouter": None,
        "groq": None,
        "mistral": None,
        "qwen": None,
        "zai": None,
        "moonshot": None,
        "opencode": None,
        "ollama": None,
    }
    with patch.object(ModelProviderFactory, "_PROVIDER_KEY_MAP", test_key_map):
        # OpenAI
        openai_provider = ModelProviderFactory.get_provider("openai")
        assert openai_provider.config["api_key"] == "sk-test-openai"

        # Anthropic
        anthropic_provider = ModelProviderFactory.get_provider("anthropic")
        assert anthropic_provider.config["api_key"] == "sk-ant-test"

        # Google
        google_provider = ModelProviderFactory.get_provider("google")
        assert google_provider.config["api_key"] == "AIza-test"

        # Grok
        grok_provider = ModelProviderFactory.get_provider("grok")
        assert grok_provider.config["api_key"] == "xai-test-key"

        # DeepSeek
        deepseek_provider = ModelProviderFactory.get_provider("deepseek")
        assert deepseek_provider.config["api_key"] == "sk-deepseek-test"
