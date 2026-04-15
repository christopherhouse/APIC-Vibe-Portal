"""Placeholder API catalog routes.

These endpoints will be implemented in task 010 (BFF API Catalog Endpoints).
Registering the router now to verify the wiring is correct.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from apic_vibe_portal_bff.middleware.rbac import require_any_role

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get(
    "/",
    dependencies=[Depends(require_any_role(["Portal.User", "Portal.Admin", "API.Owner"]))],
)
async def list_apis() -> dict[str, str]:
    """Placeholder — list APIs from Azure API Center."""
    return {"message": "API catalog endpoint — not yet implemented"}
