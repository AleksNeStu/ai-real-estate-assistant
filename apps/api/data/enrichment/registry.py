"""
Enrichment Registry (Task #78).

This module provides a central registry for all property enrichment providers,
following the AdapterRegistry pattern from apps/api/data/adapters/registry.py.

Features:
- Decorator-based auto-registration
- Instance caching for performance
- Configuration management
- Discovery and listing capabilities
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type

from core.security_utils import sanitize_for_log
from data.enrichment.hooks import EnrichmentConfig, EnrichmentPriority, PropertyEnrichmentHook

logger = logging.getLogger(__name__)


class EnrichmentRegistry:
    """
    Central registry for property enrichment providers.

    Manages enricher registration, lookup, and lifecycle.
    Follows the AdapterRegistry pattern for consistency.
    """

    _enrichers: Dict[str, Type[PropertyEnrichmentHook]] = {}
    _instances: Dict[str, PropertyEnrichmentHook] = {}
    _configs: Dict[str, EnrichmentConfig] = {}
    _priorities: Dict[str, EnrichmentPriority] = {}

    @classmethod
    def register(
        cls,
        enricher_class: Type[PropertyEnrichmentHook],
        config: Optional[EnrichmentConfig] = None,
    ) -> None:
        """
        Register an enricher class.

        Args:
            enricher_class: Enricher class to register
            config: Optional custom configuration

        Raises:
            ValueError: If enricher name is already registered
        """
        if not enricher_class.name:
            raise ValueError("Enricher must have a 'name' attribute")

        if enricher_class.name in cls._enrichers:
            logger.warning(
                "Enricher '%s' already registered, overwriting",
                sanitize_for_log(enricher_class.name),
            )

        cls._enrichers[enricher_class.name] = enricher_class
        cls._priorities[enricher_class.name] = enricher_class.priority

        if config:
            cls._configs[enricher_class.name] = config

        logger.info("Registered enricher: %s", sanitize_for_log(enricher_class.name))

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister an enricher.

        Args:
            name: Enricher name to unregister
        """
        if name in cls._enrichers:
            del cls._enrichers[name]
        if name in cls._instances:
            del cls._instances[name]
        if name in cls._configs:
            del cls._configs[name]
        if name in cls._priorities:
            del cls._priorities[name]
        logger.info("Unregistered enricher: %s", sanitize_for_log(name))

    @classmethod
    def get_enricher(
        cls,
        name: str,
        config: Optional[EnrichmentConfig] = None,
    ) -> Optional[PropertyEnrichmentHook]:
        """
        Get an enricher instance by name.

        Args:
            name: Enricher name
            config: Optional configuration override

        Returns:
            Enricher instance or None if not found
        """
        enricher_class = cls._enrichers.get(name)
        if not enricher_class:
            logger.warning("Enricher '%s' not found in registry", sanitize_for_log(name))
            return None

        # Return cached instance if available and no custom config
        if name in cls._instances and config is None:
            return cls._instances[name]

        try:
            # Use provided config, then stored config, then default
            effective_config = config or cls._configs.get(name)
            instance = enricher_class(config=effective_config)

            # Cache instance if using stored/default config
            if config is None:
                cls._instances[name] = instance

            return instance
        except Exception as e:
            logger.error(
                "Failed to instantiate enricher '%s': %s",
                sanitize_for_log(name),
                sanitize_for_log(e),
            )
            return None

    @classmethod
    def list_enrichers(cls) -> List[str]:
        """
        List all registered enricher names.

        Returns:
            List of enricher names
        """
        return list(cls._enrichers.keys())

    @classmethod
    def list_enrichers_by_priority(cls) -> List[str]:
        """
        List enricher names sorted by priority (lowest first = runs first).

        Returns:
            List of enricher names sorted by priority
        """
        return sorted(cls._priorities.keys(), key=lambda x: cls._priorities[x].value)

    @classmethod
    def get_enricher_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an enricher.

        Args:
            name: Enricher name

        Returns:
            Dictionary with enricher info or None if not found
        """
        enricher_class = cls._enrichers.get(name)
        if not enricher_class:
            return None

        instance = cls.get_enricher(name)
        if not instance:
            return {
                "name": name,
                "display_name": enricher_class.display_name,
                "description": enricher_class.description,
                "field": enricher_class.field,
                "requires_api_key": enricher_class.requires_api_key,
                "configured": False,
                "enabled": False,
            }

        return instance.get_status()

    @classmethod
    def get_all_info(cls) -> List[Dict[str, Any]]:
        """
        Get information about all registered enrichers.

        Returns:
            List of enricher info dictionaries
        """
        result: List[Dict[str, Any]] = []
        for name in cls.list_enrichers():
            info = cls.get_enricher_info(name)
            if info is not None:
                result.append(info)
        return result

    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """
        Check if an enricher is enabled.

        Args:
            name: Enricher name

        Returns:
            True if enricher is enabled
        """
        # Check stored config first
        if name in cls._configs:
            return cls._configs[name].enabled

        # Check instance config
        instance = cls._instances.get(name)
        if instance:
            return instance.is_enabled()

        # Default to class default
        enricher_class = cls._enrichers.get(name)
        if enricher_class:
            return True  # Default is enabled

        return False

    @classmethod
    def set_config(cls, name: str, config: EnrichmentConfig) -> None:
        """
        Set configuration for an enricher.

        Args:
            name: Enricher name
            config: Configuration to set
        """
        cls._configs[name] = config

        # Invalidate cached instance to pick up new config
        if name in cls._instances:
            del cls._instances[name]

        logger.info("Updated config for enricher: %s", sanitize_for_log(name))

    @classmethod
    def get_config(cls, name: str) -> Optional[EnrichmentConfig]:
        """
        Get configuration for an enricher.

        Args:
            name: Enricher name

        Returns:
            Configuration or None if not set
        """
        return cls._configs.get(name)

    @classmethod
    def get_all_enrichers(
        cls,
        enabled_only: bool = True,
    ) -> List[PropertyEnrichmentHook]:
        """
        Get all registered enricher instances.

        Args:
            enabled_only: If True, only return enabled enrichers

        Returns:
            List of enricher instances
        """
        enrichers: List[PropertyEnrichmentHook] = []

        for name in cls.list_enrichers_by_priority():
            if enabled_only and not cls.is_enabled(name):
                continue

            instance = cls.get_enricher(name)
            if instance:
                enrichers.append(instance)

        return enrichers

    @classmethod
    def clear(cls) -> None:
        """Clear all registered enrichers (for testing)."""
        cls._enrichers.clear()
        cls._instances.clear()
        cls._configs.clear()
        cls._priorities.clear()


def register_enricher(
    enricher_class: Optional[Type[PropertyEnrichmentHook]] = None,
    *,
    config: Optional[EnrichmentConfig] = None,
) -> (
    Type[PropertyEnrichmentHook]
    | Callable[[Type[PropertyEnrichmentHook]], Type[PropertyEnrichmentHook]]
):
    """
    Decorator to register an enricher class.

    Usage:
        @register_enricher
        class MyEnricher(PropertyEnrichmentHook):
            name = "my_enricher"
            field = "my_field"
            ...

        # Or with custom config:
        @register_enricher(config=EnrichmentConfig(ttl_seconds=7200))
        class MyEnricher(PropertyEnrichmentHook):
            ...
    """

    def wrapper(
        cls: Type[PropertyEnrichmentHook],
    ) -> Type[PropertyEnrichmentHook]:
        EnrichmentRegistry.register(cls, config=config)
        return cls

    # Support both @register_enricher and @register_enricher(config=...)
    if enricher_class is not None:
        return wrapper(enricher_class)
    return wrapper


def get_enricher(
    name: str,
    config: Optional[EnrichmentConfig] = None,
) -> Optional[PropertyEnrichmentHook]:
    """
    Convenience function to get an enricher instance.

    Args:
        name: Enricher name
        config: Optional configuration override

    Returns:
        Enricher instance or None if not found
    """
    return EnrichmentRegistry.get_enricher(name, config=config)
