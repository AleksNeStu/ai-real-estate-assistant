"""
Unit tests for ZAI (Zhipu AI) model provider.
"""

import os
from unittest.mock import patch

import pytest

from models.providers.base import ModelCapability
from models.providers.zai import ZAI_BASE_URL, ZaiProvider


class TestZaiProvider:
    """Tests for ZaiProvider class."""

    def test_provider_has_correct_name(self):
        """Test that provider name is 'zai'."""
        provider = ZaiProvider()
        assert provider.name == "zai"

    def test_provider_has_correct_display_name(self):
        """Test that display name is 'ZAI (Zhipu AI)'."""
        provider = ZaiProvider()
        assert provider.display_name == "ZAI (Zhipu AI)"

    def test_provider_requires_api_key(self):
        """Test that provider requires an API key."""
        provider = ZaiProvider()
        assert provider.requires_api_key is True

    def test_provider_is_not_local(self):
        """Test that provider is not local."""
        provider = ZaiProvider()
        assert provider.is_local is False

    def test_provider_lists_models(self):
        """Test that provider lists available models."""
        provider = ZaiProvider()
        models = provider.list_models()

        assert len(models) >= 4
        model_ids = [m.id for m in models]
        assert "glm-4.7-flash" in model_ids
        assert "glm-4.7-flashx" in model_ids
        assert "glm-4.7" in model_ids
        assert "glm-5" in model_ids

    def test_provider_has_free_model(self):
        """Test that provider has a free tier model."""
        provider = ZaiProvider()
        free_model = provider.get_model_info("glm-4.7-flash")

        assert free_model is not None
        assert free_model.pricing is not None
        assert free_model.pricing.input_price_per_1m == 0.0
        assert free_model.pricing.output_price_per_1m == 0.0

    def test_free_model_has_correct_description(self):
        """Test that free model has appropriate description."""
        provider = ZaiProvider()
        free_model = provider.get_model_info("glm-4.7-flash")

        assert free_model is not None
        assert "FREE" in free_model.display_name
        assert "testing" in free_model.recommended_for

    def test_flashx_model_pricing(self):
        """Test that FlashX model has ultra-low pricing."""
        provider = ZaiProvider()
        flashx_model = provider.get_model_info("glm-4.7-flashx")

        assert flashx_model is not None
        assert flashx_model.pricing is not None
        # FlashX is very cheap: $0.07 input, $0.40 output
        assert flashx_model.pricing.input_price_per_1m == 0.07
        assert flashx_model.pricing.output_price_per_1m == 0.40

    def test_models_have_capabilities(self):
        """Test that all models have required capabilities."""
        provider = ZaiProvider()
        models = provider.list_models()

        for model in models:
            assert ModelCapability.STREAMING in model.capabilities
            assert ModelCapability.FUNCTION_CALLING in model.capabilities
            assert ModelCapability.JSON_MODE in model.capabilities
            assert ModelCapability.SYSTEM_MESSAGES in model.capabilities

    def test_vision_models_have_vision_capability(self):
        """Test that vision models have vision capability."""
        provider = ZaiProvider()

        # GLM-4.6V models should have vision capability
        flash_vision = provider.get_model_info("glm-4.6v-flash")
        vision_model = provider.get_model_info("glm-4.6v")

        assert flash_vision is not None
        assert vision_model is not None
        assert ModelCapability.VISION in flash_vision.capabilities
        assert ModelCapability.VISION in vision_model.capabilities

    def test_models_have_context_windows(self):
        """Test that models have context windows set."""
        provider = ZaiProvider()
        models = provider.list_models()

        for model in models:
            assert model.context_window > 0

    def test_flash_models_have_large_context(self):
        """Test that flash models have 200K context."""
        provider = ZaiProvider()

        for model_id in ["glm-4.7-flash", "glm-4.7-flashx"]:
            model = provider.get_model_info(model_id)
            assert model is not None
            assert model.context_window == 200_000

    def test_get_model_info_returns_none_for_invalid_model(self):
        """Test that get_model_info returns None for invalid model ID."""
        provider = ZaiProvider()
        model = provider.get_model_info("invalid-model-id")
        assert model is None

    def test_create_model_raises_error_without_api_key(self):
        """Test that create_model raises error without API key."""
        # Clear the ZAI_API_KEY from environment for this test
        with patch.dict(os.environ, {}, clear=True):
            # Also need to remove from config to ensure no key
            provider = ZaiProvider(config={"api_key": None})
            # Explicitly clear the api_key in config
            provider.config["api_key"] = None

            with pytest.raises(RuntimeError) as exc_info:
                provider.create_model("glm-4.7-flash")

            assert "API key" in str(exc_info.value)

    def test_create_model_raises_error_for_invalid_model(self):
        """Test that create_model raises error for invalid model ID."""
        provider = ZaiProvider(config={"api_key": "test-key"})

        with pytest.raises(ValueError) as exc_info:
            provider.create_model("invalid-model")

        assert "not available" in str(exc_info.value)

    def test_validate_connection_fails_without_api_key(self):
        """Test that validate_connection fails without API key."""
        # Clear the ZAI_API_KEY from environment for this test
        with patch.dict(os.environ, {}, clear=True):
            provider = ZaiProvider(config={"api_key": None})
            # Explicitly clear the api_key in config
            provider.config["api_key"] = None
            is_valid, error = provider.validate_connection()

            assert is_valid is False
            assert "API key" in error

    def test_default_base_url(self):
        """Test that default base URL is set correctly."""
        provider = ZaiProvider()
        assert provider.config.get("base_url") == ZAI_BASE_URL
        assert "bigmodel.cn" in ZAI_BASE_URL or "z.ai" in ZAI_BASE_URL

    def test_api_key_from_environment(self):
        """Test that API key is loaded from environment."""
        # Use clear=True to prevent real ZHIPUAI_API_KEY from leaking in.
        # The provider reads ZHIPUAI_API_KEY first, then ZAI_API_KEY.
        with patch.dict(
            os.environ, {"ZAI_API_KEY": "test-env-key", "ZHIPUAI_API_KEY": ""}, clear=True
        ):
            provider = ZaiProvider()
            assert provider.get_api_key() == "test-env-key"

    def test_api_key_from_config(self):
        """Test that API key from config takes precedence."""
        provider = ZaiProvider(config={"api_key": "config-key"})
        assert provider.get_api_key() == "config-key"

    def test_custom_base_url(self):
        """Test that custom base URL can be set."""
        provider = ZaiProvider(config={"base_url": "https://custom.api.url"})
        assert provider.config.get("base_url") == "https://custom.api.url"


@pytest.mark.skipif(
    not os.getenv("ZAI_API_KEY"),
    reason="ZAI_API_KEY not set - skipping integration tests",
)
class TestZaiProviderIntegration:
    """Integration tests for ZaiProvider (requires API key)."""

    def test_create_model_with_valid_key(self):
        """Test that model can be created with valid API key."""
        provider = ZaiProvider()
        model = provider.create_model("glm-4.7-flash", max_tokens=10)

        assert model is not None
        assert model.model_name == "glm-4.7-flash"

    def test_validate_connection_with_valid_key(self):
        """Test that connection is valid with correct API key."""
        provider = ZaiProvider()
        is_valid, error = provider.validate_connection()

        assert is_valid is True
        assert error is None
