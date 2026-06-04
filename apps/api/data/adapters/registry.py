"""
Adapter registry for managing external source adapters.

This module provides a central registry for all portal adapters,
allowing dynamic registration and lookup.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type

from core.security_utils import sanitize_for_log
from data.adapters.base import ExternalSourceAdapter
from utils.sanitization import sanitize_for_logging

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Central registry for external source adapters.

    Manages adapter registration, lookup, and lifecycle.
    """

    _adapters: Dict[str, Type[ExternalSourceAdapter]] = {}
    _instances: Dict[str, ExternalSourceAdapter] = {}

    @classmethod
    def register(cls, adapter_class: Type[ExternalSourceAdapter]) -> None:
        """
        Register an adapter class.

        Args:
            adapter_class: Adapter class to register

        Raises:
            ValueError: If adapter name is already registered
        """
        if not adapter_class.name:
            raise ValueError("Adapter must have a 'name' attribute")

        if adapter_class.name in cls._adapters:
            logger.warning(
                "Adapter '%s' already registered, overwriting", sanitize_for_log(adapter_class.name)
            )

        cls._adapters[adapter_class.name] = adapter_class
        logger.info("Registered adapter: %s", sanitize_for_log(adapter_class.name))

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister an adapter.

        Args:
            name: Adapter name to unregister
        """
        if name in cls._adapters:
            del cls._adapters[name]
        if name in cls._instances:
            del cls._instances[name]
        logger.info("Unregistered adapter: %s", sanitize_for_log(name))

    @classmethod
    def get_adapter(
        cls, name: str, api_key: Optional[str] = None
    ) -> Optional["ExternalSourceAdapter"]:
        """
        Get an adapter instance by name.

        Args:
            name: Adapter name
            api_key: Optional API key to override environment variable

        Returns:
            Adapter instance or None if not found
        """
        adapter_class = cls._adapters.get(name)
        if not adapter_class:
            logger.warning("Adapter '%s' not found in registry", sanitize_for_log(name))
            return None

        # Return cached instance if available and api_key not provided
        if name in cls._instances and api_key is None:
            return cls._instances[name]

        try:
            instance = adapter_class(api_key=api_key)
            if api_key is None:
                cls._instances[name] = instance
            return instance
        except Exception as e:
            logger.error(
                "Failed to instantiate adapter '%s': %s",
                sanitize_for_log(sanitize_for_logging(name)),
                sanitize_for_log(sanitize_for_logging(e)),
            )
            return None

    @classmethod
    def list_adapters(cls) -> List[str]:
        """
        List all registered adapter names.

        Returns:
            List of adapter names
        """
        return list(cls._adapters.keys())

    @classmethod
    def get_adapter_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an adapter.

        Args:
            name: Adapter name

        Returns:
            Dictionary with adapter info or None if not found
        """
        adapter_class = cls._adapters.get(name)
        if not adapter_class:
            return None

        instance = cls.get_adapter(name)
        if not instance:
            return {
                "name": name,
                "display_name": adapter_class.display_name,
                "requires_api_key": adapter_class.requires_api_key,
                "configured": False,
            }

        return instance.get_status()

    @classmethod
    def get_all_info(cls) -> List[Dict[str, Any]]:
        """
        Get information about all registered adapters.

        Returns:
            List of adapter info dictionaries
        """
        result: List[Dict[str, Any]] = []
        for name in cls.list_adapters():
            info = cls.get_adapter_info(name)
            if info is not None:
                result.append(info)
        return result

    @classmethod
    def clear(cls) -> None:
        """Clear all registered adapters (for testing)."""
        cls._adapters.clear()
        cls._instances.clear()


def register_adapter(
    adapter_class: Type[ExternalSourceAdapter],
) -> (
    Type[ExternalSourceAdapter]
    | Callable[[Type[ExternalSourceAdapter]], Type[ExternalSourceAdapter]]
):
    """
    Decorator to register an adapter class.

    Usage:
        @register_adapter
        class MyAdapter(ExternalSourceAdapter):
            name = "my_adapter"
            ...
    """

    def wrapper(cls: Type[ExternalSourceAdapter]) -> Type[ExternalSourceAdapter]:
        AdapterRegistry.register(cls)
        return cls

    return wrapper(adapter_class) if hasattr(adapter_class, "name") else wrapper


def get_adapter(name: str, api_key: Optional[str] = None) -> Optional[ExternalSourceAdapter]:
    """
    Convenience function to get an adapter instance.

    Args:
        name: Adapter name
        api_key: Optional API key

    Returns:
        Adapter instance or None if not found
    """
    return AdapterRegistry.get_adapter(name, api_key=api_key)
