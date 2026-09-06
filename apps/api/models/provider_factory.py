"""
Model provider factory for creating and managing LLM providers.

This module provides a unified interface for accessing different model
providers and their models.

Memory note
-----------
On Render free tier (512 MB hard limit) the app baseline sits ~20 MB
over the cap because every provider module (``langchain_openai``,
``langchain_anthropic``, ``langchain_google_genai``, etc.) is imported
eagerly at startup — even when only one provider (``zai``) is in use.
The OS kills the instance on the first memory spike.

To stay on free tier without changing the public deployment plan, we
load provider modules lazily when running on Render. The Render
service sets ``RENDER=true`` automatically; locally and on other PaaS
providers the eager path is preserved (no behavior change, no
surprise in tests or local dev).
"""

import importlib
import logging
import os
from typing import Any, Dict, List, Optional, Type

from langchain_core.language_models import BaseChatModel

from config.settings import settings

# Base provider class is needed for type checks and is cheap to import.
from .providers.base import ModelInfo, ModelProvider

logger = logging.getLogger(__name__)

# Detect Render environment for lazy-loading optimization.
# Render sets RENDER=true automatically on all its services. Locally
# and on other PaaS, this env var is unset/false, so we use the
# fast eager-import path (no behavior change in dev / CI / other
# deployments).
IS_RENDER = os.environ.get("RENDER") == "true"


def _class_name_for(provider: str) -> str:
    """Map provider slug to its expected class name.

    Convention in this repo: ``models/providers/<slug>.py`` defines
    ``<Capitalized>Provider``. Most providers follow a simple
    first-letter-uppercase rule, but a few have brand-style casing
    (e.g. ``OpenAI`` not ``Openai``); those live in
    ``_CLASS_NAME_OVERRIDES``.
    """
    if provider in _CLASS_NAME_OVERRIDES:
        return _CLASS_NAME_OVERRIDES[provider]
    return provider[0].upper() + provider[1:] + "Provider"


# Providers whose class name doesn't follow the simple
# "Capitalize(slug) + 'Provider'" rule. Keys are slugs, values are
# the exact class name defined in models/providers/<slug>.py.
_CLASS_NAME_OVERRIDES: Dict[str, str] = {
    "openai": "OpenAIProvider",  # not "OpenaiProvider"
    "deepseek": "DeepSeekProvider",  # not "DeepseekProvider"
    "openrouter": "OpenRouterProvider",  # not "OpenrouterProvider"
    "opencode": "OpenCodeProvider",  # not "OpencodeProvider"
}


# Provider slug -> module path (relative to apps/api). Module is loaded
# lazily on first use on Render, eagerly on other environments.
_PROVIDER_MODULES: Dict[str, str] = {
    "openai": "models.providers.openai",
    "anthropic": "models.providers.anthropic",
    "google": "models.providers.google",
    "grok": "models.providers.grok",
    "deepseek": "models.providers.deepseek",
    "openrouter": "models.providers.openrouter",
    "groq": "models.providers.groq",
    "mistral": "models.providers.mistral",
    "qwen": "models.providers.qwen",
    "zai": "models.providers.zai",
    "moonshot": "models.providers.moonshot",
    "opencode": "models.providers.opencode",
    "ollama": "models.providers.ollama",
}
_PROVIDER_CLASS_NAMES: Dict[str, str] = {
    name: _class_name_for(name) for name in _PROVIDER_MODULES
}


def _load_provider_class(name: str) -> Type[ModelProvider]:
    """Import a provider module and return its provider class.

    Caches the class in ``_PROVIDERS`` so subsequent calls skip the
    import overhead.
    """
    if name in _PROVIDERS:
        return _PROVIDERS[name]
    module_path = _PROVIDER_MODULES.get(name)
    if module_path is None:
        available = ", ".join(_PROVIDER_MODULES.keys())
        raise ValueError(
            f"Unknown provider '{name}'. Available providers: {available}"
        )
    class_name = _PROVIDER_CLASS_NAMES[name]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    _PROVIDERS[name] = cls
    return cls


# Provider slug -> settings attribute for API key lookup
_PROVIDER_KEY_MAP: Dict[str, Optional[str]] = {
    "openai": settings.openai_api_key,
    "anthropic": settings.anthropic_api_key,
    "google": settings.google_api_key,
    "grok": settings.grok_api_key,
    "deepseek": settings.deepseek_api_key,
    "openrouter": settings.openrouter_api_key,
    "groq": settings.groq_api_key,
    "mistral": settings.mistral_api_key,
    "qwen": settings.qwen_api_key,
    "zai": settings.zhipuai_api_key,
    "moonshot": settings.moonshot_api_key,
    "opencode": settings.opencode_api_key,
}


def _bootstrap_providers_eager() -> None:
    """Pre-import every provider module. Used on non-Render environments."""
    for name in _PROVIDER_MODULES:
        _load_provider_class(name)


# Registry of available providers. Populated eagerly on import outside
# Render, lazily on first ``get_provider`` call on Render.
_PROVIDERS: Dict[str, Type[ModelProvider]] = {}

# Cache of instantiated providers
_instances: Dict[str, ModelProvider] = {}


# Eager load only when not on Render. Local dev / CI / other PaaS
# keeps the original behavior so existing tests and DX are unchanged.
if not IS_RENDER:
    _bootstrap_providers_eager()


class ModelProviderFactory:
    """
    Factory for creating and managing model providers.

    This class provides a centralized way to access all available providers
    and their models.
    """

    # Class-level aliases for backward compatibility with tests and
    # callers that reference these as class attributes. The aliases
    # point to the same module-level dicts, so ``patch.dict`` on the
    # class attribute mutates the shared dict (and vice versa).
    _PROVIDERS = _PROVIDERS  # type: ignore[assignment]
    _PROVIDER_MODULES = _PROVIDER_MODULES  # type: ignore[assignment]
    _PROVIDER_KEY_MAP = _PROVIDER_KEY_MAP  # type: ignore[assignment]
    _instances = _instances  # type: ignore[assignment]

    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List all available provider names.

        Returns:
            List of provider names (e.g., ['openai', 'anthropic', ...])
        """
        return list(_PROVIDER_MODULES.keys())

    @classmethod
    def get_provider(
        cls, provider_name: str, config: Optional[Dict[str, Any]] = None, use_cache: bool = True
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
        if provider_name not in _PROVIDER_MODULES:
            available = ", ".join(cls.list_providers())
            raise ValueError(
                f"Unknown provider '{provider_name}'. Available providers: {available}"
            )

        # Check cache
        if use_cache and provider_name in _instances:
            # If config is provided, we might want to update the cached instance or create a new one.
            # For now, we assume cached instances are reused unless explicit new config is needed.
            # If config is passed, we skip cache to ensure config is applied.
            if config is None:
                return _instances[provider_name]

        # Prepare config with defaults from settings
        if config is None:
            config = {}

        # Inject API key from settings if not present
        if "api_key" not in config:
            api_key = _PROVIDER_KEY_MAP.get(provider_name)
            if api_key:
                config["api_key"] = api_key

        # Create new instance (triggers lazy module load on Render)
        provider_class = _load_provider_class(provider_name)
        provider = provider_class(config=config)

        # Cache if requested
        if use_cache:
            _instances[provider_name] = provider

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
                # Use cached provider (will use settings API keys)
                provider = cls.get_provider(provider_name)

                # Check connection if requested
                if not include_unavailable:
                    is_valid, error = provider.validate_connection()
                    if not is_valid:
                        continue

                models = provider.list_models()
                all_models.extend(models)

            except Exception as e:
                logger.warning("Could not load models from %s: %s", provider_name, e)
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
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        **kwargs: Any,
    ) -> BaseChatModel:
        """
        Create a model instance by ID.

        Args:
            model_id: Model identifier
            provider_name: Optional provider name (auto-detected if not provided)
            temperature: Temperature for generation
            max_tokens: Maximum number of tokens to generate
            streaming: Whether to enable streaming
            **kwargs: Additional model-specific parameters

        Returns:
            Configured LangChain chat model instance

        Raises:
            ValueError: If model not found or provider not available
        """
        # Apply defaults from settings if not provided
        if temperature is None:
            temperature = settings.default_temperature

        if max_tokens is None:
            max_tokens = settings.default_max_tokens

        # If provider specified, use it directly
        if provider_name:
            provider = cls.get_provider(provider_name)
            return provider.create_model(
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                **kwargs,
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
            **kwargs,
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
    def register_provider(cls, name: str, provider_class: Type[ModelProvider]) -> None:
        """
        Register a custom provider.

        Args:
            name: Name of the provider
            provider_class: Provider class (must inherit from ModelProvider)
        """
        if not issubclass(provider_class, ModelProvider):
            raise TypeError("Provider class must inherit from ModelProvider")

        _PROVIDERS[name] = provider_class

        # Clear cache for this provider if it exists
        if name in _instances:
            del _instances[name]
        return None

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached provider instances."""
        _instances.clear()
        return None


def get_model_display_info(model_info: ModelInfo) -> Dict[str, Any]:
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
