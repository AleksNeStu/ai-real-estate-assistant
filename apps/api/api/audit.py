"""
Centralized Audit Logging System for security events (TASK-018).

This module provides comprehensive audit logging for all security-relevant events:
- Authentication successes and failures
- Authorization decisions
- Data access (read/write)
- Configuration changes
- Admin actions
- Security-related events

Audit logs are written to a dedicated file and include:
- Timestamp (ISO 8601)
- Event type/category
- User/client identifier
- Resource accessed
- Action performed
- Result (success/failure)
- IP address
- Request ID for correlation
- Additional metadata

Audit logs are separate from application logs and are designed for:
1. Security monitoring and incident response
2. Compliance (SOC 2, HIPAA, GDPR, etc.)
3. Forensic analysis
4. User activity tracking
"""

import csv
import hashlib
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Audit event categories."""

    # Authentication events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_MISSING_KEY = "auth.missing_key"
    AUTH_INVALID_KEY = "auth.invalid_key"
    AUTH_PRODUCTION_MISCONFIG = "auth.production_misconfig"

    # JWT Auth events (Task #47: Auth Security Hardening)
    AUTH_REGISTER = "auth.register"
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token_refresh"
    AUTH_PASSWORD_RESET_REQUEST = "auth.password_reset.request"
    AUTH_PASSWORD_RESET_COMPLETE = "auth.password_reset.complete"
    AUTH_EMAIL_VERIFIED = "auth.email_verified"
    AUTH_ACCOUNT_LOCKED = "auth.account_locked"
    AUTH_ACCOUNT_UNLOCKED = "auth.account_unlocked"
    AUTH_OAUTH_LOGIN = "auth.oauth.login"

    # Authorization events
    AUTHZ_GRANTED = "authz.granted"
    AUTHZ_DENIED = "authz.denied"
    AUTHZ_ADMIN_ACCESS = "authz.admin_access"

    # Data access events
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    DATA_UPLOAD = "data.upload"

    # Configuration events
    CONFIG_CHANGE = "config.change"
    CONFIG_READ = "config.read"

    # Admin events
    ADMIN_ACTION = "admin.action"
    ADMIN_USER_CHANGE = "admin.user_change"

    # Security events
    SECURITY_RATE_LIMIT = "security.rate_limit"
    SECURITY_BLOCKED_REQUEST = "security.blocked_request"
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious_activity"

    # API events
    API_REQUEST = "api.request"
    API_ERROR = "api.error"


class AuditLevel(str, Enum):
    """Severity/impact levels for audit events."""

    CRITICAL = "CRITICAL"  # Security breach, data exposure
    HIGH = "HIGH"  # Failed auth, admin actions, data changes
    MEDIUM = "MEDIUM"  # Successful auth, data access
    LOW = "LOW"  # Routine operations
    INFO = "INFO"  # Informational


class AuditEvent(BaseModel):
    """Structured audit event."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: AuditEventType
    level: AuditLevel
    user_id: Optional[str] = None  # Hashed identifier
    client_id: Optional[str] = None  # Hashed API key identifier
    resource: Optional[str] = None  # Resource accessed (e.g., /api/v1/search)
    action: Optional[str] = None  # Action performed
    result: str  # success, failure, error
    ip_address: Optional[str] = None
    request_id: Optional[str] = None  # Correlation ID
    user_agent: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        use_enum_values = True


class AuditLogger:
    """
    Thread-safe audit logger.

    Writes audit events to:
    1. Dedicated audit log file (CSV format for easy analysis)
    2. Standard logger (for real-time monitoring)
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        enabled: bool = True,
    ) -> None:
        """
        Initialize audit logger.

        Args:
            log_dir: Directory for audit logs (default: data/audit)
            enabled: Whether audit logging is enabled
        """
        self._enabled = enabled and (
            os.getenv("AUDIT_LOGGING_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        )

        if log_dir is None:
            log_dir = Path(os.getenv("AUDIT_LOG_DIR", "data/audit"))

        self._log_dir = Path(log_dir)

        # Current log file (rotates daily)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._log_file = self._log_dir / f"audit_{today}.csv"

        # Thread lock for file writing
        self._lock = threading.Lock()

        # Standard logger for real-time alerts
        self._logger = logging.getLogger("audit")

        requested_dir = self._log_dir
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            # Initialize CSV file with headers
            self._init_csv()
        except OSError as exc:
            # The audit directory belongs to whoever mounted it. A container
            # that runs as a non-root user (uid 999) cannot write a
            # root-owned mount, and an audit log that cannot be written must
            # not take the whole API down with it - the log moves to a
            # directory that is writable, and the fallback is named out loud.
            fallback_dir = Path(tempfile.gettempdir()) / "audit"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self._log_dir = fallback_dir
            self._log_file = fallback_dir / f"audit_{today}.csv"
            self._init_csv()
            self._logger.warning(
                "The audit log directory %s is not writable (%s); the audit log is written to %s.",
                requested_dir,
                exc,
                fallback_dir,
            )

        if self._enabled:
            self._logger.info("Audit logging initialized", extra={"log_file": str(self._log_file)})

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
                            "user_id",
                            "client_id",
                            "resource",
                            "action",
                            "result",
                            "ip_address",
                            "request_id",
                            "user_agent",
                            "metadata",
                        ]
                    )

    def _hash_identifier(self, value: Optional[str]) -> Optional[str]:
        """
        Hash sensitive identifier for PII protection.

        Uses SHA-256 to create a consistent but irreversible hash.
        Truncated to 16 hex chars for log readability (not used for security).
        """
        if not value:
            return None
        # nosemgrep: py/weak-sensitive-data-hashing - truncated hash for PII-safe logging, not security
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    def log(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: Audit event to log
        """
        if not self._enabled:
            return

        # Hash sensitive identifiers
        user_id = self._hash_identifier(event.user_id)
        client_id = self._hash_identifier(event.client_id)

        # Write to CSV
        with self._lock:
            try:
                # Check if we need to rotate to new daily file
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                expected_file = self._log_dir / f"audit_{today}.csv"
                if expected_file != self._log_file:
                    self._log_file = expected_file
                    self._init_csv()

                with open(self._log_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            event.timestamp,
                            event.event_type,
                            event.level,
                            user_id or "",
                            client_id or "",
                            event.resource or "",
                            event.action or "",
                            event.result,
                            event.ip_address or "",
                            event.request_id or "",
                            event.user_agent or "",
                            str(event.metadata),
                        ]
                    )
            except Exception as e:
                # Don't fail the request if audit logging fails
                self._logger.error("Failed to write audit log", exc_info=e)

        # Log to standard logger for real-time monitoring
        log_method = {
            AuditLevel.CRITICAL: self._logger.critical,
            AuditLevel.HIGH: self._logger.warning,
            AuditLevel.MEDIUM: self._logger.info,
            AuditLevel.LOW: self._logger.debug,
            AuditLevel.INFO: self._logger.debug,
        }.get(event.level, self._logger.info)

        log_method(
            event.event_type,
            extra={
                "audit": True,
                "event_type": event.event_type,
                "level": event.level,
                "resource": event.resource,
                "action": event.action,
                "result": event.result,
                "request_id": event.request_id,
                **event.metadata,
            },
        )

    def log_auth_success(
        self,
        client_id: Optional[str],
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log successful authentication."""
        self.log(
            AuditEvent(
                event_type=AuditEventType.AUTH_SUCCESS,
                level=AuditLevel.MEDIUM,
                client_id=client_id,
                result="success",
                request_id=request_id,
                metadata=metadata or {},
            )
        )

    def log_auth_failure(
        self,
        reason: str,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None,
        key_prefix: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log failed authentication."""
        self.log(
            AuditEvent(
                event_type=AuditEventType.AUTH_FAILURE,
                level=AuditLevel.HIGH,
                resource=path,
                action=method,
                result="failure",
                request_id=request_id,
                metadata={
                    "reason": reason,
                    "key_prefix": key_prefix,
                    **(metadata or {}),
                },
            )
        )

    def log_data_access(
        self,
        operation: str,
        resource: str,
        client_id: Optional[str],
        result: str = "success",
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log data access event."""
        event_type = {
            "read": AuditEventType.DATA_READ,
            "write": AuditEventType.DATA_WRITE,
            "delete": AuditEventType.DATA_DELETE,
            "export": AuditEventType.DATA_EXPORT,
            "upload": AuditEventType.DATA_UPLOAD,
        }.get(operation.lower(), AuditEventType.DATA_READ)

        level = {
            "delete": AuditLevel.HIGH,
            "write": AuditLevel.MEDIUM,
            "export": AuditLevel.HIGH,
            "upload": AuditLevel.MEDIUM,
        }.get(operation.lower(), AuditLevel.LOW)

        self.log(
            AuditEvent(
                event_type=event_type,
                level=level,
                client_id=client_id,
                resource=resource,
                action=operation,
                result=result,
                request_id=request_id,
                metadata=metadata or {},
            )
        )

    def log_admin_action(
        self,
        action: str,
        resource: str,
        client_id: Optional[str],
        result: str = "success",
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log administrative action."""
        self.log(
            AuditEvent(
                event_type=AuditEventType.ADMIN_ACTION,
                level=AuditLevel.HIGH,
                client_id=client_id,
                resource=resource,
                action=action,
                result=result,
                request_id=request_id,
                metadata=metadata or {},
            )
        )

    def log_security_event(
        self,
        event_type: AuditEventType,
        level: AuditLevel,
        resource: Optional[str] = None,
        client_id: Optional[str] = None,
        result: str = "detected",
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log security-related event."""
        self.log(
            AuditEvent(
                event_type=event_type,
                level=level,
                client_id=client_id,
                resource=resource,
                result=result,
                request_id=request_id,
                metadata=metadata or {},
            )
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None
_audit_lock = threading.Lock()


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    with _audit_lock:
        if _audit_logger is None:
            _audit_logger = AuditLogger()
        return _audit_logger


def log_audit_event(
    event_type: AuditEventType,
    level: AuditLevel,
    resource: Optional[str] = None,
    client_id: Optional[str] = None,
    action: Optional[str] = None,
    result: str = "success",
    request_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Convenience function to log an audit event.

    Args:
        event_type: Type of audit event
        level: Severity level
        resource: Resource being accessed
        client_id: Client identifier (will be hashed)
        action: Action being performed
        result: Result of the action
        request_id: Request correlation ID
        metadata: Additional metadata
    """
    audit_logger = get_audit_logger()
    audit_logger.log(
        AuditEvent(
            event_type=event_type,
            level=level,
            client_id=client_id,
            resource=resource,
            action=action,
            result=result,
            request_id=request_id,
            metadata=metadata or {},
        )
    )
