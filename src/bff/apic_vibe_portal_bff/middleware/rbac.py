"""Role-based access control (RBAC) dependencies for FastAPI.

Provides dependency factories that check the authenticated user's roles
before allowing access to a route. Designed to be used with
:class:`~apic_vibe_portal_bff.middleware.auth.AuthMiddleware`, which
populates ``request.state.user``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request

from apic_vibe_portal_bff.utils.logger import get_logger

if TYPE_CHECKING:
    from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser

logger = get_logger(__name__)


def get_current_user(request: Request) -> AuthenticatedUser:
    """Extract the current authenticated user from request state.

    This is a FastAPI dependency that retrieves the user set by
    :class:`~apic_vibe_portal_bff.middleware.auth.AuthMiddleware`.

    Raises
    ------
    HTTPException(401)
        If no user is attached to the request (middleware not configured
        or request is unauthenticated).
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_role(role: str):
    """FastAPI dependency factory: require the user to have a specific role.

    Usage::

        @router.get("/admin", dependencies=[Depends(require_role("Portal.Admin"))])
        async def admin_endpoint(): ...

    Parameters
    ----------
    role:
        The role name the user must have (e.g., ``Portal.Admin``).
    """

    def _check_role(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if role not in user.roles:
            logger.warning("rbac.insufficient_role", required=role, user_roles=user.roles, user_oid=user.oid)
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {role}",
            )
        return user

    return _check_role


def require_any_role(roles: list[str]):
    """FastAPI dependency factory: require the user to have at least one of the given roles.

    Usage::

        @router.get("/manage", dependencies=[Depends(require_any_role(["Portal.Admin", "API.Owner"]))])
        async def manage_endpoint(): ...

    Parameters
    ----------
    roles:
        List of acceptable role names. The user must have at least one.
    """

    def _check_any_role(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not any(r in user.roles for r in roles):
            logger.warning("rbac.insufficient_roles", required=roles, user_roles=user.roles, user_oid=user.oid)
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required one of: {', '.join(roles)}",
            )
        return user

    return _check_any_role
