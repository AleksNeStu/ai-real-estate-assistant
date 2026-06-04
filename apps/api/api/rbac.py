"""
Role-Based Access Control (RBAC) Middleware (TASK-018).

This module provides role-based authorization for API endpoints:
- Define roles and permissions
- Decorator-based authorization checks
- Admin-only endpoint protection
- Resource-level permissions

Roles:
- admin: Full system access, can manage users and configuration
- user: Standard user access to features
- read_only: Read-only access to data
- api_client: API client with limited access

Permissions are granted to roles and checked at endpoint level.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Set

from fastapi import HTTPException, Request, status

from api.audit import AuditEventType, AuditLevel, get_audit_logger


class Role(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    USER = "user"
    READ_ONLY = "read_only"
    API_CLIENT = "api_client"


class Permission(str, Enum):
    """Granular permissions."""

    # Admin permissions
    ADMIN_MANAGE_USERS = "admin.manage_users"
    ADMIN_MANAGE_CONFIG = "admin.manage_config"
    ADMIN_VIEW_LOGS = "admin.view_logs"
    ADMIN_SYSTEM_CONTROL = "admin.system_control"

    # Data permissions
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"

    # Feature permissions
    FEATURE_SEARCH = "feature.search"
    FEATURE_CHAT = "feature.chat"
    FEATURE_RAG = "feature.rag"
    FEATURE_TOOLS = "feature.tools"

    # Notification permissions
    NOTIFICATION_SEND = "notification.send"
    NOTIFICATION_MANAGE = "notification.manage"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # Admin has all permissions
        Permission.ADMIN_MANAGE_USERS,
        Permission.ADMIN_MANAGE_CONFIG,
        Permission.ADMIN_VIEW_LOGS,
        Permission.ADMIN_SYSTEM_CONTROL,
        Permission.DATA_READ,
        Permission.DATA_WRITE,
        Permission.DATA_DELETE,
        Permission.DATA_EXPORT,
        Permission.FEATURE_SEARCH,
        Permission.FEATURE_CHAT,
        Permission.FEATURE_RAG,
        Permission.FEATURE_TOOLS,
        Permission.NOTIFICATION_SEND,
        Permission.NOTIFICATION_MANAGE,
    },
    Role.USER: {
        # Standard user permissions
        Permission.DATA_READ,
        Permission.DATA_WRITE,
        Permission.DATA_EXPORT,
        Permission.FEATURE_SEARCH,
        Permission.FEATURE_CHAT,
        Permission.FEATURE_RAG,
        Permission.FEATURE_TOOLS,
        Permission.NOTIFICATION_SEND,
    },
    Role.READ_ONLY: {
        # Read-only permissions
        Permission.DATA_READ,
        Permission.FEATURE_SEARCH,
    },
    Role.API_CLIENT: {
        # API client permissions (limited)
        Permission.DATA_READ,
        Permission.FEATURE_SEARCH,
        Permission.FEATURE_CHAT,
    },
}


@dataclass
class UserContext:
    """User context for authorization decisions."""

    client_id: str  # Hashed API key identifier
    roles: Set[Role]
    permissions: Set[Permission]
    request_id: Optional[str] = None


class RBACChecker:
    """
    Role-Based Access Control checker.

    Checks if a user has the required roles or permissions
    to access a resource or perform an action.
    """

    def __init__(
        self,
        admin_api_keys: Optional[set[str]] = None,
        user_api_keys: Optional[set[str]] = None,
        read_only_api_keys: Optional[set[str]] = None,
    ) -> None:
        """
        Initialize RBAC checker.

        Args:
            admin_api_keys: Set of API keys with admin role
            user_api_keys: Set of API keys with user role
            read_only_api_keys: Set of API keys with read-only role
        """
        from config.settings import get_settings

        settings = get_settings()

        # Get API keys from settings or params
        all_keys = getattr(settings, "api_access_keys", [])
        self._admin_keys = admin_api_keys or set()
        self._user_keys = user_api_keys or set()
        self._read_only_keys = read_only_api_keys or set()

        # If no explicit keys provided, determine roles from key patterns
        # Admin keys: contain "admin" in the key identifier
        # Read-only keys: contain "readonly" or "read_only" in the key identifier
        # User keys: all other keys
        if not admin_api_keys and not user_api_keys and not read_only_api_keys:
            for key in all_keys:
                key_lower = key.lower()
                if "admin" in key_lower:
                    self._admin_keys.add(key)
                elif "readonly" in key_lower or "read_only" in key_lower:
                    self._read_only_keys.add(key)
                else:
                    self._user_keys.add(key)

        self._logger = logging.getLogger(__name__)
        self._audit_logger = get_audit_logger()

    def _get_roles_for_key(self, api_key: str) -> Set[Role]:
        """Get roles for an API key."""
        roles = set()
        if api_key in self._admin_keys:
            roles.add(Role.ADMIN)
        if api_key in self._user_keys:
            roles.add(Role.USER)
        if api_key in self._read_only_keys:
            roles.add(Role.READ_ONLY)

        # Default to API_CLIENT if no specific role found
        if not roles:
            roles.add(Role.API_CLIENT)

        return roles

    def _get_permissions_for_roles(self, roles: Set[Role]) -> Set[Permission]:
        """Get all permissions for a set of roles."""
        permissions = set()
        for role in roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        return permissions

    def get_user_context(
        self,
        api_key: str,
        request_id: Optional[str] = None,
    ) -> UserContext:
        """
        Get user context for authorization decisions.

        Args:
            api_key: The API key
            request_id: Request correlation ID

        Returns:
            UserContext with roles and permissions
        """
        roles = self._get_roles_for_key(api_key)
        permissions = self._get_permissions_for_roles(roles)

        # Hash the API key for logging (HMAC-based fingerprint, not a password hash)
        from core.security_utils import hash_fingerprint

        client_id = hash_fingerprint(api_key, length=16)

        return UserContext(
            client_id=client_id,
            roles=roles,
            permissions=permissions,
            request_id=request_id,
        )

    def check_role(self, user_context: UserContext, required_role: Role) -> bool:
        """
        Check if user has the required role.

        Args:
            user_context: User context
            required_role: Required role

        Returns:
            True if user has the role
        """
        has_role = required_role in user_context.roles

        if not has_role:
            self._audit_logger.log_security_event(
                event_type=AuditEventType.AUTHZ_DENIED,
                level=AuditLevel.HIGH,
                resource=f"role:{required_role}",
                client_id=user_context.client_id,
                result="denied",
                request_id=user_context.request_id,
                metadata={"required_role": required_role, "user_roles": list(user_context.roles)},
            )

        return has_role

    def check_permission(self, user_context: UserContext, required_permission: Permission) -> bool:
        """
        Check if user has the required permission.

        Args:
            user_context: User context
            required_permission: Required permission

        Returns:
            True if user has the permission
        """
        has_permission = required_permission in user_context.permissions

        if not has_permission:
            self._audit_logger.log_security_event(
                event_type=AuditEventType.AUTHZ_DENIED,
                level=AuditLevel.HIGH,
                resource=f"permission:{required_permission}",
                client_id=user_context.client_id,
                result="denied",
                request_id=user_context.request_id,
                metadata={
                    "required_permission": required_permission,
                    "user_permissions": list(user_context.permissions),
                },
            )

        return has_permission

    def check_any_role(self, user_context: UserContext, required_roles: Set[Role]) -> bool:
        """
        Check if user has any of the required roles.

        Args:
            user_context: User context
            required_roles: Set of acceptable roles

        Returns:
            True if user has at least one of the roles
        """
        return any(role in user_context.roles for role in required_roles)

    def check_all_roles(self, user_context: UserContext, required_roles: Set[Role]) -> bool:
        """
        Check if user has all of the required roles.

        Args:
            user_context: User context
            required_roles: Set of required roles

        Returns:
            True if user has all the roles
        """
        return all(role in user_context.roles for role in required_roles)


# Global RBAC checker instance
_rbac_checker: Optional[RBACChecker] = None


def get_rbac_checker() -> RBACChecker:
    """Get global RBAC checker instance."""
    global _rbac_checker
    if _rbac_checker is None:
        _rbac_checker = RBACChecker()
    return _rbac_checker


def require_role(required_role: Role):
    """
    Decorator to require a specific role for endpoint access.

    Usage:
        @require_role(Role.ADMIN)
        async def admin_endpoint(request: Request):
            ...

    Args:
        required_role: Required role for access
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get API key from request state (set by auth middleware)
            api_key = getattr(request.state, "api_key", None)
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            checker = get_rbac_checker()
            request_id = getattr(request.state, "request_id", None)
            user_context = checker.get_user_context(api_key, request_id)

            if not checker.check_role(user_context, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{required_role}' required",
                )

            # Store user context in request state for use in endpoint
            request.state.user_context = user_context

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_permission(required_permission: Permission):
    """
    Decorator to require a specific permission for endpoint access.

    Usage:
        @require_permission(Permission.DATA_DELETE)
        async def delete_data(request: Request):
            ...

    Args:
        required_permission: Required permission for access
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get API key from request state
            api_key = getattr(request.state, "api_key", None)
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            checker = get_rbac_checker()
            request_id = getattr(request.state, "request_id", None)
            user_context = checker.get_user_context(api_key, request_id)

            if not checker.check_permission(user_context, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{required_permission}' required",
                )

            # Store user context in request state
            request.state.user_context = user_context

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_admin():
    """
    Decorator to require admin role.

    Convenience decorator for @require_role(Role.ADMIN).

    Usage:
        @require_admin()
        async def admin_only_endpoint(request: Request):
            ...
    """

    def decorator(func: Callable):
        return require_role(Role.ADMIN)(func)

    return decorator
