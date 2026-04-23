"""Governance snapshot pipeline — configuration.

All settings are loaded from environment variables (or a ``.env`` file in
development). Defaults are safe for local iteration; production deployments
must supply the Azure service endpoints.
"""

from __future__ import annotations

import functools

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GovernanceWorkerSettings(BaseSettings):
    """Settings for the governance snapshot container job."""

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
            "Container Apps Job.  When set, ``DefaultAzureCredential`` is pinned to this "
            "specific identity, avoiding ambiguity on hosts with multiple assigned identities. "
            "Leave empty for local development (the full DefaultAzureCredential chain is used)."
        ),
    )

    # --- Runtime ---------------------------------------------------------
    log_level: str = Field(default="INFO", description="Logging level")
    applicationinsights_connection_string: str = Field(
        default="",
        description="Application Insights connection string for OpenTelemetry export",
    )

    # --- Azure API Center ------------------------------------------------
    api_center_endpoint: str = Field(
        default="",
        description="Azure API Center data-plane endpoint (e.g. https://myapic.data.eastus.azure-apicenter.ms)",
    )
    api_center_workspace_name: str = Field(default="default", description="API Center workspace name")

    # --- Azure Cosmos DB -------------------------------------------------
    cosmos_db_endpoint: str = Field(
        default="",
        description="Azure Cosmos DB account endpoint (e.g. https://myaccount.documents.azure.com:443/)",
    )
    cosmos_db_database_name: str = Field(
        default="apic-vibe-portal",
        description="Cosmos DB database name",
    )
    cosmos_db_governance_container: str = Field(
        default="governance-snapshots",
        description="Cosmos DB container name for governance snapshots",
    )

    # --- Worker behaviour ------------------------------------------------
    agent_id: str = Field(
        default="governance-worker",
        description="Agent identifier recorded on every snapshot document",
    )
    scan_cron_schedule: str = Field(
        default="0 2 * * *",
        description=(
            "Cron expression for the Azure Container Apps Job schedule. "
            "This value is read by infrastructure tooling; the container "
            "performs one full scan per invocation."
        ),
    )


@functools.lru_cache(maxsize=1)
def get_settings() -> GovernanceWorkerSettings:
    """Return a cached :class:`GovernanceWorkerSettings` instance."""
    return GovernanceWorkerSettings()
