"""Azure AI Foundry Agent Service client.

Wraps the Microsoft Agent Framework (MAF) ``OpenAIChatClient`` and configures
it to target an Azure AI Foundry project endpoint using the **v1 API**.

Authentication uses ``DefaultAzureCredential`` (managed identity in
production, developer credential chain locally).  The credential is
converted to a token provider with the ``https://ai.azure.com/.default``
scope, which is passed as ``api_key`` to the MAF client so that the
underlying ``AsyncOpenAI`` client is used (OpenAI routing) rather than
``AsyncAzureOpenAI`` (Azure routing).  This avoids appending a dated
``api-version`` query parameter that the v1 endpoint rejects.

Error handling follows the same patterns as
:class:`~apic_vibe_portal_bff.clients.openai_client.OpenAIClient`.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

logger = logging.getLogger(__name__)

# Token scope for Azure AI Foundry v1 API
_AI_FOUNDRY_SCOPE = "https://ai.azure.com/.default"


def _async_token_provider(credential: Any) -> Any:
    """Return an **async** callable that provides a bearer token.

    ``get_bearer_token_provider`` returns a *synchronous* callable.  Newer
    versions of the OpenAI SDK ``await`` the ``api_key`` provider inside
    ``AsyncOpenAI._refresh_api_key``.  If the provider is synchronous the
    ``await`` receives a plain ``str`` and raises
    ``TypeError: 'str' object can't be awaited``.

    Wrapping the sync provider in a thin ``async`` function satisfies the
    SDK contract while keeping the existing ``DefaultAzureCredential``
    (sync) auth path.
    """
    sync_provider = get_bearer_token_provider(credential, _AI_FOUNDRY_SCOPE)

    async def _provider() -> str:
        return sync_provider()

    return _provider


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
    """Client for Azure AI Foundry Agent Service (v1 API).

    Authenticates to an Azure AI Foundry project endpoint and provides a
    MAF-compatible ``OpenAIChatClient`` that agents can use for LLM calls.

    Uses the v1 API approach: ``base_url={endpoint}/openai/v1/`` with a
    bearer token provider as ``api_key``, which routes MAF through the
    standard ``AsyncOpenAI`` client and avoids the deprecated dated
    ``api-version`` query parameter.

    Parameters
    ----------
    project_endpoint:
        Azure AI Foundry project endpoint URL
        (e.g. ``https://my-foundry.api.azureml.ms``).
        Automatically normalised to ``https://``.
    deployment:
        Chat model deployment name (e.g. ``gpt-4o``).
    credential:
        Azure credential object.  Defaults to ``DefaultAzureCredential``.
    """

    def __init__(
        self,
        project_endpoint: str,
        deployment: str,
        credential: Any | None = None,
    ) -> None:
        self._endpoint = self._normalize_endpoint(project_endpoint)
        self._deployment = deployment
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
        """Lazily create and return the MAF ``OpenAIChatClient`` for the Foundry v1 endpoint.

        Uses OpenAI routing (``base_url`` + ``api_key``) instead of Azure
        routing (``azure_endpoint`` + ``credential``) so that the
        underlying ``AsyncOpenAI`` client does not append a dated
        ``api-version`` query parameter.
        """
        if self._client is None:
            from agent_framework.openai import OpenAIChatClient

            token_provider = _async_token_provider(self._credential)
            base_url = f"{self._endpoint.rstrip('/')}/openai/v1/"

            self._client = OpenAIChatClient(
                model=self._deployment,
                base_url=base_url,
                api_key=token_provider,
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
