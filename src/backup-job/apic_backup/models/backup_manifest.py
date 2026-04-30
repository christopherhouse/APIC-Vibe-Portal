"""Backup manifest model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ManifestSource(BaseModel):
    subscription_id: str = Field(..., alias="subscriptionId")
    resource_group: str = Field(..., alias="resourceGroup")
    service_name: str = Field(..., alias="serviceName")
    location: str = ""

    model_config = {"populate_by_name": True}


class ManifestCounts(BaseModel):
    apis: int = 0
    versions: int = 0
    definitions: int = 0
    deployments: int = 0
    environments: int = 0

    @property
    def total_entities(self) -> int:
        return self.apis + self.versions + self.definitions + self.deployments + self.environments


class BackupManifest(BaseModel):
    """Manifest written into every backup ZIP at ``manifest.json``."""

    version: str = "1.0"
    format: str = "apic-backup"
    created_at: str = Field(..., alias="createdAt")
    source: ManifestSource
    counts: ManifestCounts
    backup_job_version: str = Field("1.0.0", alias="backupJobVersion")

    model_config = {"populate_by_name": True}
