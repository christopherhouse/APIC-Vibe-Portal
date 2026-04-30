"""Cosmos DB metadata document for a single backup."""

from __future__ import annotations

from pydantic import BaseModel, Field

from apic_backup.models.backup_manifest import ManifestCounts


class BackupMetadata(BaseModel):
    """One document in the ``backup-metadata`` Cosmos DB container."""

    id: str
    backup_id: str = Field(..., alias="backupId")
    source_service_name: str = Field(..., alias="sourceServiceName")
    timestamp: str
    blob_url: str = Field(..., alias="blobUrl")
    blob_name: str = Field(..., alias="blobName")
    size_bytes: int = Field(..., alias="sizeBytes")
    counts: ManifestCounts
    retention_tiers: list[str] = Field(default_factory=list, alias="retentionTiers")
    status: str = "completed"
    duration_ms: int = Field(0, alias="durationMs")
    error: str | None = None
    ttl: int = -1

    model_config = {"populate_by_name": True, "extra": "ignore"}

    def to_document(self) -> dict:
        """Return the JSON-serializable dict to persist in Cosmos DB."""
        return self.model_dump(by_alias=True, exclude_none=False)
