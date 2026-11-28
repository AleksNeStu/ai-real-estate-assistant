"""Authentication dependencies for FastAPI."""

from typing import Optional, Set

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import api_key_header as api_key_header_param
from api.auth import get_api_key
from api.rbac import ROLE_PERMISSIONS, Permission, Role
from config.settings import get_settings
from core.jwt import verify_access_token
from db.database import get_db
from db.models import User
from db.repositories import UserRepository

# Optional Bearer token security (for API clients)
bearer_security = HTTPBearer(auto_error=False)


def _get_demo_user() -> User:
    """
    Create a demo user for demo mode.

    Returns a User instance without database dependency for demo/testing.
    Includes additional profile fields for ProfileResponse compatibility.
    """
    from datetime import UTC, datetime

    # Create a simple User object (not a database model)
    demo_user = User()
    demo_user.id = "demo-user-id"
    demo_user.email = "demo@example.com"
    demo_user.full_name = "Demo User"
    demo_user.is_active = True
    demo_user.is_verified = True
    demo_user.role = "admin"
    demo_user.hashed_password = None  # No password for demo user
    demo_user.created_at = datetime.now(UTC)
    demo_user.updated_at = datetime.now(UTC)

    # Add profile fields for ProfileResponse compatibility
    demo_user.phone = None
    demo_user.avatar_url = None
    demo_user.timezone = "UTC"
    demo_user.language = "en"
    demo_user.bio = "Demo mode user"
    demo_user.privacy_settings = {"profile_visible": True, "activity_visible": False}
    demo_user.gdpr_consent_at = None
    demo_user.last_login_at = datetime.now(UTC)

    return demo_user


class AuthCredentials:
    """Container for authenticated user credentials with RBAC integration."""

    # Role string to Role enum mapping
    _ROLE_MAPPING = {
        "admin": Role.ADMIN,
        "user": Role.USER,
        "read_only": Role.READ_ONLY,
        "api_client": Role.API_CLIENT,
    }

    def __init__(self, user: User, token_payload: dict):
        self.user = user
        self.token_payload = token_payload
        self.user_id = user.id
        self.email = user.email
        # Raw roles from JWT token
        self._raw_roles = token_payload.get("roles", ["user"])
        # Map to RBAC Role enum
        self.roles = self._map_roles(self._raw_roles)
        # Get permissions from roles
        self.permissions = self._get_permissions()

    def _map_roles(self, raw_roles: list[str]) -> Set[Role]:
        """Map string roles to RBAC Role enum."""
        mapped = set()
        for role_str in raw_roles:
            role = self._ROLE_MAPPING.get(role_str.lower())
            if role:
                mapped.add(role)
            else:
                # Default to USER for unknown roles
                mapped.add(Role.USER)
        return mapped

    def _get_permissions(self) -> Set[Permission]:
        """Get all permissions for user's roles."""
        permissions = set()
        for role in self.roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        return permissions

    def has_role(self, role: Role) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return Role.ADMIN in self.roles


async def _get_user_from_token(
    token: str,
    session: AsyncSession,
) -> tuple[User, dict]:
    """
    Validate token and return user with payload.

    Args:
        token: JWT access token
        session: Database session

    Returns:
        Tuple of (User, token_payload)

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user, payload


async def _extract_token(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
) -> Optional[str]:
    """
    Extract token from cookie or Authorization header.

    Priority:
    1. Authorization header (Bearer token)
    2. Cookie (access_token)
    """
    # Check Authorization header first
    if credentials:
        return credentials.credentials

    # Then check cookie
    if access_token:
        return access_token

    return None


async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current authenticated user.

    This dependency extracts the token from either:
    - Authorization: Bearer <token> header
    - access_token cookie

    In demo mode, returns a demo user without requiring authentication.

    Returns:
        User model instance

    Raises:
        HTTPException: 401 if not authenticated (and not in demo mode)
    """
    # Check if demo mode is active (from session or environment)
    settings = get_settings()
    session_id = request.headers.get("X-Session-ID", "default")

    # Check session-based demo mode first
    from api.routers.settings import _DEMO_MODE_SESSIONS

    is_demo_session = _DEMO_MODE_SESSIONS.get(session_id, False)

    # Check environment-based demo mode
    is_demo_env = settings.demo_user_bypass

    # A real session always wins. The token is read first, so a visitor who
    # signed in is that account even on a demo deployment: the synthetic demo
    # user used to answer before the token was even looked at, which made the
    # sign-in a decoration. Only a request without a token falls back.
    token = await _extract_token(request, access_token, credentials)

    if token:
        user, _ = await _get_user_from_token(token, session)

        # Set Sentry user context for error tracking
        try:
            from api.sentry_init import set_user_context

            set_user_context(user_id=str(user.id), email=user.email)
        except ImportError:
            pass  # Sentry not available

        return user

    # No token: the demo user steps in when the deployment allows it.
    if is_demo_session or is_demo_env:
        return _get_demo_user()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get the current authenticated user if available.

    This is similar to get_current_user but returns None instead of raising
    an exception when not authenticated. Useful for endpoints that work
    with both authenticated and anonymous users.

    Returns:
        User model instance if authenticated, None otherwise
    """
    token = await _extract_token(request, access_token, credentials)

    if not token:
        return None

    user, _ = await _get_user_from_token(token, session)
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    This dependency requires the user to be active.

    Returns:
        Active User model instance

    Raises:
        HTTPException: 403 if user is inactive
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


async def get_current_verified_user(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    Get the current verified user.

    This dependency requires the user to have a verified email.

    Returns:
        Verified User model instance

    Raises:
        HTTPException: 403 if user is not verified
    """
    settings = get_settings()

    # Skip verification requirement if disabled
    if not settings.auth_email_verification_required:
        return user

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return user


async def get_optional_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.

    This is useful for endpoints that behave differently
    for authenticated vs anonymous users.

    Returns:
        User model instance or None
    """
    token = await _extract_token(request, access_token, credentials)

    if not token:
        return None

    try:
        user, _ = await _get_user_from_token(token, session)
        return user
    except HTTPException:
        return None


async def get_proven_user_email(
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
) -> Optional[str]:
    """
    The e-mail the request proved - never the e-mail it claimed.

    A request may carry an ``X-User-Email`` header, and a browser may put
    any address in it. The header is an assertion, so it is not read here at
    all: the identity is the row behind a verified token.

    Returns None for an anonymous request - and for a request whose token is
    expired or invalid, which proves nothing either. A caller that wants an
    account (a settings route, say) turns that into a 401; a caller that
    only wants a preference falls back to the deployment default, and a stale
    cookie must not turn a public route into an error.

    The address is also written to ``request.state.user_email``, which is
    where the audit middleware reads the actor from.
    """
    if user is None:
        return None

    request.state.user_email = user.email
    return user.email


async def get_auth_credentials(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
    session: AsyncSession = Depends(get_db),
) -> AuthCredentials:
    """
    Get full authentication credentials including token payload.

    Returns:
        AuthCredentials with user and token payload

    Raises:
        HTTPException: 401 if not authenticated
    """
    token = await _extract_token(request, access_token, credentials)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, payload = await _get_user_from_token(token, session)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return AuthCredentials(user, payload)


def require_role(required_role: str):
    """
    Dependency factory to require a specific role.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """

    async def role_checker(
        credentials: AuthCredentials = Depends(get_auth_credentials),
    ) -> AuthCredentials:
        user_roles = credentials.roles
        if required_role not in user_roles and "admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return credentials

    return role_checker


def require_roles(required_roles: list[str]):
    """
    Dependency factory to require any of the specified roles.

    Usage:
        @router.get("/staff-only", dependencies=[Depends(require_roles(["admin", "moderator"]))])
    """

    async def roles_checker(
        credentials: AuthCredentials = Depends(get_auth_credentials),
    ) -> AuthCredentials:
        user_roles = set(credentials.roles)
        required = set(required_roles)

        # Admin has access to everything
        if "admin" in user_roles:
            return credentials

        # Check if user has any of the required roles
        if not user_roles.intersection(required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {required_roles} required",
            )
        return credentials

    return roles_checker


def _is_admin_identity(user: User) -> bool:
    """Is this account an administrator of the deployment?

    Two answers count: the account carries the admin role in the database,
    or the deployment lists its e-mail in ADMIN_EMAILS. The second one is
    what lets a Google sign-in reach the admin panel without anyone
    editing the database by hand.
    """
    if (user.role or "").strip().lower() == "admin":
        return True
    admin_emails = {part.lower() for part in get_settings().admin_emails}
    return bool(admin_emails) and (user.email or "").strip().lower() in admin_emails


async def _has_admin_account(session: AsyncSession) -> bool:
    """Does the database hold an account with the admin role?"""
    result = await session.execute(
        select(func.count()).select_from(User).where(func.lower(User.role) == "admin")
    )
    return int(result.scalar() or 0) > 0


async def require_admin_access(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
    api_key: Optional[str] = Security(api_key_header_param),
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Gate the operator's own endpoints - the admin panel, the ingestion
    routes, the audit log.

    The admin API used to be reachable by anybody who knew the API key,
    and the key is injected by the frontend proxy for every path. On a
    deployment that runs in demo mode the key was not even checked. The
    gate is therefore an identity, not a key:

    - a signed-in account with the admin role, or an account whose e-mail
      is in ADMIN_EMAILS, is an administrator;
    - a signed-in account without that role is refused, and is not offered
      the key as a way in;
    - a request without any identity is refused as soon as the deployment
      HAS an administrator - one account with the admin role in the
      database, or one e-mail in ADMIN_EMAILS;
    - only a deployment that has no administrator at all keeps the old
      behaviour, where the API key is the way in. That is the self-hoster
      who has not created an admin account yet.

    The synthetic demo user is deliberately NOT consulted here: on a demo
    deployment it stands in for every anonymous visitor, and it carries the
    admin role.
    """
    settings = get_settings()

    token = await _extract_token(request, access_token, credentials)
    if token:
        try:
            user, _ = await _get_user_from_token(token, session)
        except HTTPException as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            ) from exc
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )
        if _is_admin_identity(user):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )

    if settings.demo_api_key_bypass:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )

    if settings.admin_emails or await _has_admin_account(session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )

    # No administrator exists on this deployment yet: the API key stays
    # the way in, so a self-hoster can still work with the admin panel.
    await get_api_key(request, api_key or "")
    return None


def require_permission(required_permission: Permission):
    """
    Dependency factory to require a specific permission.

    Usage:
        from api.rbac import Permission
        @router.delete("/data", dependencies=[Depends(require_permission(Permission.DATA_DELETE))])
    """

    async def permission_checker(
        credentials: AuthCredentials = Depends(get_auth_credentials),
    ) -> AuthCredentials:
        # Admin has all permissions
        if credentials.is_admin():
            return credentials

        if not credentials.has_permission(required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission.value}' required",
            )
        return credentials

    return permission_checker
