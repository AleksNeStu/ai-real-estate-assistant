"""Authentication dependencies for FastAPI."""

from typing import Optional, Set

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

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
    is_demo_env = settings.demo_mode

    # Use demo user if demo mode is active
    if is_demo_session or is_demo_env:
        return _get_demo_user()

    # Normal authentication flow
    token = await _extract_token(request, access_token, credentials)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, _ = await _get_user_from_token(token, session)

    # Set Sentry user context for error tracking
    try:
        from api.sentry_init import set_user_context

        set_user_context(user_id=str(user.id), email=user.email)
    except ImportError:
        pass  # Sentry not available

    return user


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
