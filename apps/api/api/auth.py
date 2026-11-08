import hmac
import logging

from fastapi import HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader

from api.audit import AuditEvent, AuditEventType, AuditLevel, get_audit_logger
from config.settings import get_settings

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _is_valid_api_key(candidate: str, valid_keys: list[str]) -> bool:
    """Constant-time comparison of API key candidate against valid keys."""
    for key in valid_keys:
        if key and hmac.compare_digest(candidate, key):
            return True
    return False


async def get_api_key(
    request: Request,
    api_key_header: str = Security(api_key_header),
):
    """
    Validate API key from header.

    In demo mode, returns a fixed placeholder key without validation.

    Args:
        request: FastAPI request object for accessing request_id
        api_key_header: API key from X-API-Key header

    Returns:
        The valid API key

    Raises:
        HTTPException: If key is invalid or missing
    """
    settings = get_settings()

    if settings.demo_api_key_bypass:
        return "demo-mode-key"

    candidate = api_key_header.strip() if isinstance(api_key_header, str) else ""
    if not candidate:
        # Log missing API key attempt with request correlation
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "auth_missing_api_key",
            extra={
                "event": "auth_missing_api_key",
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
        )
        audit_logger.log_auth_failure(
            reason="missing_api_key",
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    configured_keys = getattr(settings, "api_access_keys", None)
    if not isinstance(configured_keys, list):
        configured_keys = []

    normalized_keys = [k.strip() for k in configured_keys if isinstance(k, str) and k.strip()]
    if not normalized_keys:
        configured_key = getattr(settings, "api_access_key", None)
        if isinstance(configured_key, str) and configured_key.strip():
            normalized_keys = [configured_key.strip()]

    environment = str(getattr(settings, "environment", "") or "").strip().lower()

    if environment == "production":
        if not normalized_keys or any(k == "dev-secret-key" for k in normalized_keys):
            # Log production misconfiguration
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                "auth_production_misconfiguration",
                extra={
                    "event": "auth_production_misconfiguration",
                    "request_id": request_id,
                },
            )
            audit_logger.log(
                event=AuditEvent(
                    event_type=AuditEventType.AUTH_PRODUCTION_MISCONFIG,
                    level=AuditLevel.CRITICAL,
                    result="failure",
                    request_id=request_id,
                )
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")

    if _is_valid_api_key(candidate, normalized_keys):
        audit_logger.log_auth_success(
            client_id=candidate,
            request_id=getattr(request.state, "request_id", "unknown"),
        )
        return candidate

    # Log failed auth attempt without exposing the key
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "auth_invalid_credentials",
        extra={
            "event": "auth_invalid_credentials",
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            # Only log first 4 chars of key for debugging (safe)
            "key_prefix": candidate[:4] if len(candidate) >= 4 else candidate,
        },
    )
    audit_logger.log_auth_failure(
        reason="invalid_credentials",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        key_prefix=candidate[:4] if len(candidate) >= 4 else candidate,
    )

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")


async def get_optional_api_key(
    request: Request,
    api_key_header: str = Security(api_key_header),
) -> str | None:
    """
    Optional API key validation that allows demo mode access.

    When DEMO_MODE setting is enabled, always returns the demo key.
    For GET requests with X-Demo-Mode header or ?demo=true query param,
    returns None (no auth required). Otherwise, validates the API key normally.
    Intended for read-only public endpoints (search, city-overview).
    """
    settings = get_settings()

    # Server-side demo mode always passes
    if settings.demo_api_key_bypass:
        return "demo-mode-key"

    # Check demo mode indicators from client
    is_demo = request.headers.get("x-demo-mode", "").lower() == "true"
    if not is_demo:
        is_demo = request.query_params.get("demo", "").lower() == "true"

    if is_demo and request.method == "GET":
        return None

    # Fall through to normal API key validation
    return await get_api_key(request, api_key_header)
