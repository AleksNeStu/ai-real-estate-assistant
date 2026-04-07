"""JWT token creation and validation."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import jwt

from config.settings import get_settings


def get_jwt_secret() -> str:
    """Get JWT secret key from settings."""
    settings = get_settings()
    secret = settings.jwt_secret_key
    if not secret:
        # Generate a random secret for development (not for production!)
        if settings.environment.lower() == "production":
            raise ValueError("JWT_SECRET_KEY must be set in production")
        # Use a deterministic secret for development to allow token persistence across restarts
        secret = "dev-jwt-secret-key-change-in-production"
    return secret


def get_jwt_algorithm() -> str:
    """Get JWT algorithm from settings."""
    settings = get_settings()
    return settings.jwt_algorithm or "HS256"


def get_access_token_expire_minutes() -> int:
    """Get access token expiration time in minutes."""
    settings = get_settings()
    return settings.jwt_access_token_expire_minutes or 15


def get_refresh_token_expire_days() -> int:
    """Get refresh token expiration time in days."""
    settings = get_settings()
    return settings.jwt_refresh_token_expire_days or 7


def create_access_token(
    subject: str,
    roles: Optional[list[str]] = None,
    additional_claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Token subject (usually user ID)
        roles: List of user roles
        additional_claims: Additional claims to include in the token
        expires_delta: Custom expiration time delta

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=get_access_token_expire_minutes())

    now = datetime.now(UTC)
    expire = now + expires_delta

    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "access",
    }

    if roles:
        to_encode["roles"] = roles

    if additional_claims:
        to_encode.update(additional_claims)

    # Add issuer if configured
    if hasattr(settings, "app_title"):
        to_encode["iss"] = settings.app_title

    encoded_jwt = jwt.encode(
        to_encode,
        get_jwt_secret(),
        algorithm=get_jwt_algorithm(),
    )
    return encoded_jwt


def verify_access_token(token: str) -> dict[str, Any]:
    """
    Verify and decode a JWT access token.

    Args:
        token: Encoded JWT token string

    Returns:
        Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
    """
    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[get_jwt_algorithm()],
        options={
            "verify_exp": True,
            "verify_iat": True,
            "require": ["exp", "iat", "sub"],
        },
    )

    # Verify token type
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload


def _decode_access_token_unsafe(token: str) -> Optional[dict[str, Any]]:
    """
    INTERNAL: Decode a JWT access token WITHOUT signature verification.
    
    WARNING: This function does NOT verify the token signature.
    It only decodes the token payload. DO NOT use for authentication.
    This is intended for internal debugging only.
    
    Args:
        token: Encoded JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    import warnings
    warnings.warn(
        "decode_access_token is deprecated and will be removed. "
        "Use verify_access_token instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        return jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[get_jwt_algorithm()],
            options={"verify_signature": False},
        )
    except jwt.PyJWTError:
        return None


# Alias for backwards compatibility (triggers deprecation warning)
import functools
decode_access_token = functools.partial(_decode_access_token_unsafe)


def generate_refresh_token() -> str:
    """
    Generate a secure refresh token.

    Returns:
        URL-safe refresh token string
    """
    return secrets.token_urlsafe(32)


def generate_verification_token() -> str:
    """
    Generate a secure email verification token.

    Returns:
        URL-safe verification token string
    """
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """
    Generate a secure password reset token.

    Returns:
        URL-safe reset token string
    """
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """
    Generate a CSRF token.

    Returns:
        URL-safe CSRF token string
    """
    return secrets.token_urlsafe(32)


def create_csrf_token_hash(csrf_token: str) -> str:
    """
    Create a hash of the CSRF token for cookie storage.

    Args:
        csrf_token: CSRF token to hash

    Returns:
        SHA256 hash of the token
    """
    import hashlib

    return hashlib.sha256(csrf_token.encode()).hexdigest()
