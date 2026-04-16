"""Azure API Center SDK client wrapper.

Wraps ``azure-mgmt-apicenter`` with error handling, structured logging, and
a clean interface consumed by the service layer.  Authentication always uses
``DefaultAzureCredential`` (managed identity in production, developer
credential chain locally).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential

if TYPE_CHECKING:
    from azure.mgmt.apicenter import ApiCenterMgmtClient as _ApiCenterMgmtClientType
    from azure.mgmt.apicenter.models import (
        Api,
        ApiDefinition,
        ApiVersion,
        Deployment,
        Environment,
    )

logger = logging.getLogger(__name__)


class ApiCenterClientError(Exception):
    """Base error raised by :class:`ApiCenterClient`."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiCenterNotFoundError(ApiCenterClientError):
    """Raised when the requested resource does not exist."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"Resource not found: {resource}", status_code=404)


class ApiCenterAuthError(ApiCenterClientError):
    """Raised when authentication / authorisation fails."""

    def __init__(self, detail: str = "Unauthorized") -> None:
        super().__init__(detail, status_code=401)


class ApiCenterUnavailableError(ApiCenterClientError):
    """Raised when the API Center service is unavailable."""

    def __init__(self, detail: str = "Service unavailable") -> None:
        super().__init__(detail, status_code=503)


class ApiCenterClient:
    """Thin wrapper around the Azure API Center Management SDK.

    Parameters
    ----------
    subscription_id:
        Azure subscription ID that owns the API Center service.
    resource_group:
        Resource group name.
    service_name:
        API Center service name.
    credential:
        An Azure credential object.  Defaults to ``DefaultAzureCredential``
        which works for both managed identity (production) and developer
        credential chains (local development).
    """

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        service_name: str,
        credential: object | None = None,
    ) -> None:
        self._subscription_id = subscription_id
        self._resource_group = resource_group
        self._service_name = service_name
        self._credential = credential or DefaultAzureCredential()
        self._mgmt_client: _ApiCenterMgmtClientType | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> _ApiCenterMgmtClientType:
        """Lazily create and return the management client."""
        if self._mgmt_client is None:
            from azure.mgmt.apicenter import ApiCenterMgmtClient

            self._mgmt_client = ApiCenterMgmtClient(
                credential=self._credential,
                subscription_id=self._subscription_id,
            )
        return self._mgmt_client

    def _handle_error(self, exc: Exception, context: str) -> None:
        """Translate Azure SDK exceptions into domain errors."""
        if isinstance(exc, ResourceNotFoundError):
            raise ApiCenterNotFoundError(context) from exc
        if isinstance(exc, HttpResponseError):
            status = exc.status_code
            if status in (401, 403):
                raise ApiCenterAuthError(str(exc)) from exc
            if status is not None and status >= 500:
                raise ApiCenterUnavailableError(str(exc)) from exc
            raise ApiCenterClientError(str(exc), status_code=status) from exc
        raise ApiCenterClientError(str(exc)) from exc

    # ------------------------------------------------------------------
    # API operations
    # ------------------------------------------------------------------

    def list_apis(self, filter_str: str | None = None) -> list[Api]:  # type: ignore[name-defined]
        """Return all APIs in the service.

        Parameters
        ----------
        filter_str:
            OData filter expression (e.g. ``"properties/kind eq 'rest'"``).
        """
        logger.debug(
            "ApiCenterClient.list_apis",
            extra={"service": self._service_name, "filter": filter_str},
        )
        try:
            pager = self._client().apis.list(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
                filter=filter_str,
            )
            return list(pager)
        except Exception as exc:
            self._handle_error(exc, f"apis in {self._service_name}")

    def get_api(self, api_name: str) -> Api:  # type: ignore[name-defined]
        """Return a single API by name."""
        logger.debug("ApiCenterClient.get_api", extra={"api": api_name})
        try:
            return self._client().apis.get(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
                api_name=api_name,
            )
        except Exception as exc:
            self._handle_error(exc, f"api/{api_name}")

    def list_api_versions(self, api_name: str) -> list[ApiVersion]:  # type: ignore[name-defined]
        """Return all versions for a given API."""
        logger.debug("ApiCenterClient.list_api_versions", extra={"api": api_name})
        try:
            pager = self._client().api_versions.list(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
                api_name=api_name,
            )
            return list(pager)
        except Exception as exc:
            self._handle_error(exc, f"api/{api_name}/versions")

    def list_api_definitions(self, api_name: str, version_name: str) -> list[ApiDefinition]:  # type: ignore[name-defined]
        """Return all definitions (spec documents) for a given API version."""
        logger.debug(
            "ApiCenterClient.list_api_definitions",
            extra={"api": api_name, "version": version_name},
        )
        try:
            pager = self._client().api_definitions.list(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
                api_name=api_name,
                version_name=version_name,
            )
            return list(pager)
        except Exception as exc:
            self._handle_error(exc, f"api/{api_name}/versions/{version_name}/definitions")

    def export_api_specification(
        self, api_name: str, version_name: str, definition_name: str
    ) -> str | None:
        """Export the raw specification content for a given definition.

        Returns the specification as a string (JSON or YAML) or ``None`` if
        the export returned no content.
        """
        logger.debug(
            "ApiCenterClient.export_api_specification",
            extra={"api": api_name, "version": version_name, "definition": definition_name},
        )
        try:
            result = self._client().api_definitions.export_specification(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
                api_name=api_name,
                version_name=version_name,
                definition_name=definition_name,
            )
            return result.value if result and result.value else None
        except Exception as exc:
            self._handle_error(exc, f"api/{api_name}/versions/{version_name}/definitions/{definition_name}/export")

    def list_environments(self) -> list[Environment]:  # type: ignore[name-defined]
        """Return all environments in the service."""
        logger.debug("ApiCenterClient.list_environments", extra={"service": self._service_name})
        try:
            pager = self._client().environments.list(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
            )
            return list(pager)
        except Exception as exc:
            self._handle_error(exc, "environments")

    def list_deployments(self, api_name: str) -> list[Deployment]:  # type: ignore[name-defined]
        """Return all deployments for a given API."""
        logger.debug("ApiCenterClient.list_deployments", extra={"api": api_name})
        try:
            pager = self._client().deployments.list(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
                api_name=api_name,
            )
            return list(pager)
        except Exception as exc:
            self._handle_error(exc, f"api/{api_name}/deployments")

    def close(self) -> None:
        """Close the underlying management client session."""
        if self._mgmt_client is not None:
            self._mgmt_client.close()
            self._mgmt_client = None
