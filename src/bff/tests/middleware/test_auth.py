"""Tests for JWT authentication middleware."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from apic_vibe_portal_bff.middleware.auth import (
    EXEMPT_PATHS,
    AuthenticatedUser,
    AuthMiddleware,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(*, entra_tenant_id: str = "test-tenant", entra_client_id: str = "test-client",
              entra_audience: str = "api://test-client") -> FastAPI:
    """Build a minimal FastAPI app with the auth middleware."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/health/ready")
    async def health_ready():
        return {"status": "ready"}

    @app.get("/api/test")
    async def test_endpoint(request: Request):
        user = getattr(request.state, "user", None)
        if user:
            return {"oid": user.oid, "name": user.name, "roles": user.roles}
        return {"user": None}

    app.add_middleware(AuthMiddleware)

    return app


async def _client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def _mock_settings(tenant_id: str = "test-tenant", client_id: str = "test-client",
                   audience: str = "api://test-client"):
    """Create a mock settings object."""
    settings = MagicMock()
    settings.entra_tenant_id = tenant_id
    settings.entra_client_id = client_id
    settings.entra_audience = audience
    return settings


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


# ---------------------------------------------------------------------------
# AuthMiddleware tests
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    """Tests for the AuthMiddleware."""

    @pytest.mark.asyncio
    async def test_exempt_paths_pass_through(self) -> None:
        """Health and doc paths should not require auth."""
        app = _make_app()
        with patch("apic_vibe_portal_bff.middleware.auth.get_settings", return_value=_mock_settings()):
            async with await _client(app) as c:
                for path in ["/health", "/health/ready"]:
                    response = await c.get(path)
                    assert response.status_code == 200, f"Expected 200 for {path}"

    @pytest.mark.asyncio
    async def test_no_auth_header_returns_401(self) -> None:
        """Requests without Authorization header should get 401."""
        app = _make_app()
        with patch("apic_vibe_portal_bff.middleware.auth.get_settings", return_value=_mock_settings()):
            async with await _client(app) as c:
                response = await c.get("/api/test")
                assert response.status_code == 401
                data = response.json()
                assert data["error"] == "Unauthorized"

    @pytest.mark.asyncio
    async def test_invalid_auth_header_format_returns_401(self) -> None:
        """Requests with non-Bearer auth header should get 401."""
        app = _make_app()
        with patch("apic_vibe_portal_bff.middleware.auth.get_settings", return_value=_mock_settings()):
            async with await _client(app) as c:
                response = await c.get("/api/test", headers={"Authorization": "Basic abc123"})
                assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_sets_user(self) -> None:
        """A valid token should result in request.state.user being set."""
        app = _make_app()
        mock_user = _make_user()

        with (
            patch("apic_vibe_portal_bff.middleware.auth.get_settings", return_value=_mock_settings()),
            patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=mock_user),
        ):
            async with await _client(app) as c:
                response = await c.get("/api/test", headers={"Authorization": "Bearer valid-token"})
                assert response.status_code == 200
                data = response.json()
                assert data["oid"] == "user-123"
                assert data["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self) -> None:
        """Expired tokens should return 401."""
        app = _make_app()

        with (
            patch("apic_vibe_portal_bff.middleware.auth.get_settings", return_value=_mock_settings()),
            patch(
                "apic_vibe_portal_bff.middleware.auth.validate_token",
                side_effect=pyjwt.ExpiredSignatureError("Token expired"),
            ),
        ):
            async with await _client(app) as c:
                response = await c.get("/api/test", headers={"Authorization": "Bearer expired-token"})
                assert response.status_code == 401
                assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_wrong_audience_returns_401(self) -> None:
        """Token with wrong audience should return 401."""
        app = _make_app()

        with (
            patch("apic_vibe_portal_bff.middleware.auth.get_settings", return_value=_mock_settings()),
            patch(
                "apic_vibe_portal_bff.middleware.auth.validate_token",
                side_effect=pyjwt.InvalidAudienceError("Wrong audience"),
            ),
        ):
            async with await _client(app) as c:
                response = await c.get("/api/test", headers={"Authorization": "Bearer wrong-aud-token"})
                assert response.status_code == 401
                assert "audience" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_wrong_issuer_returns_401(self) -> None:
        """Token with wrong issuer should return 401."""
        app = _make_app()

        with (
            patch("apic_vibe_portal_bff.middleware.auth.get_settings", return_value=_mock_settings()),
            patch(
                "apic_vibe_portal_bff.middleware.auth.validate_token",
                side_effect=pyjwt.InvalidIssuerError("Wrong issuer"),
            ),
        ):
            async with await _client(app) as c:
                response = await c.get("/api/test", headers={"Authorization": "Bearer wrong-iss-token"})
                assert response.status_code == 401
                assert "issuer" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generic_invalid_token_returns_401(self) -> None:
        """Any other token error should return 401."""
        app = _make_app()

        with (
            patch("apic_vibe_portal_bff.middleware.auth.get_settings", return_value=_mock_settings()),
            patch(
                "apic_vibe_portal_bff.middleware.auth.validate_token",
                side_effect=pyjwt.InvalidTokenError("Bad token"),
            ),
        ):
            async with await _client(app) as c:
                response = await c.get("/api/test", headers={"Authorization": "Bearer bad-token"})
                assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unconfigured_tenant_passes_through(self) -> None:
        """When entra_tenant_id is empty, middleware should pass through."""
        app = _make_app()

        with patch(
            "apic_vibe_portal_bff.middleware.auth.get_settings",
            return_value=_mock_settings(tenant_id=""),
        ):
            async with await _client(app) as c:
                response = await c.get("/api/test")
                assert response.status_code == 200


# ---------------------------------------------------------------------------
# AuthenticatedUser tests
# ---------------------------------------------------------------------------

class TestAuthenticatedUser:
    """Tests for the AuthenticatedUser dataclass."""

    def test_default_values(self) -> None:
        """User should have sensible defaults."""
        user = AuthenticatedUser(oid="abc")
        assert user.oid == "abc"
        assert user.name == ""
        assert user.email == ""
        assert user.roles == []
        assert user.raw_claims == {}

    def test_full_user(self) -> None:
        """User should store all provided values."""
        user = AuthenticatedUser(
            oid="abc",
            name="Alice",
            email="alice@example.com",
            roles=["Portal.User", "Portal.Admin"],
            raw_claims={"sub": "abc"},
        )
        assert user.name == "Alice"
        assert "Portal.Admin" in user.roles


# ---------------------------------------------------------------------------
# EXEMPT_PATHS tests
# ---------------------------------------------------------------------------

class TestExemptPaths:
    """Tests for the exempt paths set."""

    def test_health_paths_exempt(self) -> None:
        assert "/health" in EXEMPT_PATHS
        assert "/health/ready" in EXEMPT_PATHS

    def test_docs_paths_exempt(self) -> None:
        assert "/docs" in EXEMPT_PATHS
        assert "/redoc" in EXEMPT_PATHS
        assert "/openapi.json" in EXEMPT_PATHS
