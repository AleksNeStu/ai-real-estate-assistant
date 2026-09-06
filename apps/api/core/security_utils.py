"""
Security utilities for input sanitization and secure logging.

This module provides functions to prevent common security vulnerabilities:
- Log injection attacks
- Path traversal attacks
- SSRF (Server-Side Request Forgery)
- Weak sensitive data hashing
"""

import hashlib
import hmac
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

# Characters dangerous in logs (newlines, tabs, etc.)
LOG_SANITIZE_PATTERN = re.compile(r"[\n\r\t]")

# Dangerous path traversal patterns
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.[/\\]")

# Allowed OSRM server pattern (prevent SSRF)
ALLOWED_OSRM_PATTERN = re.compile(r"^https?://[a-zA-Z0-9.-]+(:\d+)?/([a-z]+)/")


def sanitize_for_log(value: Any, max_length: int = 500) -> str:
    """
    Sanitize a value for safe logging.

    Removes control characters (newlines, tabs, etc.) that could enable
    log injection attacks, and truncates to prevent log flooding.

    Args:
        value: Any value to sanitize
        max_length: Maximum length of returned string (default: 500)

    Returns:
        Sanitized string safe for logging
    """
    if value is None:
        return ""
    str_value = str(value)
    # Remove newlines, tabs, and other control characters
    sanitized = LOG_SANITIZE_PATTERN.sub(" ", str_value)
    # Truncate to prevent log flooding
    return sanitized[:max_length]


def validate_file_path(file_path: str, allowed_base_dir: Optional[str] = None) -> bool:
    """
    Validate file path to prevent path traversal attacks.

    Checks for:
    - Path traversal patterns (../)
    - Resolution outside allowed directory

    Args:
        file_path: File path to validate
        allowed_base_dir: If provided, path must be within this directory

    Returns:
        True if path is safe, False otherwise
    """
    try:
        path = Path(file_path).resolve()

        # Check for obvious path traversal patterns
        if PATH_TRAVERSAL_PATTERN.search(file_path):
            return False

        # If base dir specified, ensure path is within it
        if allowed_base_dir:
            base = Path(allowed_base_dir).resolve()
            try:
                path.relative_to(base)
            except ValueError:
                return False

        return True
    except (OSError, ValueError):
        return False


def validate_osrm_url(url: str) -> bool:
    """
    Validate OSRM routing URL to prevent SSRF attacks.

    Only allows requests to known OSRM server patterns.

    Args:
        url: URL to validate

    Returns:
        True if URL matches allowed OSRM pattern
    """
    return bool(ALLOWED_OSRM_PATTERN.match(url))


def hash_sensitive_data(data: str, algorithm: str = "sha256") -> str:
    """
    Hash sensitive data with a secure algorithm.

    Uses SHA-256 or SHA-512 instead of weak algorithms like MD5.

    Args:
        data: Data to hash
        algorithm: Hash algorithm to use ("sha256" or "sha512")

    Returns:
        Hexadecimal hash string

    Raises:
        ValueError: If unsupported algorithm is specified
    """
    if algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


# Server-side pepper used to derive keyed fingerprints (client_id, token digests).
# A static fallback is used only when the env var is not configured; deployments
# should set SECURITY_PEPPER to a high-entropy secret.
_SECURITY_PEPPER = (
    os.getenv("SECURITY_PEPPER")
    or "change-me-set-SECURITY_PEPPER-env-var-in-production-environments"
).encode("utf-8")

if not os.getenv("SECURITY_PEPPER"):
    logging.getLogger(__name__).warning(
        "SECURITY_PEPPER env var is not set; using insecure placeholder. "
        "Set SECURITY_PEPPER to a high-entropy secret in production."
    )


def hash_fingerprint(value: str, length: int = 16) -> str:
    """
    Derive a non-reversible, collision-resistant fingerprint of a high-entropy
    value (API key, token) using HMAC-SHA-256 with a server-side pepper.

    Use this for client identifiers and at-rest token digests — never for
    user-chosen passwords (which require argon2/bcrypt and slow hashing).

    Args:
        value: High-entropy secret to fingerprint.
        length: Number of hex chars to return (default 16, max 64).

    Returns:
        Hex string of the requested length.
    """
    digest = hmac.new(_SECURITY_PEPPER, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[: max(0, min(length, 64))]


class SecureLogger:
    """
    Logger wrapper that automatically sanitizes all log messages.

    Prevents log injection by sanitizing message format string
    and all arguments before passing to underlying logger.
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize secure logger wrapper.

        Args:
            logger: The underlying logger to wrap
        """
        self._logger = logger

    def _sanitize_args(self, args: tuple) -> tuple:
        """Sanitize all arguments before logging."""
        return tuple(sanitize_for_log(arg) for arg in args)

    def debug(self, msg: Any, *args, **kwargs):
        """Log debug message with sanitization."""
        self._logger.debug(sanitize_for_log(msg), *self._sanitize_args(args), **kwargs)

    def info(self, msg: Any, *args, **kwargs):
        """Log info message with sanitization."""
        self._logger.info(sanitize_for_log(msg), *self._sanitize_args(args), **kwargs)

    def warning(self, msg: Any, *args, **kwargs):
        """Log warning message with sanitization."""
        self._logger.warning(sanitize_for_log(msg), *self._sanitize_args(args), **kwargs)

    def error(self, msg: Any, *args, **kwargs):
        """Log error message with sanitization."""
        self._logger.error(sanitize_for_log(msg), *self._sanitize_args(args), **kwargs)

    def critical(self, msg: Any, *args, **kwargs):
        """Log critical message with sanitization."""
        self._logger.critical(sanitize_for_log(msg), *self._sanitize_args(args), **kwargs)

    def exception(self, msg: Any, *args, **kwargs):
        """Log exception message with sanitization."""
        self._logger.exception(sanitize_for_log(msg), *self._sanitize_args(args), **kwargs)


def get_secure_logger(name: str) -> SecureLogger:
    """
    Get a secure logger instance for the given name.

    Args:
        name: Logger name (typically __name__ of calling module)

    Returns:
        SecureLogger instance wrapping the named logger
    """
    return SecureLogger(logging.getLogger(name))
