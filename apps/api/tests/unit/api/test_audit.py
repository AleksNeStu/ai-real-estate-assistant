"""Tests for the audit logging system (TASK-018)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from api.audit import (
    AuditEvent,
    AuditEventType,
    AuditLevel,
    AuditLogger,
    log_audit_event,
)


class TestAuditEvent:
    """Tests for AuditEvent model."""

    def test_create_audit_event(self):
        """Test creating an audit event."""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_SUCCESS,
            level=AuditLevel.MEDIUM,
            client_id="test_client",
            result="success",
        )
        assert event.event_type == AuditEventType.AUTH_SUCCESS
        assert event.level == AuditLevel.MEDIUM
        assert event.client_id == "test_client"
        assert event.result == "success"

    def test_audit_event_defaults(self):
        """Test audit event default values."""
        event = AuditEvent(
            event_type=AuditEventType.DATA_READ,
            level=AuditLevel.LOW,
            result="success",
        )
        assert event.timestamp is not None
        assert event.user_id is None
        assert event.client_id is None
        assert event.metadata == {}


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_audit_logger_init(self):
        """Test audit logger initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=True)
            assert logger._enabled is True
            assert logger._log_dir == Path(tmpdir)
            assert logger._log_file.exists()

    def test_an_unwritable_audit_directory_does_not_take_the_api_down(self, tmp_path, monkeypatch):
        """A directory the app cannot write moves the log, it does not raise.

        On a Linux host the container's user (uid 999) cannot write a
        root-owned mount, and the API must not die because of it.
        """
        blocked = tmp_path / "blocked"
        fallback_root = tmp_path / "fallback"
        original_mkdir = Path.mkdir

        def refuse_the_blocked_dir(self, *args, **kwargs):
            if self == blocked:
                raise PermissionError(13, "Permission denied")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", refuse_the_blocked_dir)
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(fallback_root))
        monkeypatch.setenv("AUDIT_LOG_DIR", str(blocked))

        logger = AuditLogger(log_dir=None)

        assert logger._log_dir == fallback_root / "audit"
        assert logger._log_file.exists()

    def test_audit_logger_hash_identifier(self):
        """Test identifier hashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=False)
            hashed = logger._hash_identifier("test_api_key")
            assert hashed is not None
            assert len(hashed) == 16
            assert hashed != "test_api_key"

    def test_audit_logger_hash_identifier_none(self):
        """Test hashing None identifier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=False)
            hashed = logger._hash_identifier(None)
            assert hashed is None

    def test_audit_logger_log_auth_success(self):
        """Test logging successful authentication."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=True)
            logger.log_auth_success(client_id="test_client", request_id="req-123")

            # Check that log file was created and has content
            assert logger._log_file.exists()
            content = logger._log_file.read_text()
            assert "auth.success" in content

    def test_audit_logger_log_auth_failure(self):
        """Test logging failed authentication."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=True)
            logger.log_auth_failure(
                reason="invalid_key",
                request_id="req-456",
                path="/api/v1/search",
                method="GET",
            )

            content = logger._log_file.read_text()
            assert "auth.failure" in content
            assert "invalid_key" in content

    def test_audit_logger_log_data_access(self):
        """Test logging data access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=True)
            logger.log_data_access(
                operation="read",
                resource="/api/v1/properties",
                client_id="test_client",
                result="success",
            )

            content = logger._log_file.read_text()
            assert "data.read" in content

    def test_audit_logger_log_admin_action(self):
        """Test logging admin action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=True)
            logger.log_admin_action(
                action="update_config",
                resource="settings",
                client_id="admin_client",
                result="success",
            )

            content = logger._log_file.read_text()
            assert "admin.action" in content

    def test_audit_logger_disabled(self):
        """Test audit logger when disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=False)
            logger.log_auth_success(client_id="test_client")

            # Log file should exist but be empty or have only headers
            content = logger._log_file.read_text()
            # Should only have CSV header, no data rows
            lines = [
                line
                for line in content.split("\n")
                if line.strip() and not line.startswith("timestamp")
            ]
            assert len(lines) == 0

    def test_audit_logger_log_security_event(self):
        """Test logging security event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir), enabled=True)
            logger.log_security_event(
                event_type=AuditEventType.SECURITY_RATE_LIMIT,
                level=AuditLevel.HIGH,
                resource="/api/v1/search",
                result="detected",
            )

            content = logger._log_file.read_text()
            assert "security.rate_limit" in content


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch("api.audit.get_audit_logger")
    def test_log_audit_event(self, mock_get_logger):
        """Test log_audit_event convenience function."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        log_audit_event(
            event_type=AuditEventType.AUTH_SUCCESS,
            level=AuditLevel.MEDIUM,
            client_id="test_client",
            result="success",
        )

        mock_logger.log.assert_called_once()
        # The event is passed as a positional argument (first arg)
        call_args = mock_logger.log.call_args
        event = call_args[0][0]  # First positional argument
        assert event.event_type == AuditEventType.AUTH_SUCCESS
