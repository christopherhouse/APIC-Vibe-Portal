"""Environment-based configuration using Pydantic Settings.

All configuration is loaded from environment variables (or a `.env` file in
development).  Server settings have sensible defaults for local development.
Azure service settings default to empty strings and are only required in
production — see the ``environment`` field.
"""

from __future__ import annotations

import functools

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All fields have defaults suitable for local development. Azure service
    fields default to empty strings; they are expected to be set in
    production deployments.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Server ----------------------------------------------------------
    port: int = Field(default=8000, description="Port the BFF listens on")
    environment: str = Field(default="development", description="Runtime environment (development | production)")
    log_level: str = Field(default="INFO", description="Logging level")

    # --- Frontend --------------------------------------------------------
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend origin URL")

    # --- Azure services (required in production) -------------------------
    api_center_endpoint: str = Field(
        default="",
        description=("Azure API Center data-plane endpoint (e.g. https://myapic.data.eastus.azure-apicenter.ms)"),
    )
    ai_search_endpoint: str = Field(default="", description="Azure AI Search endpoint")
    ai_search_index_name: str = Field(default="apic-apis", description="Azure AI Search index name")
    openai_endpoint: str = Field(default="", description="Azure OpenAI endpoint")
    openai_chat_deployment: str = Field(default="gpt-4o", description="Azure OpenAI chat model deployment name")
    key_vault_url: str = Field(default="", description="Azure Key Vault URL")
    appinsights_connection_string: str = Field(default="", description="Application Insights connection string")

    # --- Azure API Center -----------------------------------------------
    api_center_workspace_name: str = Field(default="default", description="API Center workspace name")
    cache_ttl_seconds: int = Field(
        default=300, description="Default cache TTL in seconds (Redis and in-memory fallback)"
    )

    # --- Redis cache ----------------------------------------------------
    redis_host: str = Field(
        default="",
        description=(
            "Azure Cache for Redis hostname (e.g. my-redis.redis.cache.windows.net). "
            "When empty the BFF falls back to a single-process in-memory cache."
        ),
    )
    redis_port: int = Field(
        default=6380,
        description="Azure Cache for Redis SSL port (default 6380).",
    )

    # --- Cosmos DB -------------------------------------------------------
    cosmos_db_endpoint: str = Field(
        default="",
        description="Azure Cosmos DB account endpoint (e.g. https://myaccount.documents.azure.com:443/)",
    )
    cosmos_db_database_name: str = Field(
        default="apic-vibe-portal",
        description="Cosmos DB database name",
    )
    cosmos_db_chat_container: str = Field(
        default="chat-sessions",
        description="Cosmos DB container name for chat sessions",
    )
    cosmos_db_governance_container: str = Field(
        default="governance-snapshots",
        description="Cosmos DB container name for governance snapshots",
    )
    cosmos_db_analytics_container: str = Field(
        default="analytics-events",
        description="Cosmos DB container name for analytics events",
    )
    cosmos_db_access_policies_container: str = Field(
        default="api-access-policies",
        description="Cosmos DB container name for API access policies (security trimming)",
    )

    # --- Azure AI Foundry Agent Service ---------------------------------
    foundry_project_endpoint: str = Field(
        default="",
        description=(
            "Azure AI Foundry project endpoint URL "
            "(e.g. https://my-foundry.api.azureml.ms). "
            "When set, agent requests are routed through the Foundry Agent Service "
            "instead of direct Azure OpenAI."
        ),
    )

    # --- Entra ID (authentication) ---------------------------------------
    bff_entra_tenant_id: str = Field(default="", description="Entra ID (Azure AD) tenant ID")
    bff_entra_client_id: str = Field(default="", description="Entra ID client (audience) ID for the BFF API")
    bff_entra_audience: str = Field(default="", description="Expected token audience (defaults to client ID if empty)")


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    The first call validates environment variables; subsequent calls return
    the same object.
    """
    return Settings()
