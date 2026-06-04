"""
MCP Allowlist Validator.

Provides structured validation and loading of allowlist configuration
from YAML file with environment variable fallback.

This module implements the governance layer for MCP connectors:
- YAML-based configuration for external management
- Edition-based access control
- Audit logging for compliance
- Admin API support for runtime management
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml  # type: ignore[import-untyped]

from core.security_utils import sanitize_for_log
from mcp.config import MCPEdition
from mcp.exceptions import MCPConfigError

logger = logging.getLogger(__name__)


@dataclass
class AllowlistEntry:
    """
    Represents a single allowlist entry.

    Attributes:
        name: Unique connector identifier
        display_name: Human-readable name for UI
        description: Connector purpose description
        enabled: Whether this entry is active
        edition: Edition level for this connector
        added_at: Timestamp when added
        added_by: Who added this entry
    """

    name: str
    display_name: str
    description: str = ""
    enabled: bool = True
    edition: MCPEdition = MCPEdition.COMMUNITY
    added_at: datetime = field(default_factory=datetime.utcnow)
    added_by: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for API responses."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "enabled": self.enabled,
            "edition": self.edition.value,
            "added_at": self.added_at.isoformat(),
            "added_by": self.added_by,
        }


@dataclass
class AllowlistConfig:
    """
    Complete allowlist configuration loaded from YAML.

    Attributes:
        edition: Current application edition
        allowlist: List of allowed connectors
        restricted: List of restricted connectors (higher tier)
        metadata: Configuration metadata
        loaded_at: When configuration was loaded
        config_path: Path to the YAML file
    """

    edition: MCPEdition = MCPEdition.COMMUNITY
    allowlist: List[AllowlistEntry] = field(default_factory=list)
    restricted: List[AllowlistEntry] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    loaded_at: datetime = field(default_factory=datetime.utcnow)
    config_path: Optional[Path] = None

    def get_allowlist_names(self) -> List[str]:
        """Get list of allowlisted connector names (enabled only)."""
        return [e.name for e in self.allowlist if e.enabled]

    def is_allowlisted(self, name: str) -> bool:
        """Check if a connector is in the allowlist and enabled."""
        return name in self.get_allowlist_names()

    def get_entry(self, name: str) -> Optional[AllowlistEntry]:
        """Get allowlist entry by name."""
        for entry in self.allowlist:
            if entry.name == name:
                return entry
        return None

    def get_restricted_entry(self, name: str) -> Optional[AllowlistEntry]:
        """Get restricted entry by name."""
        for entry in self.restricted:
            if entry.name == name:
                return entry
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for API responses."""
        return {
            "edition": self.edition.value,
            "allowlist": [e.to_dict() for e in self.allowlist],
            "restricted": [e.to_dict() for e in self.restricted],
            "metadata": self.metadata,
            "loaded_at": self.loaded_at.isoformat(),
            "config_path": str(self.config_path) if self.config_path else None,
        }


class AllowlistValidator:
    """
    Validates MCP connectors against allowlist configuration.

    Loads configuration from YAML file with environment variable fallback.
    Provides validation on connector registration and instantiation.

    Features:
    - YAML-based configuration for external management
    - Edition-based access control (CE, PRO, Enterprise)
    - Audit logging for compliance monitoring
    - Runtime allowlist management via admin API

    Usage:
        validator = AllowlistValidator()
        if validator.validate_connector("my_connector", MCPEdition.COMMUNITY):
            connector = get_connector("my_connector")
    """

    DEFAULT_CONFIG_PATH = Path("config/mcp_allowlist.yaml")

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the validator.

        Args:
            config_path: Optional path to YAML config file.
                        Falls back to MCP_ALLOWLIST_PATH env var,
                        then DEFAULT_CONFIG_PATH.
        """
        # Resolve config path: parameter > env > default
        if config_path:
            self.config_path = config_path
        else:
            env_path = os.getenv("MCP_ALLOWLIST_PATH")
            self.config_path = Path(env_path) if env_path else self.DEFAULT_CONFIG_PATH

        self._config: Optional[AllowlistConfig] = None
        self._violations: List[Dict[str, Any]] = []

    def load_config(self) -> AllowlistConfig:
        """
        Load allowlist configuration from YAML file.

        Returns:
            AllowlistConfig with parsed configuration

        Raises:
            MCPConfigError: If YAML parsing fails
        """
        if not self.config_path.exists():
            logger.warning(
                "Allowlist config not found: %s, using defaults", sanitize_for_log(self.config_path)
            )
            return self._get_default_config()

        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning("Empty allowlist config: %s", sanitize_for_log(self.config_path))
                return self._get_default_config()

            # Parse edition
            edition_str = data.get("edition", "community").lower()
            try:
                edition = MCPEdition(edition_str)
            except ValueError:
                logger.warning(
                    "Invalid edition '%s', defaulting to community", sanitize_for_log(edition_str)
                )
                edition = MCPEdition.COMMUNITY

            # Parse allowlist entries
            allowlist = self._parse_entries(data.get("allowlist", []), "allowlist")

            # Parse restricted entries
            restricted = self._parse_restricted(data.get("restricted", []))

            self._config = AllowlistConfig(
                edition=edition,
                allowlist=allowlist,
                restricted=restricted,
                metadata=data.get("metadata", {}),
                config_path=self.config_path,
            )

            logger.info(
                "Loaded allowlist config: %s allowed, %s restricted",
                len(allowlist),
                len(restricted),
            )
            return self._config

        except yaml.YAMLError as e:
            logger.error(
                "YAML parsing error in %s: %s",
                sanitize_for_log(self.config_path),
                sanitize_for_log(e),
            )
            raise MCPConfigError(f"Invalid YAML in allowlist config: {e}") from e
        except Exception as e:
            logger.error("Failed to load allowlist config: %s", sanitize_for_log(e))
            raise MCPConfigError(f"Failed to load allowlist config: {e}") from e

    def _parse_entries(
        self, entries_data: List[Dict[str, Any]], source: str
    ) -> List[AllowlistEntry]:
        """Parse allowlist entries from YAML data."""
        entries = []
        for entry_data in entries_data:
            if not isinstance(entry_data, dict):
                logger.warning(
                    "Invalid entry in %s: %s",
                    sanitize_for_log(source),
                    sanitize_for_log(entry_data),
                )
                continue

            name = entry_data.get("name")
            if not name:
                logger.warning("Entry missing 'name' in %s", sanitize_for_log(source))
                continue

            edition_str = entry_data.get("edition", "community")
            try:
                entry_edition = MCPEdition(edition_str.lower())
            except ValueError:
                entry_edition = MCPEdition.COMMUNITY

            entry = AllowlistEntry(
                name=name,
                display_name=entry_data.get("display_name", name) or name,  # type: ignore[arg-type]
                description=entry_data.get("description", ""),
                enabled=entry_data.get("enabled", True),
                edition=entry_edition,
            )
            entries.append(entry)

        return entries

    def _parse_restricted(self, entries_data: List[Dict[str, Any]]) -> List[AllowlistEntry]:
        """Parse restricted entries from YAML data."""
        entries = []
        for entry_data in entries_data:
            if not isinstance(entry_data, dict):
                continue

            name = entry_data.get("name")
            if not name:
                continue

            min_edition_str = entry_data.get("min_edition", "pro")
            try:
                entry_edition = MCPEdition(min_edition_str.lower())
            except ValueError:
                entry_edition = MCPEdition.PRO

            entry = AllowlistEntry(
                name=name,
                display_name=entry_data.get("display_name", name) or name,  # type: ignore[arg-type]
                description=entry_data.get("description", ""),
                enabled=entry_data.get("enabled", True),
                edition=entry_edition,
            )
            entries.append(entry)

        return entries

    def _get_default_config(self) -> AllowlistConfig:
        """Get default configuration when YAML file not found."""
        return AllowlistConfig(
            edition=MCPEdition.COMMUNITY,
            allowlist=[
                AllowlistEntry(
                    name="echo_stub",
                    display_name="Echo Stub (Testing)",
                    description="Testing connector - no external API calls",
                    edition=MCPEdition.COMMUNITY,
                )
            ],
            restricted=[],
            config_path=None,
        )

    @property
    def config(self) -> AllowlistConfig:
        """Get current configuration (lazy loaded)."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def reload_config(self) -> AllowlistConfig:
        """Force reload configuration from file."""
        self._config = None
        return self.load_config()

    def validate_connector(self, name: str, current_edition: MCPEdition) -> bool:
        """
        Validate if a connector can be used in the current edition.

        Args:
            name: Connector name to validate
            current_edition: Current application edition

        Returns:
            True if connector is accessible, False otherwise
        """
        config = self.config

        # In non-CE editions, all connectors are accessible
        if current_edition != MCPEdition.COMMUNITY:
            logger.debug(
                "Connector '%s' accessible in %s edition (non-CE)",
                sanitize_for_log(name),
                sanitize_for_log(current_edition.value),
            )
            return True

        # Check if in allowlist
        if config.is_allowlisted(name):
            entry = config.get_entry(name)
            if entry and entry.enabled:
                logger.debug("Connector '%s' is allowlisted and enabled", sanitize_for_log(name))
                return True

        # Check if restricted
        restricted_entry = config.get_restricted_entry(name)
        if restricted_entry:
            logger.debug(
                "Connector '%s' is restricted (requires %s)",
                sanitize_for_log(name),
                sanitize_for_log(restricted_entry.edition.value),
            )
            return False

        # Not in any list - default deny in CE
        logger.debug("Connector '%s' not found in allowlist for CE", sanitize_for_log(name))
        return False

    def log_violation(
        self,
        connector_name: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an allowlist violation for audit purposes.

        Args:
            connector_name: Name of the connector that violated allowlist
            operation: What operation was attempted (e.g., "get_connector", "register")
            context: Additional context about the violation
        """
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "connector": connector_name,
            "operation": operation,
            "context": context or {},
            "config_edition": self.config.edition.value,
        }
        self._violations.append(violation)

        logger.warning(
            "Allowlist violation: connector '%s' not accessible in %s edition (operation: %s)",
            sanitize_for_log(connector_name),
            sanitize_for_log(self.config.edition.value),
            sanitize_for_log(operation),
        )

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all logged violations (copy)."""
        return self._violations.copy()

    def clear_violations(self) -> None:
        """Clear violation log."""
        self._violations.clear()
        logger.info("Allowlist violations cleared")

    def add_connector(
        self,
        name: str,
        display_name: str,
        description: str = "",
        edition: MCPEdition = MCPEdition.COMMUNITY,
        added_by: str = "admin",
    ) -> AllowlistEntry:
        """
        Add a connector to the allowlist at runtime.

        Note: This modifies the in-memory config only. For persistence,
        update the YAML file directly or use save_config().

        Args:
            name: Connector identifier
            display_name: Human-readable name
            description: Connector description
            edition: Edition level
            added_by: Who added this entry

        Returns:
            The created AllowlistEntry
        """
        if self._config is None:
            self._config = self.load_config()

        # Check if already exists
        existing = self._config.get_entry(name)
        if existing:
            logger.info("Connector '%s' already in allowlist, updating", sanitize_for_log(name))
            existing.display_name = display_name
            existing.description = description
            existing.edition = edition
            existing.added_by = added_by
            existing.added_at = datetime.utcnow()
            return existing

        entry = AllowlistEntry(
            name=name,
            display_name=display_name,
            description=description,
            edition=edition,
            added_by=added_by,
            added_at=datetime.utcnow(),
        )
        self._config.allowlist.append(entry)
        logger.info(
            "Added connector '%s' to allowlist by %s",
            sanitize_for_log(name),
            sanitize_for_log(added_by),
        )
        return entry

    def remove_connector(self, name: str) -> bool:
        """
        Remove a connector from the allowlist.

        Args:
            name: Connector name to remove

        Returns:
            True if removed, False if not found
        """
        if self._config is None:
            return False

        original_count = len(self._config.allowlist)
        self._config.allowlist = [e for e in self._config.allowlist if e.name != name]
        removed = len(self._config.allowlist) < original_count

        if removed:
            logger.info("Removed connector '%s' from allowlist", sanitize_for_log(name))
        else:
            logger.debug("Connector '%s' not found in allowlist", sanitize_for_log(name))

        return removed

    def get_all_connectors_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all known connectors (allowlist + restricted).

        Returns:
            Dictionary mapping connector names to their info
        """
        config = self.config
        result = {}

        # Add allowlisted connectors
        for entry in config.allowlist:
            result[entry.name] = {
                **entry.to_dict(),
                "status": "allowlisted",
                "accessible_in_ce": entry.enabled,
            }

        # Add restricted connectors
        for entry in config.restricted:
            result[entry.name] = {
                **entry.to_dict(),
                "status": "restricted",
                "accessible_in_ce": False,
            }

        return result


# Module-level validator instance (singleton pattern)
_validator_instance: Optional[AllowlistValidator] = None


def get_allowlist_validator() -> AllowlistValidator:
    """
    Get the global AllowlistValidator instance.

    Creates a new instance on first call.
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = AllowlistValidator()
    return _validator_instance


def reset_allowlist_validator() -> None:
    """Reset the global validator instance (for testing)."""
    global _validator_instance
    _validator_instance = None
