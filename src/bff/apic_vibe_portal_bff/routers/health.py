"""Health check endpoints.

``GET /health``      — Liveness probe (always returns 200).
``GET /health/ready`` — Readiness probe (stubs for Azure service checks).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Liveness check — returns 200 if the process is running."""
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    """Readiness check — validates downstream service connectivity.

    Currently stubbed; will be expanded to verify Azure service
    connections (API Center, AI Search, etc.) in later tasks.
    """
    # TODO: Add Azure service connectivity checks (tasks 009, 013, 017)
    return {"status": "ready"}
