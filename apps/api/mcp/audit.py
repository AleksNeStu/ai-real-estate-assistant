"""
MCP Audit Logging System for connector calls (Task #69).

This module provides audit logging specifically for MCP connector operations:
- Connector lifecycle events (connect, execute, disconnect)
- Request/response metadata (no PII)
- Request ID correlation across connector calls
- Configurable log retention
- Query API for audit log access

Design principles:
1. Data minimization - only log metadata, never PII
2. Request correlation - track requests across connector calls
3. Configurable retention - automatic cleanup of old logs
4. Query capability - admin API for audit log access
"""

import csv
import logging
import os
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from core.security_utils import sanitize_for_log
from mcp.context import get_request_id

logger = logging.getLogger(__name__)


class MCPAuditEventType(str, Enum):
    """MCP connector audit event types."""

    # Lifecycle events
    CONNECTOR_CONNECT = "mcp.connector.connect"
    CONNECTOR_DISCONNECT = "mcp.connector.disconnect"
    CONNECTOR_EXECUTE = "mcp.connector.execute"
    CONNECTOR_ERROR = "mcp.connector.error"
    CONNECTOR_HEALTH_CHECK = "mcp.connector.health_check"

    # Registry events
    CONNECTOR_REGISTER = "mcp.connector.register"
    CONNECTOR_UNREGISTER = "mcp.connector.unregister"
    CONNECTOR_ALLOWLIST_VIOLATION = "mcp.connector.allowlist_violation"


class MCPAuditLevel(str, Enum):
    """Severity levels for MCP audit events."""

    CRITICAL = "CRITICAL"  # Security breach, data exposure
    HIGH = "HIGH"  # Connector errors, allowlist violations
    MEDIUM = "MEDIUM"  # Successful connector calls
    LOW = "LOW"  # Routine operations (health checks)
    INFO = "INFO"  # Informational events


class MCPAuditEvent(BaseModel):
    """Structured MCP audit event."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: MCPAuditEventType
    level: MCPAuditLevel
    connector_name: str
    operation: Optional[str] = None
    status: str  # success, failure, error
    duration_ms: Optional[int] = None
    request_id: Optional[str] = None
    params_meta: dict[str, Any] = Field(default_factory=dict)  # Redacted params
    result_meta: dict[str, Any] = Field(default_factory=dict)  # Redacted result
    error_message: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        use_enum_values = True


class MCPAuditLogger:
    """
    Thread-safe audit logger for MCP connector operations.

    Writes audit events to:
    1. Dedicated MCP audit log file (CSV format)
    2. Standard logger (for real-time monitoring)

    Features:
    - Request ID correlation via contextvars
    - Automatic PII redaction
    - Daily log rotation
    - Configurable retention
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        enabled: bool = True,
        retention_days: int = 30,
    ) -> None:
        """
        Initialize MCP audit logger.

        Args:
            log_dir: Directory for audit logs (default: logs/mcp_audit)
            enabled: Whether audit logging is enabled
            retention_days: Number of days to retain logs
        """
        self._enabled = enabled and (
            os.getenv("MCP_AUDIT_LOGGING_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        )

        if log_dir is None:
            log_dir = Path(os.getenv("MCP_AUDIT_LOG_DIR", "logs/mcp_audit"))

        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Retention configuration
        self._retention_days = int(os.getenv("MCP_AUDIT_RETENTION_DAYS", str(retention_days)))

        # Current log file (rotates daily)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._log_file = self._log_dir / f"mcp_audit_{today}.csv"

        # Thread lock for file writing
        self._lock = threading.Lock()

        # Initialize CSV file with headers
        self._init_csv()

        if self._enabled:
            logger.info(
                "MCP audit logging initialized",
                extra={"log_file": str(self._log_file), "retention_days": self._retention_days},
            )

    def _init_csv(self) -> None:
        """Initialize CSV file with headers."""
        if not self._log_file.exists():
            with self._lock:
                with open(self._log_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "timestamp",
                            "event_type",
                            "level",
                            "connector_name",
                            "operation",
                            "status",
                            "duration_ms",
                            "request_id",
                            "params_meta",
                            "result_meta",
                            "error_message",
                            "metadata",
                        ]
                    )

    def _rotate_if_needed(self) -> None:
        """Rotate to new daily file if needed."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        expected_file = self._log_dir / f"mcp_audit_{today}.csv"
        if expected_file != self._log_file:
            self._log_file = expected_file
            self._init_csv()

    def log(self, event: MCPAuditEvent) -> None:
        """
        Log an MCP audit event.

        Args:
            event: MCP audit event to log
        """
        if not self._enabled:
            return

        # Write to CSV
        with self._lock:
            try:
                self._rotate_if_needed()

                with open(self._log_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            event.timestamp,
                            event.event_type,
                            event.level,
                            event.connector_name,
                            event.operation or "",
                            event.status,
                            event.duration_ms or "",
                            event.request_id or "",
                            str(event.params_meta),
                            str(event.result_meta),
                            event.error_message or "",
                            str(event.metadata),
                        ]
                    )
            except Exception as e:
                logger.error("Failed to write MCP audit log", exc_info=e)

        # Log to standard logger for real-time monitoring
        log_method = {
            MCPAuditLevel.CRITICAL: logger.critical,
            MCPAuditLevel.HIGH: logger.warning,
            MCPAuditLevel.MEDIUM: logger.info,
            MCPAuditLevel.LOW: logger.debug,
            MCPAuditLevel.INFO: logger.debug,
        }.get(event.level, logger.info)

        log_method(
            f"mcp_audit: {event.event_type}",
            extra={
                "mcp_audit": True,
                "event_type": event.event_type,
                "level": event.level,
                "connector_name": event.connector_name,
                "operation": event.operation,
                "status": event.status,
                "duration_ms": event.duration_ms,
                "request_id": event.request_id,
            },
        )

    def log_connector_call(
        self,
        connector_name: str,
        operation: str,
        params_meta: dict[str, Any],
        result_meta: dict[str, Any],
        duration_ms: int,
        status: str,
        request_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Log a connector execution call.

        Args:
            connector_name: Name of the connector
            operation: Operation being executed
            params_meta: Redacted parameters metadata
            result_meta: Redacted result metadata
            duration_ms: Execution duration in milliseconds
            status: Call status (success, failure, error)
            request_id: Optional request ID for correlation
            error_message: Optional error message if failed
            metadata: Additional metadata
        """
        # Get request ID from context if not provided
        if request_id is None:
            request_id = get_request_id()

        # Determine event type and level based on status
        if status == "error":
            event_type = MCPAuditEventType.CONNECTOR_ERROR
            level = MCPAuditLevel.HIGH
        else:
            event_type = MCPAuditEventType.CONNECTOR_EXECUTE
            level = MCPAuditLevel.MEDIUM if status == "success" else MCPAuditLevel.HIGH

        self.log(
            MCPAuditEvent(
                event_type=event_type,
                level=level,
                connector_name=connector_name,
                operation=operation,
                status=status,
                duration_ms=duration_ms,
                request_id=request_id,
                params_meta=params_meta,
                result_meta=result_meta,
                error_message=error_message,
                metadata=metadata or {},
            )
        )

    def log_connector_lifecycle(
        self,
        connector_name: str,
        lifecycle_event: str,  # "connect", "disconnect", "health_check"
        status: str,
        request_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Log a connector lifecycle event.

        Args:
            connector_name: Name of the connector
            lifecycle_event: Type of lifecycle event
            status: Event status
            request_id: Optional request ID
            error_message: Optional error message
            metadata: Additional metadata
        """
        if request_id is None:
            request_id = get_request_id()

        event_type_map = {
            "connect": MCPAuditEventType.CONNECTOR_CONNECT,
            "disconnect": MCPAuditEventType.CONNECTOR_DISCONNECT,
            "health_check": MCPAuditEventType.CONNECTOR_HEALTH_CHECK,
        }
        event_type = event_type_map.get(lifecycle_event, MCPAuditEventType.CONNECTOR_EXECUTE)

        level = MCPAuditLevel.LOW if status == "success" else MCPAuditLevel.MEDIUM

        self.log(
            MCPAuditEvent(
                event_type=event_type,
                level=level,
                connector_name=connector_name,
                operation=lifecycle_event,
                status=status,
                request_id=request_id,
                error_message=error_message,
                metadata=metadata or {},
            )
        )

    def log_allowlist_violation(
        self,
        connector_name: str,
        edition: str,
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Log an allowlist violation attempt.

        Args:
            connector_name: Name of the connector
            edition: Current edition (community, pro, etc.)
            request_id: Optional request ID
            metadata: Additional metadata
        """
        if request_id is None:
            request_id = get_request_id()

        self.log(
            MCPAuditEvent(
                event_type=MCPAuditEventType.CONNECTOR_ALLOWLIST_VIOLATION,
                level=MCPAuditLevel.HIGH,
                connector_name=connector_name,
                operation="allowlist_check",
                status="blocked",
                request_id=request_id,
                metadata={
                    "edition": edition,
                    **(metadata or {}),
                },
            )
        )

    def query(
        self,
        connector_name: Optional[str] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        request_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Query audit logs with filters.

        Args:
            connector_name: Filter by connector name
            operation: Filter by operation
            status: Filter by status
            request_id: Filter by request ID
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            List of matching audit log entries
        """
        results: list[dict[str, Any]] = []

        # Determine which files to search
        if start_date and end_date:
            date_range = self._get_date_range(start_date, end_date)
        else:
            # Default to last 7 days
            date_range = self._get_recent_dates(7)

        for date_str in date_range:
            log_file = self._log_dir / f"mcp_audit_{date_str}.csv"
            if not log_file.exists():
                continue

            try:
                with open(log_file, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if self._matches_filters(
                            row, connector_name, operation, status, request_id
                        ):
                            results.append(row)
                            if len(results) >= limit + offset:
                                break
            except Exception as e:
                logger.warning(
                    "Failed to read audit log file %s: %s",
                    sanitize_for_log(log_file),
                    sanitize_for_log(e),
                )

        # Apply offset and limit
        return results[offset : offset + limit]

    def _matches_filters(
        self,
        row: dict[str, Any],
        connector_name: Optional[str],
        operation: Optional[str],
        status: Optional[str],
        request_id: Optional[str],
    ) -> bool:
        """Check if a row matches the given filters."""
        if connector_name and row.get("connector_name") != connector_name:
            return False
        if operation and row.get("operation") != operation:
            return False
        if status and row.get("status") != status:
            return False
        if request_id and row.get("request_id") != request_id:
            return False
        return True

    def _get_date_range(self, start_date: datetime, end_date: datetime) -> list[str]:
        """Get list of date strings in range."""
        dates = []
        current = start_date.date()
        end = end_date.date()
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            from datetime import timedelta

            current = current + timedelta(days=1)
        return dates

    def _get_recent_dates(self, days: int) -> list[str]:
        """Get list of recent date strings."""
        dates = []
        from datetime import timedelta

        for i in range(days):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        return dates

    def cleanup_old_logs(self) -> int:
        """
        Remove audit logs older than retention period.

        Returns:
            Number of files removed
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        removed = 0
        for log_file in self._log_dir.glob("mcp_audit_*.csv"):
            # Extract date from filename
            try:
                date_str = log_file.stem.replace("mcp_audit_", "")
                if date_str < cutoff_str:
                    log_file.unlink()
                    removed += 1
                    logger.info("Removed old MCP audit log: %s", sanitize_for_log(log_file))
            except Exception as e:
                logger.warning(
                    "Failed to process log file %s: %s",
                    sanitize_for_log(log_file),
                    sanitize_for_log(e),
                )

        return removed


# Global MCP audit logger instance
_mcp_audit_logger: Optional[MCPAuditLogger] = None
_mcp_audit_lock = threading.Lock()


def get_mcp_audit_logger() -> MCPAuditLogger:
    """Get global MCP audit logger instance."""
    global _mcp_audit_logger
    with _mcp_audit_lock:
        if _mcp_audit_logger is None:
            _mcp_audit_logger = MCPAuditLogger()
        return _mcp_audit_logger


def log_mcp_audit(
    connector_name: str,
    operation: str,
    params_meta: dict[str, Any],
    result_meta: dict[str, Any],
    duration_ms: int,
    status: str,
    request_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    Convenience function to log an MCP audit event.

    Args:
        connector_name: Name of the connector
        operation: Operation being executed
        params_meta: Redacted parameters metadata
        result_meta: Redacted result metadata
        duration_ms: Execution duration in milliseconds
        status: Call status
        request_id: Optional request ID for correlation
        error_message: Optional error message
    """
    audit_logger = get_mcp_audit_logger()
    audit_logger.log_connector_call(
        connector_name=connector_name,
        operation=operation,
        params_meta=params_meta,
        result_meta=result_meta,
        duration_ms=duration_ms,
        status=status,
        request_id=request_id,
        error_message=error_message,
    )
