"""Environment-based configuration using Pydantic Settings.

All configuration is loaded from environment variables (or a `.env` file in
development).  Missing **required** variables cause the application to fail
fast on startup with a clear validation error.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required variables will raise a ``ValidationError`` at import time if
    they are not set, ensuring fail-fast behaviour.
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
    api_center_endpoint: str = Field(default="", description="Azure API Center endpoint")
    ai_search_endpoint: str = Field(default="", description="Azure AI Search endpoint")
    openai_endpoint: str = Field(default="", description="Azure OpenAI endpoint")
    key_vault_url: str = Field(default="", description="Azure Key Vault URL")
    appinsights_connection_string: str = Field(default="", description="Application Insights connection string")


def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    The first call validates environment variables; subsequent calls return
    the same object.
    """
    return Settings()
