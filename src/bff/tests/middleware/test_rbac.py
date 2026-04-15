"""Tests for RBAC (role-based access control) dependencies."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser, AuthMiddleware
from apic_vibe_portal_bff.middleware.rbac import (
    require_any_role,
    require_role,
)


def _make_app_with_rbac() -> FastAPI:
    """Create a FastAPI app with auth middleware and RBAC-protected routes."""
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/role-user", dependencies=[Depends(require_role("Portal.User"))])
    async def role_user():
        return {"access": "user"}

    @app.get("/role-admin", dependencies=[Depends(require_role("Portal.Admin"))])
    async def role_admin():
        return {"access": "admin"}

    @app.get(
        "/any-role",
        dependencies=[Depends(require_any_role(["Portal.Admin", "Portal.Maintainer"]))],
    )
    async def any_role():
        return {"access": "any"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def _mock_validate(oid: str = "user-1", roles: list[str] | None = None):
    """Create a mock for validate_token returning a user with given roles."""
    user = AuthenticatedUser(
        oid=oid,
        name="Test User",
        email="test@example.com",
        roles=roles or [],
        claims={},
    )
    return user


@pytest.fixture
def app():
    return _make_app_with_rbac()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


class TestRequireRole:
    """Test the require_role dependency."""

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_user_with_correct_role_allowed(self, mock_validate, client):
        mock_validate.return_value = _mock_validate(roles=["Portal.User"])
        response = await client.get("/role-user", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200
        assert response.json()["access"] == "user"

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_user_without_role_forbidden(self, mock_validate, client):
        mock_validate.return_value = _mock_validate(roles=["Portal.User"])
        response = await client.get("/role-admin", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403
        assert "Portal.Admin" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_no_auth_header_unauthorized(self, client):
        response = await client.get("/role-user")
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_admin_role_allowed(self, mock_validate, client):
        mock_validate.return_value = _mock_validate(roles=["Portal.Admin"])
        response = await client.get("/role-admin", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200
        assert response.json()["access"] == "admin"


class TestRequireAnyRole:
    """Test the require_any_role dependency."""

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_user_with_one_of_roles_allowed(self, mock_validate, client):
        mock_validate.return_value = _mock_validate(roles=["Portal.Maintainer"])
        response = await client.get("/any-role", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_user_with_none_of_roles_forbidden(self, mock_validate, client):
        mock_validate.return_value = _mock_validate(roles=["Portal.User"])
        response = await client.get("/any-role", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 403

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_user_with_multiple_matching_roles(self, mock_validate, client):
        mock_validate.return_value = _mock_validate(roles=["Portal.Admin", "Portal.Maintainer"])
        response = await client.get("/any-role", headers={"Authorization": "Bearer tok"})
        assert response.status_code == 200


class TestGetCurrentUser:
    """Test the get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_no_user_returns_401(self, client):
        """When auth middleware is bypassed (public path + direct call), should 401."""
        response = await client.get("/role-user")
        assert response.status_code == 401
