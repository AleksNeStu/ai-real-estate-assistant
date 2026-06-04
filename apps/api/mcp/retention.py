"""
MCP Audit Log Retention Policy (Task #69).

This module provides configurable log retention for MCP audit logs:
1. Automatic cleanup of old log files
2. Configurable retention period
3. Scheduled cleanup job
4. Storage metrics
"""

import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, TypedDict

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


class CleanupResult(TypedDict):
    """Result of a cleanup operation."""

    files_found: int
    files_removed: int
    bytes_freed: int
    errors: list[str]
    dry_run: bool


class MCPAuditRetention:
    """
    Manages retention policy for MCP audit logs.

    Features:
    - Configurable retention days (default: 30)
    - Automatic cleanup of old files
    - Scheduled background cleanup
    - Storage metrics reporting
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        retention_days: Optional[int] = None,
    ) -> None:
        """
        Initialize retention manager.

        Args:
            log_dir: Directory for audit logs
            retention_days: Number of days to retain logs
        """
        if log_dir is None:
            log_dir = Path(os.getenv("MCP_AUDIT_LOG_DIR", "logs/mcp_audit"))

        self._log_dir = Path(log_dir)

        # Get retention days from env or use default
        self._retention_days = retention_days or int(os.getenv("MCP_AUDIT_RETENTION_DAYS", "30"))

        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_event = threading.Event()
        self._running = False

    @property
    def retention_days(self) -> int:
        """Get the current retention period in days."""
        return self._retention_days

    @retention_days.setter
    def retention_days(self, days: int) -> None:
        """Set the retention period in days."""
        if days < 1:
            raise ValueError("Retention days must be at least 1")
        self._retention_days = days

    def get_cutoff_date(self) -> datetime:
        """
        Get the cutoff date for log retention.

        Returns:
            Datetime before which logs should be deleted
        """
        return datetime.now(timezone.utc) - timedelta(days=self._retention_days)

    def get_log_files(self) -> list[Path]:
        """
        Get all MCP audit log files.

        Returns:
            List of log file paths
        """
        if not self._log_dir.exists():
            return []

        return list(self._log_dir.glob("mcp_audit_*.csv"))

    def get_expired_files(self) -> list[Path]:
        """
        Get log files that are past the retention period.

        Returns:
            List of expired log file paths
        """
        cutoff = self.get_cutoff_date()
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        expired = []
        for log_file in self.get_log_files():
            # Extract date from filename (mcp_audit_YYYY-MM-DD.csv)
            try:
                date_str = log_file.stem.replace("mcp_audit_", "")
                if date_str < cutoff_str:
                    expired.append(log_file)
            except Exception as e:
                logger.warning(
                    "Failed to parse date from %s: %s",
                    sanitize_for_log(log_file),
                    sanitize_for_log(e),
                )

        return expired

    def cleanup(self, dry_run: bool = False) -> CleanupResult:
        """
        Remove expired audit log files.

        Args:
            dry_run: If True, don't actually delete files

        Returns:
            Dictionary with cleanup results
        """
        expired = self.get_expired_files()

        result: CleanupResult = {
            "files_found": len(expired),
            "files_removed": 0,
            "bytes_freed": 0,
            "errors": [],
            "dry_run": dry_run,
        }

        for log_file in expired:
            try:
                file_size = log_file.stat().st_size

                if not dry_run:
                    log_file.unlink()
                    logger.info("Removed expired MCP audit log: %s", sanitize_for_log(log_file))
                    result["files_removed"] += 1

                result["bytes_freed"] += file_size

            except Exception as e:
                error_msg = f"Failed to remove {log_file}: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)

        return result

    def get_storage_metrics(self) -> dict[str, Any]:
        """
        Get storage metrics for audit logs.

        Returns:
            Dictionary with storage information
        """
        files = self.get_log_files()

        total_size = 0
        file_count = 0
        oldest_date = None
        newest_date = None

        for log_file in files:
            try:
                total_size += log_file.stat().st_size
                file_count += 1

                date_str = log_file.stem.replace("mcp_audit_", "")
                if oldest_date is None or date_str < oldest_date:
                    oldest_date = date_str
                if newest_date is None or date_str > newest_date:
                    newest_date = date_str

            except Exception:
                pass

        return {
            "log_directory": str(self._log_dir),
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_log_date": oldest_date,
            "newest_log_date": newest_date,
            "retention_days": self._retention_days,
            "expired_files": len(self.get_expired_files()),
        }

    def start_scheduled_cleanup(self, interval_hours: int = 24) -> None:
        """
        Start background thread for scheduled cleanup.

        Args:
            interval_hours: Hours between cleanup runs
        """
        if self._running:
            logger.warning("Scheduled cleanup already running")
            return

        self._running = True
        self._cleanup_event.clear()

        def cleanup_loop():
            while self._running:
                # Wait for interval or stop signal
                if self._cleanup_event.wait(timeout=interval_hours * 3600):
                    break  # Stop signal received

                if self._running:
                    logger.info("Running scheduled MCP audit log cleanup")
                    try:
                        result = self.cleanup()
                        logger.info("Cleanup completed: %s", sanitize_for_log(result))
                    except Exception as e:
                        logger.error("Scheduled cleanup failed: %s", sanitize_for_log(e))

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("Started scheduled cleanup (interval: %sh)", sanitize_for_log(interval_hours))

    def stop_scheduled_cleanup(self) -> None:
        """Stop the scheduled cleanup thread."""
        self._running = False
        self._cleanup_event.set()

        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)

        logger.info("Stopped scheduled cleanup")


# Global retention manager instance
_retention_manager: Optional[MCPAuditRetention] = None
_retention_lock = threading.Lock()


def get_retention_manager() -> MCPAuditRetention:
    """Get global retention manager instance."""
    global _retention_manager
    with _retention_lock:
        if _retention_manager is None:
            _retention_manager = MCPAuditRetention()
        return _retention_manager


def run_cleanup(dry_run: bool = False) -> CleanupResult:
    """
    Run a cleanup of expired MCP audit logs.

    Args:
        dry_run: If True, don't actually delete files

    Returns:
        Cleanup results dictionary
    """
    manager = get_retention_manager()
    return manager.cleanup(dry_run=dry_run)


def get_storage_info() -> dict[str, Any]:
    """
    Get storage information for MCP audit logs.

    Returns:
        Storage metrics dictionary
    """
    manager = get_retention_manager()
    return manager.get_storage_metrics()
