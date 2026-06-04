"""
MCP connector abstract base class.

This module defines the abstract interface that all MCP connectors
must implement, ensuring consistent behavior across different services.
Enhanced with audit logging for connector calls (Task #69).
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Generic, Optional, TypeVar

from core.security_utils import sanitize_for_log
from mcp.config import MCPConnectorConfig, MCPEdition
from mcp.exceptions import MCPNotAllowlistedError
from mcp.result import MCPConnectorResult

logger = logging.getLogger(__name__)


def _get_audit_logger():
    """Lazy import to avoid circular dependency."""
    from mcp.audit import get_mcp_audit_logger

    return get_mcp_audit_logger()


def _get_redaction():
    """Lazy import for redaction utilities."""
    from mcp.redaction import (
        redact_params,
        redact_result,
        sanitize_error_message,
    )

    return redact_params, redact_result, sanitize_error_message


T = TypeVar("T")


class MCPConnector(ABC, Generic[T]):
    """
    Abstract base class for MCP connectors.

    All MCP connectors must inherit from this class and implement the
    required lifecycle and operation methods.

    Generic type T represents the response payload type for this connector.

    Class Attributes:
        name: Unique identifier for the connector (must be set by subclass)
        display_name: Human-readable name for display in UI
        description: Brief description of connector functionality
        requires_api_key: Whether this connector requires an API key
        api_key_env_var: Environment variable name for the API key
        default_timeout: Default request timeout in seconds
        allowlisted: Whether connector is allowlisted for Community Edition
        min_edition: Minimum edition required to use this connector
        supports_streaming: Whether streaming is supported
    """

    name: str = ""
    display_name: str = ""
    description: str = ""
    requires_api_key: bool = True
    api_key_env_var: str = ""
    default_timeout: float = 30.0
    allowlisted: bool = False
    min_edition: MCPEdition = MCPEdition.PRO
    supports_streaming: bool = False

    def __init__(self, config: Optional[MCPConnectorConfig] = None) -> None:
        """
        Initialize the connector.

        Args:
            config: Optional configuration (falls back to defaults)

        Raises:
            MCPConfigError: If configuration is invalid
        """
        self._config = config or self._create_default_config()
        self._connected = False
        self._connection_pool: Any = None
        self._validate_configuration()
        logger.info("Initialized MCP connector: %s", sanitize_for_log(self.name))

    def _create_default_config(self) -> MCPConnectorConfig:
        """Create default configuration from class attributes."""
        return MCPConnectorConfig(
            name=self.name,
            display_name=self.display_name,
            api_key_env_var=self.api_key_env_var,
            timeout_seconds=self.default_timeout,
            allowlisted=self.allowlisted,
            min_edition=self.min_edition,
            supports_streaming=self.supports_streaming,
        )

    def _validate_configuration(self) -> None:
        """
        Validate connector configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.name:
            raise ValueError("Connector must have a 'name' attribute")

        if self.requires_api_key and not self._config.api_key:
            raise ValueError(
                f"Connector '{self.name}' requires API key. "
                f"Set environment variable '{self.api_key_env_var}'"
            )

    def check_edition_access(self, current_edition: MCPEdition) -> None:
        """
        Check if current edition allows access to this connector.

        Args:
            current_edition: The current application edition

        Raises:
            MCPNotAllowlistedError: If connector not accessible in current edition
        """
        if current_edition == MCPEdition.COMMUNITY:
            if not self.allowlisted:
                raise MCPNotAllowlistedError(self.name, "community")

        if not self._config.is_available_for_edition(current_edition):
            raise MCPNotAllowlistedError(self.name, current_edition.value)

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the MCP service.

        Returns:
            True if connection successful

        Raises:
            MCPConnectionError: If connection fails
            MCPAuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to the MCP service.

        Should gracefully close all connections in the pool.
        """
        pass

    @abstractmethod
    async def health_check(self) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Check health status of the connector and underlying service.

        Returns:
            MCPConnectorResult with health status information
        """
        pass

    @abstractmethod
    async def execute(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MCPConnectorResult[T]:
        """
        Execute an operation on the MCP service.

        Args:
            operation: Operation name to execute
            params: Parameters for the operation
            **kwargs: Additional operation-specific options

        Returns:
            MCPConnectorResult with operation result
        """
        pass

    async def execute_with_timing(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MCPConnectorResult[T]:
        """
        Execute operation with automatic timing measurement and audit logging.

        Args:
            operation: Operation name to execute
            params: Parameters for the operation
            **kwargs: Additional operation-specific options

        Returns:
            MCPConnectorResult with timing metadata
        """
        start_time = time.perf_counter()
        status = "success"
        error_message = None
        result = None

        try:
            result = await self.execute(operation, params, **kwargs)
            if result and hasattr(result, "success") and not result.success:
                status = "failure"
        except Exception as e:
            status = "error"
            error_message = str(e)
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            result = MCPConnectorResult.error_result(
                errors=[str(e)],
                connector_name=self.name,
                operation=operation,
                execution_time_ms=execution_time_ms,
            )

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Update result timing
        if result:
            result.execution_time_ms = execution_time_ms

        # Log audit event (non-blocking, catches own errors)
        try:
            audit_logger = _get_audit_logger()
            redact_params, redact_result, sanitize_error = _get_redaction()

            audit_logger.log_connector_call(
                connector_name=self.name,
                operation=operation,
                params_meta=redact_params(params),
                result_meta=redact_result(result),
                duration_ms=int(execution_time_ms),
                status=status,
                error_message=sanitize_error(error_message) if error_message else None,
            )
        except Exception as audit_error:
            # Don't fail the request if audit logging fails
            logger.warning("Audit logging failed: %s", sanitize_for_log(audit_error))

        return result

    async def stream(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[T, None]:
        """
        Stream results from the MCP service.

        Args:
            operation: Operation name to execute
            params: Parameters for the operation
            **kwargs: Additional operation-specific options

        Yields:
            Chunks of the response

        Raises:
            NotImplementedError: If connector doesn't support streaming
        """
        if not self.supports_streaming:
            raise NotImplementedError(f"Connector '{self.name}' does not support streaming")
        # Subclasses should override this method if streaming is supported
        if False:  # pragma: no cover
            yield  # type: ignore

    def is_connected(self) -> bool:
        """Check if connector is currently connected."""
        return self._connected

    def get_config(self) -> MCPConnectorConfig:
        """Get current connector configuration."""
        return self._config

    def get_status(self) -> Dict[str, Any]:
        """
        Get connector status information.

        Returns:
            Dictionary with status information
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "connected": self._connected,
            "config": self._config.to_dict(),
            "requires_api_key": self.requires_api_key,
            "has_api_key": bool(self._config.api_key),
        }

    async def __aenter__(self) -> "MCPConnector[T]":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
