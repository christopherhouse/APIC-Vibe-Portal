"""Azure AI Foundry Agent Service client.

Wraps the Microsoft Agent Framework (MAF) ``OpenAIChatClient`` and configures
it to target an Azure AI Foundry project endpoint.  Authentication uses
``DefaultAzureCredential`` (managed identity in production, developer
credential chain locally).

The Foundry Agent Service exposes an Azure OpenAI-compatible API at the
project endpoint, so the same MAF ``OpenAIChatClient`` used for direct
Azure OpenAI can be pointed at the Foundry project URL instead.

Error handling follows the same patterns as
:class:`~apic_vibe_portal_bff.clients.openai_client.OpenAIClient`.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# Azure AI Services token scope used for Foundry authentication
_AI_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FoundryAgentClientError(Exception):
    """Base error raised by :class:`FoundryAgentClient`."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FoundryAgentUnavailableError(FoundryAgentClientError):
    """Raised when the Foundry Agent Service is unavailable."""

    def __init__(self, detail: str = "Foundry Agent Service unavailable") -> None:
        super().__init__(detail, status_code=503)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FoundryAgentClient:
    """Client for Azure AI Foundry Agent Service.

    Authenticates to an Azure AI Foundry project endpoint and provides a
    MAF-compatible ``OpenAIChatClient`` that agents can use for LLM calls.

    Parameters
    ----------
    project_endpoint:
        Azure AI Foundry project endpoint URL
        (e.g. ``https://my-foundry.api.azureml.ms``).
        Automatically normalised to ``https://``.
    deployment:
        Chat model deployment name (e.g. ``gpt-4o``).
    api_version:
        Azure OpenAI API version string.
    credential:
        Azure credential object.  Defaults to ``DefaultAzureCredential``.
    """

    def __init__(
        self,
        project_endpoint: str,
        deployment: str,
        api_version: str = "2024-06-01",
        credential: Any | None = None,
    ) -> None:
        self._endpoint = self._normalize_endpoint(project_endpoint)
        self._deployment = deployment
        self._api_version = api_version
        self._credential = credential or DefaultAzureCredential()
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        """Ensure the endpoint uses ``https://``.

        Upgrades ``http://`` to ``https://`` and prepends the scheme when
        absent, consistent with the :class:`~apic_vibe_portal_bff.clients.ai_search_client.AISearchClient`
        normalisation.
        """
        stripped = endpoint.strip()
        if not stripped:
            return stripped
        if stripped.startswith("http://"):
            logger.warning(
                "Foundry endpoint uses http:// — upgrading to https://",
                extra={"original_endpoint": stripped},
            )
            return "https://" + stripped[len("http://") :]
        if not stripped.startswith("https://"):
            return "https://" + stripped
        return stripped

    # ------------------------------------------------------------------
    # MAF client access
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazily create and return the MAF ``OpenAIChatClient`` for the Foundry endpoint."""
        if self._client is None:
            from agent_framework.openai import OpenAIChatClient

            self._client = OpenAIChatClient(
                model=self._deployment,
                azure_endpoint=self._endpoint,
                api_version=self._api_version,
                credential=self._credential,
            )
        return self._client

    def get_maf_client(self) -> Any:
        """Return the underlying MAF ``OpenAIChatClient`` for use by agents.

        The returned client can be passed directly to
        :class:`~apic_vibe_portal_bff.agents.api_discovery_agent.definition.ApiDiscoveryAgent`
        or any other :class:`~apic_vibe_portal_bff.agents.base_agent.BaseAgent` implementation.
        """
        return self._get_client()

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Return ``True`` when a non-empty project endpoint has been set.

        Used at startup to decide whether to wire the Foundry client or fall
        back to the direct Azure OpenAI path.
        """
        return bool(self._endpoint.strip())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release the underlying MAF client."""
        if self._client is not None:
            self._client = None
