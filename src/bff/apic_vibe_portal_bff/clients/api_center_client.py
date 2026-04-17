"""Azure API Center data-plane client wrapper.

Thin wrapper around the shared :class:`apic_client.ApiCenterDataPlaneClient`
that provides the same public interface the BFF service layer and router
expect.  Authentication uses ``DefaultAzureCredential`` (managed identity in
production, developer credential chain locally).

All domain exceptions are re-exported from the shared ``apic_client`` package
so that existing imports continue to work.
"""

from __future__ import annotations

import logging
from typing import Any

from apic_client import ApiCenterDataPlaneClient
from apic_client.exceptions import (
    ApiCenterAuthError,
    ApiCenterClientError,
    ApiCenterNotFoundError,
    ApiCenterUnavailableError,
)

logger = logging.getLogger(__name__)

# Re-export exceptions so existing ``from …api_center_client import …``
# statements keep working throughout the BFF.
__all__ = [
    "ApiCenterAuthError",
    "ApiCenterClient",
    "ApiCenterClientError",
    "ApiCenterNotFoundError",
    "ApiCenterUnavailableError",
]


class ApiCenterClient:
    """BFF-facing wrapper around the shared data-plane client.

    Parameters
    ----------
    base_url:
        The API Center data-plane endpoint, e.g.
        ``https://myapic.data.eastus.azure-apicenter.ms``.
    credential:
        An Azure credential object.  Defaults to ``DefaultAzureCredential``.
    workspace_name:
        API Center workspace name.  Defaults to ``"default"``.
    """

    def __init__(
        self,
        base_url: str,
        credential: object | None = None,
        workspace_name: str = "default",
    ) -> None:
        self._dp_client = ApiCenterDataPlaneClient(
            base_url=base_url,
            workspace_name=workspace_name,
            credential=credential,
        )

    # ------------------------------------------------------------------
    # API operations — delegate to the shared data-plane client
    # ------------------------------------------------------------------

    def list_apis(self, filter_str: str | None = None) -> list[dict[str, Any]]:
        """Return all APIs in the workspace.

        Parameters
        ----------
        filter_str:
            Ignored in the data-plane client (no OData support on data
            plane). Kept for interface compatibility with callers that
            pass it; filtering is applied in-process by the service layer.
        """
        logger.debug(
            "ApiCenterClient.list_apis",
            extra={"filter": filter_str},
        )
        return self._dp_client.list_apis()

    def get_api(self, api_name: str) -> dict[str, Any]:
        """Return a single API by name."""
        logger.debug("ApiCenterClient.get_api", extra={"api": api_name})
        return self._dp_client.get_api(api_name)

    def list_api_versions(self, api_name: str) -> list[dict[str, Any]]:
        """Return all versions for a given API."""
        logger.debug("ApiCenterClient.list_api_versions", extra={"api": api_name})
        return self._dp_client.list_api_versions(api_name)

    def list_api_definitions(self, api_name: str, version_name: str) -> list[dict[str, Any]]:
        """Return all definitions (spec documents) for a given API version."""
        logger.debug(
            "ApiCenterClient.list_api_definitions",
            extra={"api": api_name, "version": version_name},
        )
        return self._dp_client.list_api_definitions(api_name, version_name)

    def export_api_specification(self, api_name: str, version_name: str, definition_name: str) -> str | None:
        """Export the raw specification content for a given definition."""
        logger.debug(
            "ApiCenterClient.export_api_specification",
            extra={"api": api_name, "version": version_name, "definition": definition_name},
        )
        return self._dp_client.export_api_specification(api_name, version_name, definition_name)

    def list_environments(self) -> list[dict[str, Any]]:
        """Return all environments in the workspace."""
        logger.debug("ApiCenterClient.list_environments")
        return self._dp_client.list_environments()

    def list_deployments(self, api_name: str) -> list[dict[str, Any]]:
        """Return all deployments for a given API."""
        logger.debug("ApiCenterClient.list_deployments", extra={"api": api_name})
        return self._dp_client.list_deployments(api_name)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._dp_client.close()
