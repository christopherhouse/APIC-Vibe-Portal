"""Tests for health check endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


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
async def test_api_catalog_requires_auth(client: AsyncClient) -> None:
    """GET /api/catalog/ returns 401 when unauthenticated (RBAC enforced)."""
    response = await client.get("/api/catalog/")
    assert response.status_code == 401
