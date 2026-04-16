"""Tests for health check endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser

_MOCK_USER = AuthenticatedUser(
    oid="test-user",
    name="Test User",
    email="test@example.com",
    roles=["Portal.User"],
    claims={},
)


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient) -> None:
    """GET /health returns 200 with ``{"status": "healthy"}``."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_readiness(client: AsyncClient) -> None:
    """GET /health/ready returns 200 with ``{"status": "ready"}``."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


@pytest.mark.asyncio
async def test_health_liveness_method_not_allowed(client: AsyncClient) -> None:
    """POST /health is not allowed."""
    response = await client.post("/health")
    assert response.status_code == 405


@pytest.mark.asyncio
@patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER)
async def test_api_catalog_placeholder(_mock, client: AsyncClient) -> None:
    """GET /api/catalog/ returns 200 with a placeholder message."""
    response = await client.get("/api/catalog/", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert "message" in response.json()
