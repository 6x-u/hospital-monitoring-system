"""
Role-Based Access Control (RBAC) system.
Defines roles, permissions, and FastAPI dependency guards.
Developed by: MERO:TG@QP4RM
"""

from enum import Enum
from functools import wraps
from typing import Callable, Set

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user_payload


class UserRole(str, Enum):
    """System-defined user roles with hierarchical access levels."""
    ADMIN = "admin"           # Full system access
    ENGINEER = "engineer"     # Operational access (read + ack + recovery)
    VIEWER = "viewer"         # Read-only access


class Permission(str, Enum):
    """Granular permissions mapped to API operations."""
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # Device management
    DEVICE_READ = "device:read"
    DEVICE_WRITE = "device:write"
    DEVICE_DELETE = "device:delete"
    DEVICE_ISOLATE = "device:isolate"

    # Metrics
    METRICS_READ = "metrics:read"
    METRICS_WRITE = "metrics:write"

    # Alerts
    ALERT_READ = "alert:read"
    ALERT_WRITE = "alert:write"
    ALERT_ACKNOWLEDGE = "alert:acknowledge"
    ALERT_SUPPRESS = "alert:suppress"

    # Reports
    REPORT_READ = "report:read"
    REPORT_GENERATE = "report:generate"

    # System
    SYSTEM_CONFIG = "system:config"
    SYSTEM_BACKUP = "system:backup"
    AUDIT_LOG_READ = "audit:read"


# Role → permission set mapping
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: {
        # Admins have all permissions
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE,
        Permission.DEVICE_READ, Permission.DEVICE_WRITE, Permission.DEVICE_DELETE,
        Permission.DEVICE_ISOLATE,
        Permission.METRICS_READ, Permission.METRICS_WRITE,
        Permission.ALERT_READ, Permission.ALERT_WRITE,
        Permission.ALERT_ACKNOWLEDGE, Permission.ALERT_SUPPRESS,
        Permission.REPORT_READ, Permission.REPORT_GENERATE,
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_BACKUP,
        Permission.AUDIT_LOG_READ,
    },
    UserRole.ENGINEER: {
        # Engineers: operational + read access, no user management
        Permission.DEVICE_READ, Permission.DEVICE_WRITE, Permission.DEVICE_ISOLATE,
        Permission.METRICS_READ, Permission.METRICS_WRITE,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE, Permission.ALERT_SUPPRESS,
        Permission.REPORT_READ, Permission.REPORT_GENERATE,
        Permission.AUDIT_LOG_READ,
    },
    UserRole.VIEWER: {
        # Viewers: read-only access
        Permission.DEVICE_READ,
        Permission.METRICS_READ,
        Permission.ALERT_READ,
        Permission.REPORT_READ,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    """
    Check if a given role has a specific permission.

    Args:
        role: The role string (e.g., 'admin').
        permission: The permission to check.

    Returns:
        True if allowed, False otherwise.
    """
    try:
        user_role = UserRole(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(user_role, set())


def require_permission(permission: Permission) -> Callable:
    """
    FastAPI dependency factory: protects an endpoint by required permission.
    Raises 403 if the authenticated user's role lacks the permission.

    Usage:
        @router.get("/protected")
        async def endpoint(
            _: None = Depends(require_permission(Permission.DEVICE_READ))
        ):
            ...
    """
    async def permission_guard(
        payload: dict = Depends(get_current_user_payload),
    ) -> dict:
        role = payload.get("role", "")
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission.value}' required.",
            )
        return payload

    return permission_guard


def require_role(*roles: UserRole) -> Callable:
    """
    FastAPI dependency factory: restricts access to specific roles.

    Usage:
        @router.delete("/admin-only")
        async def endpoint(
            _: None = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    """
    async def role_guard(
        payload: dict = Depends(get_current_user_payload),
    ) -> dict:
        user_role = payload.get("role", "")
        if user_role not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges for this operation.",
            )
        return payload

    return role_guard
