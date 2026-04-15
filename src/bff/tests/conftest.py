"""Shared pytest fixtures for the BFF test suite."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.app import create_app


@pytest.fixture
def app():
    """Return a fresh FastAPI application instance."""
    return create_app()


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient]:
    """Yield an async ``httpx`` client bound to the test application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
