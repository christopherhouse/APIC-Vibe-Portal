"""Role-based access control (RBAC) FastAPI dependencies.

Provides dependency factories that check the authenticated user's roles
before allowing access to a route.

Usage::

    from apic_vibe_portal_bff.middleware.rbac import require_role, require_any_role

    @router.get("/admin", dependencies=[Depends(require_role("Portal.Admin"))])
    async def admin_endpoint(): ...

    @router.get("/api", dependencies=[Depends(require_any_role(["Portal.User", "Portal.Maintainer"]))])
    async def api_endpoint(): ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser


def get_current_user(request: Request) -> AuthenticatedUser:
    """FastAPI dependency that extracts the authenticated user from request state.

    Raises 401 if the user has not been set by the auth middleware.
    """
    user: AuthenticatedUser | None = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


def require_role(role: str):
    """Return a FastAPI dependency that enforces a single required role.

    Raises 403 if the user does not have the specified role.
    """

    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:  # noqa: B008
        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is required",
            )
        return user

    return _dependency


def require_any_role(roles: list[str]):
    """Return a FastAPI dependency that enforces at least one of the listed roles.

    Raises 403 if the user does not have any of the specified roles.
    """

    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:  # noqa: B008
        if not any(r in user.roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {roles} is required",
            )
        return user

    return _dependency
