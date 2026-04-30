"""Configuration for the backup container job.

All settings are loaded from environment variables (or a ``.env`` file in
local development).
"""

from __future__ import annotations

import functools

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackupSettings(BaseSettings):
    """Settings for the API Center backup container job."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Azure identity --------------------------------------------------
    azure_client_id: str = Field(
        default="",
        description=(
            "Client ID of the User-Assigned Managed Identity (UAMI) assigned to the "
            "Container Apps Job.  Pins DefaultAzureCredential to this identity in Azure."
        ),
    )

    # --- Runtime ---------------------------------------------------------
    log_level: str = Field(default="INFO", description="Logging level")
    applicationinsights_connection_string: str = Field(
        default="",
        description="Application Insights connection string for OpenTelemetry export",
    )

    # --- API Center source ----------------------------------------------
    apic_subscription_id: str = Field(default="", description="API Center subscription ID")
    apic_resource_group: str = Field(default="", description="API Center resource group")
    apic_service_name: str = Field(default="", description="API Center service name")
    apic_location: str = Field(
        default="",
        description="Azure region of the API Center service (recorded in manifest.source.location)",
    )
    api_center_endpoint: str = Field(
        default="",
        description="Azure API Center data-plane endpoint (https://...azure-apicenter.ms)",
    )
    api_center_workspace_name: str = Field(default="default", description="API Center workspace name")

    # --- Backup storage --------------------------------------------------
    backup_storage_account_url: str = Field(
        default="",
        description="Blob storage account URL (https://acct.blob.core.windows.net)",
    )
    backup_container_name: str = Field(default="apic-backups", description="Blob container name")

    # --- Cosmos DB metadata ----------------------------------------------
    cosmos_endpoint: str = Field(default="", description="Cosmos DB account endpoint")
    cosmos_database: str = Field(default="apic-vibe-portal", description="Cosmos DB database name")
    cosmos_backup_container: str = Field(
        default="backup-metadata",
        description="Cosmos DB container for backup metadata",
    )

    # --- Retention policy (grandfather-father-son) -----------------------
    retention_hourly: int = Field(default=24, ge=0, description="Hourly backups to retain")
    retention_daily: int = Field(default=30, ge=0, description="Daily backups to retain")
    retention_monthly: int = Field(default=12, ge=0, description="Monthly backups to retain")
    retention_annual: int = Field(default=3, ge=0, description="Annual backups to retain")

    # --- Backup behaviour ------------------------------------------------
    backup_cron_schedule: str = Field(
        default="0 * * * *",
        description="Cron expression read by the deploy script when creating the Container Apps Job",
    )


@functools.lru_cache(maxsize=1)
def get_settings() -> BackupSettings:
    """Return a cached :class:`BackupSettings` instance."""
    return BackupSettings()
