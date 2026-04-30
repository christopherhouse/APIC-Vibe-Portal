"""Admin endpoints for API Center backups.

All endpoints require the ``Portal.Admin`` role.

Endpoints
---------
GET /api/admin/backups               — List recent backup metadata
GET /api/admin/backups/{backup_id}   — Retrieve a single backup metadata document
GET /api/admin/backups/{backup_id}/download — Return a short-lived SAS URL
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from apic_vibe_portal_bff.middleware.rbac import require_role
from apic_vibe_portal_bff.services.backup_service import (
    BackupNotConfiguredError,
    BackupNotFoundError,
    BackupService,
    get_backup_service,
)

logger = logging.getLogger(__name__)

_ADMIN_ROLE = "Portal.Admin"

router = APIRouter(tags=["admin", "backups"], prefix="/api/admin/backups")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class BackupCounts(BaseModel):
    apis: int = 0
    versions: int = 0
    definitions: int = 0
    deployments: int = 0
    environments: int = 0


class BackupSummary(BaseModel):
    backup_id: str = Field(..., alias="backupId")
    source_service_name: str = Field(..., alias="sourceServiceName")
    timestamp: str
    blob_name: str = Field(..., alias="blobName")
    size_bytes: int = Field(..., alias="sizeBytes")
    size_formatted: str = Field(..., alias="sizeFormatted")
    counts: BackupCounts
    retention_tiers: list[str] = Field(default_factory=list, alias="retentionTiers")
    status: str = "completed"
    duration_ms: int = Field(0, alias="durationMs")

    model_config = {"populate_by_name": True}


class BackupListResponse(BaseModel):
    items: list[BackupSummary]
    count: int


class BackupDownloadResponse(BaseModel):
    backup_id: str = Field(..., alias="backupId")
    download_url: str = Field(..., alias="downloadUrl")
    expires_at: str = Field(..., alias="expiresAt")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _to_summary(doc: dict[str, Any]) -> BackupSummary:
    return BackupSummary.model_validate(doc)


@router.get(
    "",
    response_model=BackupListResponse,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="List recent API Center backups",
)
def list_backups(
    limit: int = Query(default=50, ge=1, le=500),
    service: BackupService = Depends(get_backup_service),  # noqa: B008
) -> BackupListResponse:
    items = [_to_summary(item) for item in service.list_backups(limit=limit)]
    return BackupListResponse(items=items, count=len(items))


@router.get(
    "/{backup_id}",
    response_model=BackupSummary,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Retrieve a single backup metadata document",
)
def get_backup(
    backup_id: str,
    service: BackupService = Depends(get_backup_service),  # noqa: B008
) -> BackupSummary:
    try:
        return _to_summary(service.get_backup(backup_id))
    except BackupNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BACKUP_NOT_FOUND", "message": f"Backup {backup_id} not found"},
        ) from exc


@router.get(
    "/{backup_id}/download",
    response_model=BackupDownloadResponse,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Return a short-lived SAS URL for downloading the backup ZIP",
)
def get_backup_download(
    backup_id: str,
    service: BackupService = Depends(get_backup_service),  # noqa: B008
) -> BackupDownloadResponse:
    try:
        url, expires_at = service.generate_download_url(backup_id)
    except BackupNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BACKUP_NOT_FOUND", "message": f"Backup {backup_id} not found"},
        ) from exc
    except BackupNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "BACKUP_NOT_CONFIGURED",
                "message": "Backup storage is not configured for this environment",
            },
        ) from exc
    return BackupDownloadResponse(
        backupId=backup_id,
        downloadUrl=url,
        expiresAt=expires_at.isoformat(),
    )
