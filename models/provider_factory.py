"""
Model provider factory for creating and managing LLM providers.

This module provides a unified interface for accessing different model providers
and their models.
"""

from typing import Dict, List, Optional, Type
from .providers.base import ModelProvider, ModelInfo
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider
from .providers.google import GoogleProvider
from .providers.ollama import OllamaProvider


class ModelProviderFactory:
    """
    Factory for creating and managing model providers.

    This class provides a centralized way to access all available providers
    and their models.
    """

    # Registry of available providers
    _PROVIDERS: Dict[str, Type[ModelProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "ollama": OllamaProvider,
    }

    # Cache of instantiated providers
    _instances: Dict[str, ModelProvider] = {}

    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List all available provider names.

        Returns:
            List of provider names (e.g., ['openai', 'anthropic', ...])
        """
        return list(cls._PROVIDERS.keys())

    @classmethod
    def get_provider(
        cls,
        provider_name: str,
        config: Optional[Dict] = None,
        use_cache: bool = True
    ) -> ModelProvider:
        """
        Get a provider instance by name.

        Args:
            provider_name: Name of the provider (e.g., 'openai', 'anthropic')
            config: Optional configuration dictionary
            use_cache: Whether to use cached instances (default: True)

        Returns:
            ModelProvider instance

        Raises:
            ValueError: If provider_name is not recognized
        """
        if provider_name not in cls._PROVIDERS:
            available = ", ".join(cls.list_providers())
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {available}"
            )

        # Check cache
        if use_cache and provider_name in cls._instances:
            return cls._instances[provider_name]

        # Create new instance
        provider_class = cls._PROVIDERS[provider_name]
        provider = provider_class(config=config)

        # Cache if requested
        if use_cache:
            cls._instances[provider_name] = provider

        return provider

    @classmethod
    def list_all_models(cls, include_unavailable: bool = True) -> List[ModelInfo]:
        """
        List all available models from all providers.

        Args:
            include_unavailable: Whether to include models from providers
                                 with connection issues

        Returns:
            List of ModelInfo objects from all providers
        """
        all_models = []

        for provider_name in cls.list_providers():
            try:
                provider = cls.get_provider(provider_name)

                # Check connection if requested
                if not include_unavailable:
                    is_valid, error = provider.validate_connection()
                    if not is_valid:
                        continue

                models = provider.list_models()
                all_models.extend(models)

            except Exception as e:
                print(f"Warning: Could not load models from {provider_name}: {e}")
                continue

        return all_models

    @classmethod
    def get_model_by_id(cls, model_id: str) -> Optional[tuple[ModelProvider, ModelInfo]]:
        """
        Find a model by its ID across all providers.

        Args:
            model_id: Model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')

        Returns:
            Tuple of (provider, model_info) if found, None otherwise
        """
        for provider_name in cls.list_providers():
            try:
                provider = cls.get_provider(provider_name)
                model_info = provider.get_model_info(model_id)

                if model_info:
                    return provider, model_info

            except Exception:
                continue

        return None

    @classmethod
    def create_model(
        cls,
        model_id: str,
        provider_name: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        **kwargs
    ):
        """
        Create a model instance by ID.

        Args:
            model_id: Model identifier
            provider_name: Optional provider name (auto-detected if not provided)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            streaming: Whether to enable streaming
            **kwargs: Additional model-specific parameters

        Returns:
            Configured LangChain chat model instance

        Raises:
            ValueError: If model not found or provider not available
        """
        # If provider specified, use it directly
        if provider_name:
            provider = cls.get_provider(provider_name)
            return provider.create_model(
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                **kwargs
            )

        # Auto-detect provider
        result = cls.get_model_by_id(model_id)
        if not result:
            raise ValueError(
                f"Model '{model_id}' not found in any provider. "
                f"Available providers: {', '.join(cls.list_providers())}"
            )

        provider, model_info = result
        return provider.create_model(
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            **kwargs
        )

    @classmethod
    def get_available_providers(cls) -> List[tuple[str, bool, Optional[str]]]:
        """
        Get list of providers with their availability status.

        Returns:
            List of tuples: (provider_name, is_available, error_message)
        """
        results = []

        for provider_name in cls.list_providers():
            try:
                provider = cls.get_provider(provider_name)
                is_valid, error = provider.validate_connection()
                results.append((provider_name, is_valid, error))

            except Exception as e:
                results.append((provider_name, False, str(e)))

        return results

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: Type[ModelProvider]
    ):
        """
        Register a custom provider.

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from ModelProvider)
        """
        if not issubclass(provider_class, ModelProvider):
            raise TypeError("Provider class must inherit from ModelProvider")

        cls._PROVIDERS[name] = provider_class

        # Clear cache for this provider if it exists
        if name in cls._instances:
            del cls._instances[name]

    @classmethod
    def clear_cache(cls):
        """Clear all cached provider instances."""
        cls._instances.clear()


def get_model_display_info(model_info: ModelInfo) -> Dict:
    """
    Get formatted display information for a model.

    Args:
        model_info: ModelInfo object

    Returns:
        Dictionary with formatted display information
    """
    info = {
        "name": model_info.display_name,
        "id": model_info.id,
        "provider": model_info.provider_name,
        "context": f"{model_info.context_window:,} tokens",
        "capabilities": [c.value for c in model_info.capabilities],
    }

    if model_info.pricing:
        info["cost"] = (
            f"${model_info.pricing.input_price_per_1m:.2f} / "
            f"${model_info.pricing.output_price_per_1m:.2f} per 1M tokens"
        )
    else:
        info["cost"] = "Free (local)"

    if model_info.description:
        info["description"] = model_info.description

    if model_info.recommended_for:
        info["recommended_for"] = model_info.recommended_for

    return info
