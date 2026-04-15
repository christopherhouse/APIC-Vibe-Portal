"""Tests for RBAC (role-based access control) dependencies."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.middleware.rbac import get_current_user, require_any_role, require_role

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(**kwargs) -> AuthenticatedUser:
    """Create a test user."""
    defaults = {
        "oid": "user-123",
        "name": "Test User",
        "email": "test@example.com",
        "roles": ["Portal.User"],
        "raw_claims": {},
    }
    defaults.update(kwargs)
    return AuthenticatedUser(**defaults)


def _make_app_with_rbac(user: AuthenticatedUser | None = None) -> FastAPI:
    """Build a FastAPI app that injects a mock user into request state via middleware."""
    app = FastAPI()

    # Simple middleware to inject user into request state (simulates AuthMiddleware)
    from starlette.middleware.base import BaseHTTPMiddleware

    class _InjectUserMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if user is not None:
                request.state.user = user
            return await call_next(request)

    app.add_middleware(_InjectUserMiddleware)

    @app.get("/public")
    async def public_endpoint():
        return {"message": "public"}

    @app.get("/user-only", dependencies=[Depends(require_role("Portal.User"))])
    async def user_endpoint():
        return {"message": "user"}

    @app.get("/admin-only", dependencies=[Depends(require_role("Portal.Admin"))])
    async def admin_endpoint():
        return {"message": "admin"}

    @app.get("/multi-role", dependencies=[Depends(require_any_role(["Portal.Admin", "API.Owner"]))])
    async def multi_role_endpoint():
        return {"message": "multi"}

    @app.get("/current-user")
    async def current_user_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
        return {"oid": user.oid, "name": user.name}

    return app


async def _client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# get_current_user tests
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    """Tests for the get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_when_present(self) -> None:
        """Should return user from request state."""
        user = _make_user()
        app = _make_app_with_rbac(user=user)
        async with await _client(app) as c:
            response = await c.get("/current-user")
            assert response.status_code == 200
            data = response.json()
            assert data["oid"] == "user-123"
            assert data["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_returns_401_when_no_user(self) -> None:
        """Should return 401 when no user in request state."""
        app = _make_app_with_rbac(user=None)
        async with await _client(app) as c:
            response = await c.get("/current-user")
            assert response.status_code == 401


# ---------------------------------------------------------------------------
# require_role tests
# ---------------------------------------------------------------------------

class TestRequireRole:
    """Tests for the require_role dependency factory."""

    @pytest.mark.asyncio
    async def test_allows_user_with_required_role(self) -> None:
        """User with the required role should get 200."""
        user = _make_user(roles=["Portal.User"])
        app = _make_app_with_rbac(user=user)
        async with await _client(app) as c:
            response = await c.get("/user-only")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rejects_user_without_required_role(self) -> None:
        """User without the required role should get 403."""
        user = _make_user(roles=["Portal.User"])
        app = _make_app_with_rbac(user=user)
        async with await _client(app) as c:
            response = await c.get("/admin-only")
            assert response.status_code == 403
            assert "Portal.Admin" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_can_access_admin_routes(self) -> None:
        """Admin user should access admin-only routes."""
        user = _make_user(roles=["Portal.User", "Portal.Admin"])
        app = _make_app_with_rbac(user=user)
        async with await _client(app) as c:
            response = await c.get("/admin-only")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self) -> None:
        """No user at all should get 401 (not 403)."""
        app = _make_app_with_rbac(user=None)
        async with await _client(app) as c:
            response = await c.get("/user-only")
            assert response.status_code == 401


# ---------------------------------------------------------------------------
# require_any_role tests
# ---------------------------------------------------------------------------

class TestRequireAnyRole:
    """Tests for the require_any_role dependency factory."""

    @pytest.mark.asyncio
    async def test_allows_user_with_one_matching_role(self) -> None:
        """User with at least one matching role should get 200."""
        user = _make_user(roles=["API.Owner"])
        app = _make_app_with_rbac(user=user)
        async with await _client(app) as c:
            response = await c.get("/multi-role")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_user_with_other_matching_role(self) -> None:
        """User with Portal.Admin should also get 200."""
        user = _make_user(roles=["Portal.Admin"])
        app = _make_app_with_rbac(user=user)
        async with await _client(app) as c:
            response = await c.get("/multi-role")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rejects_user_with_no_matching_roles(self) -> None:
        """User with none of the required roles should get 403."""
        user = _make_user(roles=["Portal.User"])
        app = _make_app_with_rbac(user=user)
        async with await _client(app) as c:
            response = await c.get("/multi-role")
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self) -> None:
        """No user at all should get 401."""
        app = _make_app_with_rbac(user=None)
        async with await _client(app) as c:
            response = await c.get("/multi-role")
            assert response.status_code == 401
