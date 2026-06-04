"""
MCP connector registry for managing connector discovery and instantiation.

This module provides a central registry for all MCP connectors,
allowing dynamic registration, lookup, and lifecycle management.
Enhanced with AllowlistValidator for governance (Task #68).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type

from core.security_utils import sanitize_for_log
from mcp.base import MCPConnector
from mcp.config import MCPConnectorConfig, MCPEdition
from mcp.exceptions import MCPConnectorNotFoundError, MCPNotAllowlistedError
from mcp.result import MCPConnectorResult

logger = logging.getLogger(__name__)


def _get_validator():
    """Lazy import to avoid circular dependency."""
    from mcp.allowlist_validator import get_allowlist_validator

    return get_allowlist_validator()


class MCPConnectorRegistry:
    """
    Central registry for MCP connectors.

    Manages connector registration, lookup, instantiation, and lifecycle.
    Implements the same pattern as AdapterRegistry for consistency.
    """

    _connectors: Dict[str, Type[MCPConnector]] = {}
    _instances: Dict[str, MCPConnector] = {}
    _configs: Dict[str, MCPConnectorConfig] = {}
    _allowlist: set[str] = set()
    _current_edition: MCPEdition = MCPEdition.COMMUNITY

    @classmethod
    def set_edition(cls, edition: MCPEdition) -> None:
        """
        Set the current application edition.

        Args:
            edition: The edition to set (COMMUNITY, PRO, ENTERPRISE)
        """
        cls._current_edition = edition
        logger.info("MCP registry edition set to: %s", sanitize_for_log(edition.value))

    @classmethod
    def load_allowlist_from_yaml(cls, config_path: Optional[str] = None) -> None:
        """
        Load allowlist from YAML configuration file.

        Args:
            config_path: Optional path to YAML file.
                        Falls back to MCP_ALLOWLIST_PATH env or default.
        """
        from pathlib import Path

        from mcp.allowlist_validator import AllowlistValidator

        path = Path(config_path) if config_path else None
        validator = AllowlistValidator(config_path=path)
        config = validator.load_config()

        # Sync internal allowlist with YAML config
        cls._allowlist = set(config.get_allowlist_names())
        cls._current_edition = config.edition

        logger.info(
            "Loaded allowlist from YAML: %s connectors, edition=%s",
            len(cls._allowlist),
            sanitize_for_log(config.edition.value),
        )

    @classmethod
    def get_edition(cls) -> MCPEdition:
        """Get the current application edition."""
        return cls._current_edition

    @classmethod
    def set_allowlist(cls, connector_names: List[str]) -> None:
        """
        Set the allowlist for Community Edition connectors.

        Args:
            connector_names: List of connector names to allowlist
        """
        cls._allowlist = set(connector_names)
        logger.info("MCP allowlist updated: %s connectors", len(cls._allowlist))

    @classmethod
    def add_to_allowlist(cls, connector_name: str) -> None:
        """
        Add a connector to the CE allowlist.

        Args:
            connector_name: Connector name to add
        """
        cls._allowlist.add(connector_name)

    @classmethod
    def remove_from_allowlist(cls, connector_name: str) -> None:
        """
        Remove a connector from the CE allowlist.

        Args:
            connector_name: Connector name to remove
        """
        cls._allowlist.discard(connector_name)

    @classmethod
    def is_allowlisted(cls, connector_name: str) -> bool:
        """Check if a connector is in the CE allowlist."""
        return connector_name in cls._allowlist

    @classmethod
    def register(
        cls,
        connector_class: Type[MCPConnector],
        config: Optional[MCPConnectorConfig] = None,
    ) -> None:
        """
        Register a connector class.

        Args:
            connector_class: Connector class to register
            config: Optional configuration for the connector

        Raises:
            ValueError: If connector name is missing
        """
        if not connector_class.name:
            raise ValueError("Connector must have a 'name' attribute")

        if connector_class.name in cls._connectors:
            logger.warning(
                "Connector '%s' already registered, overwriting",
                sanitize_for_log(connector_class.name),
            )

        cls._connectors[connector_class.name] = connector_class

        if config:
            cls._configs[connector_class.name] = config

        # Auto-add to allowlist if connector is marked as allowlisted
        if connector_class.allowlisted:
            cls._allowlist.add(connector_class.name)

        logger.info("Registered MCP connector: %s", sanitize_for_log(connector_class.name))

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a connector.

        Args:
            name: Connector name to unregister
        """
        if name in cls._connectors:
            del cls._connectors[name]
        if name in cls._instances:
            # Disconnect before removing
            instance = cls._instances[name]
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(instance.disconnect())
                else:
                    loop.run_until_complete(instance.disconnect())
            except Exception as e:
                logger.warning(
                    "Error disconnecting '%s': %s", sanitize_for_log(name), sanitize_for_log(e)
                )
            del cls._instances[name]
        if name in cls._configs:
            del cls._configs[name]
        logger.info("Unregistered MCP connector: %s", sanitize_for_log(name))

    @classmethod
    def get_connector(
        cls,
        name: str,
        config: Optional[MCPConnectorConfig] = None,
        skip_edition_check: bool = False,
    ) -> MCPConnector:
        """
        Get a connector instance by name.

        Args:
            name: Connector name
            config: Optional configuration override
            skip_edition_check: Skip edition/allowlist validation (for admin)

        Returns:
            Connector instance

        Raises:
            MCPConnectorNotFoundError: If connector not found
            MCPNotAllowlistedError: If connector not accessible in edition
        """
        connector_class = cls._connectors.get(name)
        if not connector_class:
            raise MCPConnectorNotFoundError(name)

        # Edition/allowlist check using AllowlistValidator
        if not skip_edition_check:
            validator = _get_validator()
            if not validator.validate_connector(name, cls._current_edition):
                # Log violation for audit
                validator.log_violation(
                    connector_name=name,
                    operation="get_connector",
                    context={"edition": cls._current_edition.value},
                )
                raise MCPNotAllowlistedError(name, cls._current_edition.value)

        # Return cached instance if available and no config override
        if name in cls._instances and config is None:
            return cls._instances[name]

        # Create new instance
        effective_config = config or cls._configs.get(name)
        try:
            instance = connector_class(config=effective_config)
            if config is None:
                cls._instances[name] = instance
            return instance
        except Exception as e:
            logger.error(
                "Failed to instantiate connector '%s': %s",
                sanitize_for_log(name),
                sanitize_for_log(e),
            )
            raise

    @classmethod
    def list_connectors(
        cls,
        include_non_accessible: bool = False,
    ) -> List[str]:
        """
        List all registered connector names.

        Args:
            include_non_accessible: Include connectors not accessible in current edition

        Returns:
            List of connector names
        """
        if include_non_accessible:
            return list(cls._connectors.keys())

        # Filter by edition accessibility
        accessible = []
        for name in cls._connectors:
            if cls._current_edition == MCPEdition.COMMUNITY:
                if cls.is_allowlisted(name):
                    accessible.append(name)
            else:
                accessible.append(name)
        return accessible

    @classmethod
    def get_connector_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a connector.

        Args:
            name: Connector name

        Returns:
            Dictionary with connector info or None if not found
        """
        connector_class = cls._connectors.get(name)
        if not connector_class:
            return None

        info: Dict[str, Any] = {
            "name": name,
            "display_name": connector_class.display_name,
            "description": connector_class.description,
            "requires_api_key": connector_class.requires_api_key,
            "allowlisted": cls.is_allowlisted(name),
            "accessible": (
                cls.is_allowlisted(name) if cls._current_edition == MCPEdition.COMMUNITY else True
            ),
            "min_edition": connector_class.min_edition.value,
            "supports_streaming": connector_class.supports_streaming,
        }

        # Include instance status if available
        if name in cls._instances:
            info["instance"] = cls._instances[name].get_status()

        return info

    @classmethod
    def get_all_info(cls, include_non_accessible: bool = False) -> List[Dict[str, Any]]:
        """
        Get information about all registered connectors.

        Args:
            include_non_accessible: Include connectors not accessible in current edition

        Returns:
            List of connector info dictionaries
        """
        result: List[Dict[str, Any]] = []
        for name in cls.list_connectors(include_non_accessible):
            info = cls.get_connector_info(name)
            if info is not None:
                result.append(info)
        return result

    @classmethod
    async def health_check_all(cls) -> Dict[str, MCPConnectorResult]:
        """
        Run health check on all instantiated connectors.

        Returns:
            Dictionary mapping connector names to health check results
        """
        results: Dict[str, MCPConnectorResult] = {}
        for name, instance in cls._instances.items():
            try:
                results[name] = await instance.health_check()
            except Exception as e:
                results[name] = MCPConnectorResult.error_result(
                    errors=[str(e)],
                    connector_name=name,
                    operation="health_check",
                )
        return results

    @classmethod
    def clear(cls) -> None:
        """Clear all registered connectors (for testing)."""
        cls._connectors.clear()
        cls._instances.clear()
        cls._configs.clear()
        # Don't clear allowlist - preserve for tests

    @classmethod
    def get_allowlist_violations(cls) -> List[Dict[str, Any]]:
        """
        Get all logged allowlist violations for audit.

        Returns:
            List of violation records with timestamps and context
        """
        validator = _get_validator()
        return validator.get_violations()  # type: ignore[no-any-return]

    @classmethod
    def clear_allowlist_violations(cls) -> None:
        """Clear all logged allowlist violations."""
        validator = _get_validator()
        validator.clear_violations()

    @classmethod
    def reload_allowlist(cls) -> None:
        """Reload allowlist configuration from YAML file."""
        validator = _get_validator()
        config = validator.reload_config()
        cls._allowlist = set(config.get_allowlist_names())
        cls._current_edition = config.edition
        logger.info("Reloaded allowlist: %s connectors", len(cls._allowlist))


def register_mcp_connector(
    connector_class: Type[MCPConnector],
) -> Type[MCPConnector]:
    """
    Decorator to register a connector class.

    Usage:
        @register_mcp_connector
        class MyConnector(MCPConnector):
            name = "my_connector"
            ...
    """
    MCPConnectorRegistry.register(connector_class)
    return connector_class


def get_mcp_connector(
    name: str,
    config: Optional[MCPConnectorConfig] = None,
) -> MCPConnector:
    """
    Convenience function to get a connector instance.

    Args:
        name: Connector name
        config: Optional configuration

    Returns:
        Connector instance
    """
    return MCPConnectorRegistry.get_connector(name, config=config)
