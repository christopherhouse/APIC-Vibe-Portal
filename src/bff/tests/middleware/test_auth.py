"""Tests for JWT authentication middleware."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from apic_vibe_portal_bff.middleware.auth import (
    _PUBLIC_PATHS,
    AuthenticatedUser,
    AuthMiddleware,
    reset_jwks_client,
    validate_token,
)

# --- Helpers ---


def _make_app() -> Starlette:
    """Create a Starlette app with AuthMiddleware for testing."""

    async def protected(request: Request) -> JSONResponse:
        user: AuthenticatedUser | None = getattr(request.state, "user", None)
        if user:
            return JSONResponse({"oid": user.oid, "name": user.name, "roles": user.roles})
        return JSONResponse({"user": None})

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "healthy"})

    app = Starlette(
        routes=[
            Route("/api/test", protected),
            Route("/health", health),
        ],
    )
    app.add_middleware(AuthMiddleware)
    return app


_RSA_PRIVATE_KEY = None
_RSA_PUBLIC_KEY = None


def _get_rsa_keys():
    """Generate an RSA key pair for test JWT signing."""
    global _RSA_PRIVATE_KEY, _RSA_PUBLIC_KEY
    if _RSA_PRIVATE_KEY is None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        _RSA_PRIVATE_KEY = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        _RSA_PUBLIC_KEY = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    return _RSA_PRIVATE_KEY, _RSA_PUBLIC_KEY


def _make_token(
    claims: dict | None = None,
    expired: bool = False,
    wrong_audience: bool = False,
) -> str:
    """Create a test JWT signed with the test RSA key."""
    private_key, _ = _get_rsa_keys()
    now = int(time.time())
    payload = {
        "oid": "user-123",
        "name": "Test User",
        "preferred_username": "test@example.com",
        "roles": ["Portal.User"],
        "aud": "wrong-audience" if wrong_audience else "test-client-id",
        "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
        "iat": now - 60,
        "nbf": now - 60,
        "exp": now - 10 if expired else now + 3600,
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-kid"})


@pytest.fixture(autouse=True)
def _reset_jwks():
    """Reset the JWKS client cache before each test."""
    reset_jwks_client()
    yield
    reset_jwks_client()


# --- AuthMiddleware Integration Tests ---


class TestAuthMiddleware:
    """Test the AuthMiddleware integration."""

    def test_public_path_no_auth_required(self):
        """Health-check paths should pass through without auth."""
        app = _make_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_missing_authorization_header(self):
        """Requests without Authorization header should get 401."""
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/test")
        assert response.status_code == 401
        assert "Missing" in response.json()["detail"]

    def test_invalid_authorization_scheme(self):
        """Requests with non-Bearer scheme should get 401."""
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/test", headers={"Authorization": "Basic abc123"})
        assert response.status_code == 401

    def test_invalid_token(self):
        """Requests with invalid JWT should get 401."""
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/test", headers={"Authorization": "Bearer not-a-valid-jwt"})
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    def test_valid_token_sets_user(self, mock_validate):
        """A valid token should populate request.state.user."""
        mock_validate.return_value = AuthenticatedUser(
            oid="user-123",
            name="Test User",
            email="test@example.com",
            roles=["Portal.User"],
            claims={},
        )
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/test", headers={"Authorization": "Bearer valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["oid"] == "user-123"
        assert data["name"] == "Test User"
        assert "Portal.User" in data["roles"]

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    def test_expired_token(self, mock_validate):
        """Expired tokens should return 401."""
        mock_validate.side_effect = jwt.ExpiredSignatureError("Token expired")
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/test", headers={"Authorization": "Bearer expired-token"})
        assert response.status_code == 401
        assert "expired" in response.json()["detail"]

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    def test_wrong_audience(self, mock_validate):
        """Tokens with wrong audience should return 401."""
        mock_validate.side_effect = jwt.InvalidAudienceError("Wrong audience")
        app = _make_app()
        client = TestClient(app)
        response = client.get("/api/test", headers={"Authorization": "Bearer wrong-aud"})
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]


# --- validate_token Unit Tests ---


class TestValidateToken:
    """Test the validate_token function directly."""

    @patch("apic_vibe_portal_bff.middleware.auth.get_settings")
    def test_missing_config_raises(self, mock_settings):
        """Should raise when Entra ID is not configured."""
        settings = MagicMock()
        settings.entra_tenant_id = ""
        settings.entra_client_id = ""
        settings.entra_audience = ""
        mock_settings.return_value = settings

        with pytest.raises(jwt.InvalidTokenError, match="not configured"):
            validate_token("any-token")

    @patch("apic_vibe_portal_bff.middleware.auth._get_jwks_client")
    @patch("apic_vibe_portal_bff.middleware.auth.get_settings")
    def test_valid_token_decodes_correctly(self, mock_settings, mock_jwks):
        """A properly signed token should decode to an AuthenticatedUser."""
        _, public_key = _get_rsa_keys()

        settings = MagicMock()
        settings.entra_tenant_id = "test-tenant-id"
        settings.entra_client_id = "test-client-id"
        settings.entra_audience = "test-client-id"
        mock_settings.return_value = settings

        signing_key = MagicMock()
        signing_key.key = public_key
        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = signing_key
        mock_jwks.return_value = mock_jwks_client

        token = _make_token()
        user = validate_token(token)

        assert user.oid == "user-123"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert "Portal.User" in user.roles

    @patch("apic_vibe_portal_bff.middleware.auth._get_jwks_client")
    @patch("apic_vibe_portal_bff.middleware.auth.get_settings")
    def test_expired_token_raises(self, mock_settings, mock_jwks):
        """Expired token should raise ExpiredSignatureError."""
        _, public_key = _get_rsa_keys()

        settings = MagicMock()
        settings.entra_tenant_id = "test-tenant-id"
        settings.entra_client_id = "test-client-id"
        settings.entra_audience = "test-client-id"
        mock_settings.return_value = settings

        signing_key = MagicMock()
        signing_key.key = public_key
        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = signing_key
        mock_jwks.return_value = mock_jwks_client

        token = _make_token(expired=True)
        with pytest.raises(jwt.ExpiredSignatureError):
            validate_token(token)

    @patch("apic_vibe_portal_bff.middleware.auth._get_jwks_client")
    @patch("apic_vibe_portal_bff.middleware.auth.get_settings")
    def test_wrong_audience_raises(self, mock_settings, mock_jwks):
        """Token with wrong audience should raise InvalidAudienceError."""
        _, public_key = _get_rsa_keys()

        settings = MagicMock()
        settings.entra_tenant_id = "test-tenant-id"
        settings.entra_client_id = "test-client-id"
        settings.entra_audience = "test-client-id"
        mock_settings.return_value = settings

        signing_key = MagicMock()
        signing_key.key = public_key
        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = signing_key
        mock_jwks.return_value = mock_jwks_client

        token = _make_token(wrong_audience=True)
        with pytest.raises(jwt.InvalidAudienceError):
            validate_token(token)


class TestPublicPaths:
    """Test that public paths are correctly defined."""

    def test_health_is_public(self):
        assert "/health" in _PUBLIC_PATHS

    def test_health_ready_is_public(self):
        assert "/health/ready" in _PUBLIC_PATHS

    def test_docs_is_public(self):
        assert "/docs" in _PUBLIC_PATHS

    def test_openapi_is_public(self):
        assert "/openapi.json" in _PUBLIC_PATHS
