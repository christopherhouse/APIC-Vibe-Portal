"""Tests for custom middleware (error handler, request logger, auth)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser, AuthMiddleware
from apic_vibe_portal_bff.middleware.error_handler import ErrorHandlerMiddleware
from apic_vibe_portal_bff.middleware.request_logger import RequestLoggerMiddleware

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_USER = AuthenticatedUser(
    oid="test-user",
    name="Test User",
    email="test@example.com",
    roles=["Portal.User"],
    claims={},
)


def _make_app(*, debug: bool = False) -> FastAPI:
    """Build a minimal FastAPI app with our middleware stack."""
    app = FastAPI()

    @app.get("/ok")
    async def ok_endpoint():
        return {"status": "ok"}

    @app.get("/error")
    async def error_endpoint():
        msg = "Something went wrong"
        raise RuntimeError(msg)

    app.add_middleware(ErrorHandlerMiddleware, debug=debug)
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(AuthMiddleware)
    return app


async def _client(app: FastAPI):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


_AUTH_HEADERS = {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# Error handler middleware
# ---------------------------------------------------------------------------


class TestErrorHandlerMiddleware:
    """Test the global error handler."""

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_normal_request_passes_through(self, _mock) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok", headers=_AUTH_HEADERS)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_unhandled_error_returns_500(self, _mock) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/error", headers=_AUTH_HEADERS)
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal Server Error"

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_production_mode_hides_traceback(self, _mock) -> None:
        app = _make_app(debug=False)
        async with await _client(app) as c:
            response = await c.get("/error", headers=_AUTH_HEADERS)
        data = response.json()
        # detail should be a generic message, not the exception text
        assert isinstance(data["detail"], str)
        assert data["detail"] == "An unexpected error occurred."
        assert "Something went wrong" not in data["detail"]

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_production_mode_includes_request_id(self, _mock) -> None:
        app = _make_app(debug=False)
        async with await _client(app) as c:
            response = await c.get("/error", headers={**_AUTH_HEADERS, "X-Request-ID": "err-456"})
        data = response.json()
        assert data["request_id"] == "err-456"
        assert response.headers["x-request-id"] == "err-456"

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_debug_mode_includes_traceback(self, _mock) -> None:
        app = _make_app(debug=True)
        async with await _client(app) as c:
            response = await c.get("/error", headers=_AUTH_HEADERS)
        data = response.json()
        assert isinstance(data["detail"], dict)
        assert "traceback" in data["detail"]
        assert "RuntimeError" in data["detail"]["traceback"]


# ---------------------------------------------------------------------------
# Request logger middleware
# ---------------------------------------------------------------------------


class TestRequestLoggerMiddleware:
    """Test the request logging middleware."""

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_adds_request_id_header(self, _mock) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok", headers=_AUTH_HEADERS)
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_echoes_provided_request_id(self, _mock) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok", headers={**_AUTH_HEADERS, "X-Request-ID": "test-123"})
        assert response.headers["x-request-id"] == "test-123"

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_generates_request_id_when_missing(self, _mock) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok", headers=_AUTH_HEADERS)
        request_id = response.headers["x-request-id"]
        # Should be a UUID-like string
        assert len(request_id) > 0
        assert "-" in request_id


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    """Test the auth middleware blocks unauthenticated requests."""

    @pytest.mark.asyncio
    async def test_rejects_unauthenticated_requests(self) -> None:
        """Auth middleware should reject requests without a Bearer token."""
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok")
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
    async def test_passes_authenticated_requests(self, _mock) -> None:
        """Auth middleware should pass requests with a valid token."""
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok", headers=_AUTH_HEADERS)
        assert response.status_code == 200
