"""Placeholder API catalog routes.

These endpoints will be implemented in task 010 (BFF API Catalog Endpoints).
Registering the router now to verify the wiring is correct.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/")
async def list_apis() -> dict[str, str]:
    """Placeholder — list APIs from Azure API Center."""
    return {"message": "API catalog endpoint — not yet implemented"}
