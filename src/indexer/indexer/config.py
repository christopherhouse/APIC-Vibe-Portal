"""Azure AI Search indexing pipeline — configuration.

All settings are loaded from environment variables (or a ``.env`` file in
development). Defaults are safe for local iteration; production deployments
must supply the Azure service endpoints.
"""

from __future__ import annotations

import functools

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IndexerSettings(BaseSettings):
    """Settings for the AI Search indexing container job."""

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
    appinsights_connection_string: str = Field(
        default="",
        description="Application Insights connection string for OpenTelemetry export",
    )

    # --- Azure AI Search -------------------------------------------------
    ai_search_endpoint: str = Field(default="", description="Azure AI Search endpoint URL")
    ai_search_index_name: str = Field(default="apic-apis", description="Name of the AI Search index")

    # --- Azure OpenAI ----------------------------------------------------
    openai_endpoint: str = Field(default="", description="Azure OpenAI endpoint URL")
    openai_embedding_deployment: str = Field(
        default="text-embedding-ada-002",
        description="Azure OpenAI embedding model deployment name",
    )
    openai_embedding_dimensions: int = Field(
        default=1536,
        description="Embedding vector dimensions (1536 for text-embedding-ada-002)",
    )

    # --- Azure API Center ------------------------------------------------
    api_center_endpoint: str = Field(
        default="",
        description=("Azure API Center data-plane endpoint (e.g. https://myapic.data.eastus.azure-apicenter.ms)"),
    )
    api_center_workspace_name: str = Field(default="default", description="API Center workspace name")

    # --- Indexing behaviour ----------------------------------------------
    embedding_chunk_size: int = Field(
        default=8000,
        description="Maximum characters per chunk when splitting large spec content for embedding",
    )
    reindex_cron_schedule: str = Field(
        default="*/5 * * * *",
        description=(
            "Cron expression for the Azure Container Apps Job schedule. "
            "This value is read by infrastructure tooling to configure the job trigger; "
            "the container itself performs one full reindex run per invocation."
        ),
    )


@functools.lru_cache(maxsize=1)
def get_settings() -> IndexerSettings:
    """Return a cached :class:`IndexerSettings` instance."""
    return IndexerSettings()
