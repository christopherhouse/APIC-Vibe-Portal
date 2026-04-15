"""Tests for custom middleware (error handler, request logger, auth)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.middleware.auth import AuthMiddleware
from apic_vibe_portal_bff.middleware.error_handler import ErrorHandlerMiddleware
from apic_vibe_portal_bff.middleware.request_logger import RequestLoggerMiddleware

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(*, debug: bool = False, raise_error: bool = False) -> FastAPI:
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


# ---------------------------------------------------------------------------
# Error handler middleware
# ---------------------------------------------------------------------------

class TestErrorHandlerMiddleware:
    """Test the global error handler."""

    @pytest.mark.asyncio
    async def test_normal_request_passes_through(self) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_unhandled_error_returns_500(self) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/error")
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal Server Error"

    @pytest.mark.asyncio
    async def test_production_mode_hides_traceback(self) -> None:
        app = _make_app(debug=False)
        async with await _client(app) as c:
            response = await c.get("/error")
        data = response.json()
        # detail should be a plain string, not a dict with traceback
        assert isinstance(data["detail"], str)
        assert "traceback" not in str(data["detail"]).lower() or "Traceback" not in str(data["detail"])

    @pytest.mark.asyncio
    async def test_debug_mode_includes_traceback(self) -> None:
        app = _make_app(debug=True)
        async with await _client(app) as c:
            response = await c.get("/error")
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
    async def test_adds_request_id_header(self) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok")
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_echoes_provided_request_id(self) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok", headers={"X-Request-ID": "test-123"})
        assert response.headers["x-request-id"] == "test-123"

    @pytest.mark.asyncio
    async def test_generates_request_id_when_missing(self) -> None:
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok")
        request_id = response.headers["x-request-id"]
        # Should be a UUID-like string
        assert len(request_id) > 0
        assert "-" in request_id


# ---------------------------------------------------------------------------
# Auth middleware (placeholder)
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    """Test the auth middleware placeholder."""

    @pytest.mark.asyncio
    async def test_passes_through(self) -> None:
        """Auth middleware should pass all requests through for now."""
        app = _make_app()
        async with await _client(app) as c:
            response = await c.get("/ok")
        assert response.status_code == 200
