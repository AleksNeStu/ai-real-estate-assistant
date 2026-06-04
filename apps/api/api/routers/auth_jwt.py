"""JWT Authentication endpoints.

This module provides JWT-based authentication endpoints including:
- User registration
- Login (email/password)
- Logout
- Token refresh
- Current user info
- Email verification
- Password reset
- OAuth (Google, Apple)
"""

import logging
import time
from typing import Optional

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from api.audit import AuditEvent, AuditEventType, AuditLevel, get_audit_logger
from api.deps.auth import get_current_active_user
from config.settings import get_settings
from core.email import get_email_service
from core.jwt import (
    create_access_token,
    generate_refresh_token,
    get_access_token_expire_minutes,
    get_refresh_token_expire_days,
)
from core.lockout import AccountLockoutService
from core.password import hash_password, needs_rehash, verify_password
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import User
from db.repositories import (
    OAuthAccountRepository,
    RefreshTokenRepository,
    UserRepository,
)
from db.schemas import (
    MessageResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["JWT Auth"])


# Auth-specific rate limiting (in-memory, per-instance)
_auth_rate_limits: dict[str, list[float]] = {}


def _check_auth_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int = 60,
) -> tuple[bool, int]:
    """Check auth-specific rate limit."""
    now = time.time()
    window_start = now - window_seconds

    if key not in _auth_rate_limits:
        _auth_rate_limits[key] = []

    _auth_rate_limits[key] = [ts for ts in _auth_rate_limits[key] if ts > window_start]

    if len(_auth_rate_limits[key]) >= max_requests:
        oldest = min(_auth_rate_limits[key])
        retry_after = int(oldest + window_seconds - now) + 1
        return False, max(1, retry_after)

    _auth_rate_limits[key].append(now)
    return True, 0


def _get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def auth_rate_limit(max_requests: int, window_seconds: int = 60):
    """Dependency-based rate limiter for auth endpoints.

    Returns a FastAPI dependency that checks rate limits before the
    endpoint runs. This preserves the original endpoint signature so
    that FastAPI's dependency injection continues to work correctly.
    """

    async def _check(request: Request) -> None:
        client_ip = _get_client_ip(request)
        key = f"auth:{request.url.path}:{client_ip}"
        allowed, retry_after = _check_auth_rate_limit(key, max_requests, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Try again in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return Depends(_check)


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: Optional[str] = None,
) -> None:
    """Set authentication cookies on response."""
    settings = get_settings()

    # Access token cookie (short-lived)
    access_max_age = get_access_token_expire_minutes() * 60
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=access_max_age,
        path="/",
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="strict",
    )

    # Refresh token cookie (long-lived, restricted path)
    refresh_max_age = get_refresh_token_expire_days() * 24 * 60 * 60
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=refresh_max_age,
        path="/api/v1/auth/refresh",
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="strict",
    )

    # CSRF token cookie (for double-submit pattern)
    if csrf_token:
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            max_age=access_max_age,
            path="/",
            httponly=False,  # Must be readable by JavaScript
            secure=settings.environment.lower() == "production",
            samesite="strict",
        )


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")
    response.delete_cookie(key="csrf_token", path="/")


def _get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extract client info from request."""
    user_agent = request.headers.get("user-agent")
    # Handle proxied requests
    forwarded = request.headers.get("x-forwarded-for")
    client_host = request.client.host if request.client else None
    ip_address = forwarded or client_host
    if ip_address and "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    return user_agent, ip_address


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password.",
    dependencies=[auth_rate_limit(max_requests=3, window_seconds=60)],
)
async def register(
    body: UserCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user."""
    settings = get_settings()

    if not settings.auth_registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled",
        )

    user_repo = UserRepository(session)

    # Check if user already exists
    existing_user = await user_repo.get_by_email(body.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    hashed_password = hash_password(body.password)
    # Auto-verify if email verification not required
    is_verified = not settings.auth_email_verification_required
    user = await user_repo.create(
        email=body.email,
        hashed_password=hashed_password,
        full_name=body.full_name,
        is_verified=is_verified,
    )

    # Generate tokens
    access_token = create_access_token(
        subject=user.id,
        roles=[user.role],
    )
    refresh_token = generate_refresh_token()

    # Store refresh token
    user_agent, ip_address = _get_client_info(request)
    refresh_repo = RefreshTokenRepository(session)
    await refresh_repo.create(
        user_id=user.id,
        token=refresh_token,
        expires_days=get_refresh_token_expire_days(),
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Set cookies
    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_access_token_expire_minutes() * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="Authenticate user and return tokens.",
    dependencies=[auth_rate_limit(max_requests=5, window_seconds=60)],
)
async def login(
    body: UserLogin,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Login with email and password."""
    user_repo = UserRepository(session)
    lockout_service = AccountLockoutService(session)
    audit_logger = get_audit_logger()
    ip_address = _get_client_ip(request)

    # Find user
    user = await user_repo.get_by_email(body.email)
    if not user:
        # Log failed login attempt (user not found)
        audit_logger.log(
            AuditEvent(
                event_type=AuditEventType.AUTH_LOGIN_FAILURE,
                level=AuditLevel.HIGH,
                resource="/auth/login",
                action="login",
                result="failure",
                ip_address=ip_address,
                metadata={"reason": "user_not_found", "email": body.email[:4] + "***"},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if account is locked (Task #47: Account Lockout)
    is_locked, locked_for_seconds = await lockout_service.check_lockout(user)
    if is_locked:
        # Log lockout event
        audit_logger.log(
            AuditEvent(
                event_type=AuditEventType.AUTH_ACCOUNT_LOCKED,
                level=AuditLevel.HIGH,
                user_id=user.id,
                resource="/auth/login",
                action="login",
                result="blocked",
                ip_address=ip_address,
                metadata={"reason": "account_locked", "locked_for_seconds": locked_for_seconds},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is temporarily locked. Try again in {locked_for_seconds // 60} minutes.",
            headers={"Retry-After": str(locked_for_seconds)},
        )

    # Verify password
    password_valid = user.hashed_password and verify_password(body.password, user.hashed_password)
    if not password_valid:
        # Record failed attempt (Task #47: Account Lockout)
        is_now_locked, _ = await lockout_service.record_failed_attempt(user)

        # Log failed login attempt
        audit_logger.log(
            AuditEvent(
                event_type=AuditEventType.AUTH_LOGIN_FAILURE,
                level=AuditLevel.HIGH,
                user_id=user.id,
                resource="/auth/login",
                action="login",
                result="failure",
                ip_address=ip_address,
                metadata={
                    "reason": "invalid_password",
                    "attempts": user.failed_login_attempts + 1,
                    "account_locked": is_now_locked,
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Clear failed attempts on successful login (Task #47: Account Lockout)
    await lockout_service.clear_failed_attempts(user)

    # Log successful login
    audit_logger.log(
        AuditEvent(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            level=AuditLevel.MEDIUM,
            user_id=user.id,
            resource="/auth/login",
            action="login",
            result="success",
            ip_address=ip_address,
            metadata={"method": "password"},
        )
    )

    # Rehash password if needed (algorithm upgrade)
    if needs_rehash(user.hashed_password):
        await user_repo.set_password(user, hash_password(body.password))

    # Update last login
    await user_repo.update_last_login(user)

    # Generate tokens
    access_token = create_access_token(
        subject=user.id,
        roles=[user.role],
    )
    refresh_token = generate_refresh_token()

    # Store refresh token
    user_agent, ip_address = _get_client_info(request)
    refresh_repo = RefreshTokenRepository(session)
    await refresh_repo.create(
        user_id=user.id,
        token=refresh_token,
        expires_days=get_refresh_token_expire_days(),
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Set cookies
    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_access_token_expire_minutes() * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Invalidate the current session and clear cookies.",
)
async def logout(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Logout and invalidate refresh token."""
    if refresh_token:
        refresh_repo = RefreshTokenRepository(session)
        stored_token = await refresh_repo.get_by_token(refresh_token)
        if stored_token:
            await refresh_repo.revoke(stored_token)

    # Clear cookies
    _clear_auth_cookies(response)

    return MessageResponse(message="Successfully logged out")


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange refresh token for new access token.",
)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    refresh_repo = RefreshTokenRepository(session)
    user_repo = UserRepository(session)

    # Validate refresh token
    stored_token = await refresh_repo.get_by_token(refresh_token)
    if not stored_token or not stored_token.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user
    user = await user_repo.get_by_id(stored_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old token (rotation)
    await refresh_repo.revoke(stored_token)

    # Generate new tokens
    new_access_token = create_access_token(
        subject=user.id,
        roles=[user.role],
    )
    new_refresh_token = generate_refresh_token()

    # Store new refresh token
    user_agent, ip_address = _get_client_info(request)
    await refresh_repo.create(
        user_id=user.id,
        token=new_refresh_token,
        expires_days=get_refresh_token_expire_days(),
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Set cookies
    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=get_access_token_expire_minutes() * 60,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the currently authenticated user's profile.",
)
async def get_current_user_info(
    user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Get current user info."""
    return UserResponse.model_validate(user)


# Email Verification Endpoints


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address",
    description="Verify user email with token sent via email.",
)
async def verify_email(
    body: dict[str, str],
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Verify email address with token."""
    from db.repositories import EmailVerificationTokenRepository

    token = body.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is required",
        )

    token_repo = EmailVerificationTokenRepository(session)
    user_repo = UserRepository(session)

    stored_token = await token_repo.get_by_token(token)
    if not stored_token or not stored_token.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Get user and mark as verified
    user = await user_repo.get_by_id(stored_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await user_repo.set_verified(user)
    await token_repo.mark_used(stored_token)

    return MessageResponse(
        message="Email verified successfully",
        detail="You can now log in to your account.",
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
    description="Request a new email verification token.",
    dependencies=[auth_rate_limit(max_requests=3, window_seconds=60)],
)
async def resend_verification(
    body: dict[str, str],
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Resend verification email."""
    from db.repositories import EmailVerificationTokenRepository

    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(email)

    # Don't reveal if user exists or is already verified
    if not user or user.is_verified:
        return MessageResponse(
            message="If the email exists and is not verified, "
            "a new verification email has been sent.",
        )

    # Invalidate existing tokens
    token_repo = EmailVerificationTokenRepository(session)
    await token_repo.invalidate_for_user(user.id)

    # Generate new token
    from core.jwt import generate_verification_token

    verification_token = generate_verification_token()
    await token_repo.create(
        user_id=user.id,
        token=verification_token,
        expires_hours=24,
    )

    # Send verification email
    settings = get_settings()
    if settings.environment.lower() == "development":
        logger.info(
            "Verification token generated for %s (prefix: %s...)",
            sanitize_for_log(email),
            sanitize_for_log(verification_token[:4]),
        )

    # Send email using email service
    email_service = get_email_service()
    verification_url = f"{settings.frontend_url}/auth/verify-email"
    await email_service.send_verification_email(
        to=user.email,
        verification_token=verification_token,
        verification_url=verification_url,
    )

    return MessageResponse(
        message="If the email exists and is not verified, a new verification email has been sent.",
    )


# Password Reset Endpoints


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Request a password reset email.",
    dependencies=[auth_rate_limit(max_requests=3, window_seconds=60)],
)
async def forgot_password(
    body: dict[str, str],
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Request password reset email."""
    from db.repositories import PasswordResetTokenRepository

    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(email)

    # Don't reveal if user exists
    if not user:
        return MessageResponse(
            message="If the email exists, a password reset email has been sent.",
        )

    # Generate reset token
    from core.jwt import generate_password_reset_token

    reset_token = generate_password_reset_token()
    token_repo = PasswordResetTokenRepository(session)
    await token_repo.create(
        user_id=user.id,
        token=reset_token,
        expires_hours=1,  # 1 hour expiry
    )

    # Send reset email
    settings = get_settings()
    if settings.environment.lower() == "development":
        logger.info(
            "Password reset token generated for %s (prefix: %s...)",
            sanitize_for_log(email),
            sanitize_for_log(reset_token[:4]),
        )

    # Send email using email service
    email_service = get_email_service()
    reset_url = f"{settings.frontend_url}/auth/reset-password"
    await email_service.send_password_reset_email(
        to=user.email,
        reset_token=reset_token,
        reset_url=reset_url,
    )

    return MessageResponse(
        message="If the email exists, a password reset email has been sent.",
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password",
    description="Reset password using token from email.",
)
async def reset_password(
    body: dict[str, str],
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Reset password with token."""
    from db.repositories import PasswordResetTokenRepository

    token = body.get("token")
    new_password = body.get("new_password")

    if not token or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token and new_password are required",
        )

    # Validate password strength
    from core.password import validate_password_strength

    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    token_repo = PasswordResetTokenRepository(session)
    user_repo = UserRepository(session)

    stored_token = await token_repo.get_by_token(token)
    if not stored_token or not stored_token.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Get user and update password
    user = await user_repo.get_by_id(stored_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    hashed_password = hash_password(new_password)
    await user_repo.set_password(user, hashed_password)
    await token_repo.mark_used(stored_token)

    # Revoke all refresh tokens for security
    refresh_repo = RefreshTokenRepository(session)
    await refresh_repo.revoke_all_for_user(user.id)

    return MessageResponse(
        message="Password reset successfully",
        detail="You can now log in with your new password.",
    )


# Admin Endpoints (Task #47: Auth Security Hardening)


@router.post(
    "/admin/unlock-account",
    response_model=MessageResponse,
    summary="Unlock a locked account",
    description="Admin endpoint to unlock a user account that was locked due to failed login attempts.",
)
async def admin_unlock_account(
    body: dict[str, str],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """
    Unlock a locked user account (admin only).

    Requires admin role. Provide user_id in request body.
    """
    from api.rbac import Role

    # Check admin role
    if current_user.role != Role.ADMIN.value and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    lockout_service = AccountLockoutService(session)
    await lockout_service.unlock_account(user)

    logger.info(
        "admin_account_unlocked",
        extra={
            "event": "admin_account_unlocked",
            "admin_id": current_user.id,
            "unlocked_user_id": user.id,
        },
    )

    return MessageResponse(
        message="Account unlocked successfully",
        detail=f"Account for {user.email} has been unlocked.",
    )


# OAuth Endpoints


@router.get(
    "/oauth/google",
    summary="Start Google OAuth flow",
    description="Redirect to Google for OAuth authentication.",
)
async def google_oauth_start(
    request: Request,
    response: Response,
) -> dict:
    """Start Google OAuth flow."""
    settings = get_settings()

    if not settings.auth_oauth_google_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google OAuth is not enabled",
        )

    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured",
        )

    from core.oauth import GoogleOAuthProvider

    provider = GoogleOAuthProvider(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )

    # Generate state and PKCE verifier
    import secrets

    state = secrets.token_urlsafe(32)
    code_verifier = GoogleOAuthProvider.generate_pkce_verifier()
    code_challenge = GoogleOAuthProvider.generate_pkce_challenge(code_verifier)

    # Store state and verifier in session/cookie for callback
    # Using cookies for simplicity (in production, use server-side sessions)
    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=600,  # 10 minutes
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
    )
    response.set_cookie(
        key="oauth_code_verifier",
        value=code_verifier,
        max_age=600,  # 10 minutes
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
    )

    auth_url = provider.get_authorization_url(
        state=state,
        code_challenge=code_challenge,
    )

    return {"authorization_url": auth_url}


@router.get(
    "/oauth/callback",
    response_model=TokenResponse,
    summary="OAuth callback",
    description="Handle OAuth callback from providers.",
)
async def oauth_callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Handle OAuth callback."""
    settings = get_settings()

    # Check for OAuth errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter",
        )

    # Verify state
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    # Get code verifier
    code_verifier = request.cookies.get("oauth_code_verifier")

    # Clear OAuth cookies
    response.delete_cookie(key="oauth_state")
    response.delete_cookie(key="oauth_code_verifier")

    # Use Google provider
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured",
        )

    from core.oauth import GoogleOAuthProvider, OAuthError

    provider = GoogleOAuthProvider(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )

    try:
        user_info = await provider.verify_and_get_user(code, code_verifier)
    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    # Find or create user
    user_repo = UserRepository(session)
    oauth_repo = OAuthAccountRepository(session)

    # Check if OAuth account exists
    oauth_account = await oauth_repo.get_by_provider(
        provider=user_info.provider,
        provider_user_id=user_info.provider_user_id,
    )

    if oauth_account:
        # Existing user - get user
        user = await user_repo.get_by_id(oauth_account.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User not found for OAuth account",
            )
    else:
        # New OAuth user - check if email exists
        if user_info.email:
            existing_user = await user_repo.get_by_email(user_info.email)
            if existing_user:
                # Link OAuth account to existing user
                await oauth_repo.create(
                    user_id=existing_user.id,
                    provider=user_info.provider,
                    provider_user_id=user_info.provider_user_id,
                    provider_email=user_info.email,
                )
                user = existing_user
            else:
                # Create new user
                user = await user_repo.create(
                    email=user_info.email,
                    full_name=user_info.name,
                    is_verified=user_info.email_verified,
                )
                await oauth_repo.create(
                    user_id=user.id,
                    provider=user_info.provider,
                    provider_user_id=user_info.provider_user_id,
                    provider_email=user_info.email,
                )
        else:
            # No email - create user without email
            user = await user_repo.create(
                email=f"{user_info.provider}_{user_info.provider_user_id}@oauth.local",
                full_name=user_info.name,
                is_verified=False,
            )
            await oauth_repo.create(
                user_id=user.id,
                provider=user_info.provider,
                provider_user_id=user_info.provider_user_id,
                provider_email=user_info.email,
            )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    await user_repo.update_last_login(user)

    # Generate tokens
    access_token = create_access_token(
        subject=user.id,
        roles=[user.role],
    )
    refresh_token_value = generate_refresh_token()

    # Store refresh token
    user_agent, ip_address = _get_client_info(request)
    refresh_repo = RefreshTokenRepository(session)
    await refresh_repo.create(
        user_id=user.id,
        token=refresh_token_value,
        expires_days=get_refresh_token_expire_days(),
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Set cookies
    _set_auth_cookies(response, access_token, refresh_token_value)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_value,
        token_type="bearer",
        expires_in=get_access_token_expire_minutes() * 60,
        user=UserResponse.model_validate(user),
    )


# Apple OAuth Endpoints


@router.get(
    "/oauth/apple",
    summary="Start Apple OAuth flow",
    description="Redirect to Apple for Sign In.",
)
async def apple_oauth_start(
    request: Request,
    response: Response,
) -> dict:
    """Start Apple Sign-In OAuth flow."""
    settings = get_settings()

    if not settings.auth_oauth_apple_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apple Sign-In is not enabled",
        )

    if not settings.apple_client_id or not settings.apple_team_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Apple Sign-In is not configured",
        )

    # Read private key from file if path is provided
    private_key = None
    if settings.apple_private_key_path:
        try:
            with open(settings.apple_private_key_path, "r") as f:
                private_key = f.read()
        except Exception as e:
            logger.error("Failed to read Apple private key: %s", sanitize_for_log(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Apple Sign-In private key not found",
            ) from None

    if not private_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Apple Sign-In private key not configured",
        )

    from core.oauth import AppleOAuthProvider

    provider = AppleOAuthProvider(
        client_id=settings.apple_client_id,
        client_secret="",  # Not used for Apple
        redirect_uri=settings.google_redirect_uri.replace("google", "apple"),  # Use same base
        team_id=settings.apple_team_id,
        key_id=settings.apple_key_id or "",
        private_key=private_key,
    )

    # Generate state and PKCE verifier
    import secrets

    state = secrets.token_urlsafe(32)
    code_verifier = AppleOAuthProvider.generate_pkce_verifier()
    code_challenge = AppleOAuthProvider.generate_pkce_challenge(code_verifier)

    # Store state and verifier in cookies for callback
    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
    )
    response.set_cookie(
        key="oauth_code_verifier",
        value=code_verifier,
        max_age=600,
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
    )
    response.set_cookie(
        key="oauth_provider",
        value="apple",
        max_age=600,
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
    )

    auth_url = provider.get_authorization_url(
        state=state,
        code_challenge=code_challenge,
    )

    return {"authorization_url": auth_url}
