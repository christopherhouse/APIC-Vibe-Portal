"""Azure API Center data-plane REST client.

Communicates with the API Center **data-plane** endpoint
(``https://{service}.data.{region}.azure-apicenter.ms``) instead of the ARM
management plane.  This gives lower latency, higher throttling limits, and
requires only the ``Azure API Center Data Reader`` role (``c7244dfb-…``)
instead of service-level management permissions.

Authentication uses ``azure-identity`` to obtain a bearer token for the
``https://azure-apicenter.net/.default`` scope.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from azure.identity import DefaultAzureCredential

from apic_client.exceptions import (
    ApiCenterAuthError,
    ApiCenterClientError,
    ApiCenterNotFoundError,
    ApiCenterUnavailableError,
)

logger = structlog.get_logger()

_DATA_PLANE_SCOPE = "https://azure-apicenter.net/.default"
_API_VERSION = "2024-02-01-preview"


class ApiCenterDataPlaneClient:
    """Data-plane client for Azure API Center.

    Parameters
    ----------
    base_url:
        The data-plane endpoint, e.g.
        ``https://myapic.data.eastus.azure-apicenter.ms``.
    workspace_name:
        API Center workspace name.  Defaults to ``"default"``.
    credential:
        An Azure credential object.  Defaults to ``DefaultAzureCredential``.
    """

    def __init__(
        self,
        base_url: str,
        workspace_name: str = "default",
        credential: object | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._workspace_name = workspace_name
        self._credential = credential or DefaultAzureCredential()
        self._http: httpx.Client | None = None
        self._token: str | None = None
        self._token_expiry: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        """Obtain or refresh a bearer token for the data-plane scope."""
        now = time.time()
        if self._token and now < self._token_expiry - 60:
            return self._token
        token_result = self._credential.get_token(_DATA_PLANE_SCOPE)
        self._token = token_result.token
        self._token_expiry = token_result.expires_on
        return self._token

    def _client(self) -> httpx.Client:
        """Lazily create and return the HTTP client."""
        if self._http is None:
            self._http = httpx.Client(
                base_url=self._base_url,
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._http

    def _headers(self) -> dict[str, str]:
        """Return authorization and content-type headers."""
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _workspace_path(self, *segments: str) -> str:
        """Build a path under ``/workspaces/{name}/``."""
        parts = "/".join(segments)
        return f"/workspaces/{self._workspace_name}/{parts}"

    def _handle_response(self, response: httpx.Response, context: str) -> Any:
        """Translate HTTP errors into domain exceptions."""
        if response.is_success:
            return response.json()

        status = response.status_code
        try:
            body = response.json()
            message = body.get("error", {}).get("message", response.text)
        except Exception:
            message = response.text

        if status == 404:
            raise ApiCenterNotFoundError(context)
        if status in (401, 403):
            raise ApiCenterAuthError(message)
        if status >= 500:
            raise ApiCenterUnavailableError(message)
        raise ApiCenterClientError(f"{context}: {message}", status_code=status)

    def _get(self, path: str, context: str, params: dict[str, Any] | None = None) -> Any:
        """Issue a GET request and return the parsed JSON response."""
        logger.debug("api_center_data_plane.get", path=path, context=context)
        response = self._client().get(
            path,
            headers=self._headers(),
            params={"api-version": _API_VERSION, **(params or {})},
        )
        return self._handle_response(response, context)

    def _get_paged(self, path: str, context: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Follow ``nextLink`` pagination and return all items."""
        all_items: list[dict[str, Any]] = []
        current_url: str | None = path
        query_params: dict[str, Any] | None = {"api-version": _API_VERSION, **(params or {})}

        while current_url is not None:
            logger.debug("api_center_data_plane.get_paged", url=current_url, context=context)
            response = self._client().get(
                current_url,
                headers=self._headers(),
                params=query_params,
            )
            data = self._handle_response(response, context)
            all_items.extend(data.get("value", []))
            next_link = data.get("nextLink")
            if next_link:
                # nextLink is an absolute URL — use it directly.
                # Keep api-version unless it's already present in the URL.
                current_url = next_link
                query_params = None if "api-version" in next_link else {"api-version": _API_VERSION}
            else:
                current_url = None

        return all_items

    def _post(self, path: str, context: str, json_body: dict[str, Any] | None = None) -> Any:
        """Issue a POST request and return the parsed JSON response."""
        logger.debug("api_center_data_plane.post", path=path, context=context)
        response = self._client().post(
            path,
            headers=self._headers(),
            params={"api-version": _API_VERSION},
            json=json_body,
        )
        return self._handle_response(response, context)

    # ------------------------------------------------------------------
    # API operations
    # ------------------------------------------------------------------

    def list_apis(self) -> list[dict[str, Any]]:
        """Return all APIs in the workspace."""
        path = self._workspace_path("apis")
        return self._get_paged(path, "apis")

    def get_api(self, api_name: str) -> dict[str, Any]:
        """Return a single API by name."""
        path = self._workspace_path("apis", api_name)
        return self._get(path, f"api/{api_name}")

    def list_api_versions(self, api_name: str) -> list[dict[str, Any]]:
        """Return all versions for a given API."""
        path = self._workspace_path("apis", api_name, "versions")
        return self._get_paged(path, f"api/{api_name}/versions")

    def list_api_definitions(self, api_name: str, version_name: str) -> list[dict[str, Any]]:
        """Return all definitions (spec documents) for a given API version."""
        path = self._workspace_path("apis", api_name, "versions", version_name, "definitions")
        return self._get_paged(path, f"api/{api_name}/versions/{version_name}/definitions")

    def export_api_specification(self, api_name: str, version_name: str, definition_name: str) -> str | None:
        """Export the raw specification content for a given definition.

        The data-plane export is an async operation:
        1. POST ``:exportSpecification`` → 202 with ``Operation-Location``
        2. Poll the operation URL until status is ``Succeeded``
        3. Return ``result.value`` (the raw spec content)

        Returns ``None`` if the export yields no content.
        """
        path = self._workspace_path(
            "apis",
            api_name,
            "versions",
            version_name,
            "definitions",
            f"{definition_name}:exportSpecification",
        )
        context = f"api/{api_name}/versions/{version_name}/definitions/{definition_name}/export"
        logger.debug("api_center_data_plane.export_spec", path=path)

        response = self._client().post(
            path,
            headers=self._headers(),
            params={"api-version": _API_VERSION},
        )

        if response.status_code == 200:
            data = response.json()
            result = data.get("result", data)
            return result.get("value") if result else None

        if response.status_code != 202:
            self._handle_response(response, context)
            return None

        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            body = response.json() if response.content else {}
            result = body.get("result", body)
            return result.get("value") if result else None

        return self._poll_operation(operation_url, context)

    def _poll_operation(self, operation_url: str, context: str, max_polls: int = 30, delay: float = 1.0) -> str | None:
        """Poll an async operation URL until completion."""
        # Include api-version unless it's already present in the operation URL
        poll_params: dict[str, str] | None = None
        if "api-version" not in operation_url:
            poll_params = {"api-version": _API_VERSION}

        for _ in range(max_polls):
            time.sleep(delay)
            response = self._client().get(
                operation_url,
                headers=self._headers(),
                params=poll_params,
            )
            if not response.is_success:
                self._handle_response(response, context)
                return None

            data = response.json()
            status = data.get("status", "").lower()
            if status == "succeeded":
                result = data.get("result", {})
                return result.get("value") if result else None
            if status in ("failed", "canceled", "cancelled"):
                error_msg = data.get("error", {}).get("message", f"Operation {status}")
                raise ApiCenterClientError(f"{context}: {error_msg}")

        raise ApiCenterClientError(f"{context}: operation timed out after {max_polls} polls")

    def list_environments(self) -> list[dict[str, Any]]:
        """Return all environments in the workspace."""
        path = self._workspace_path("environments")
        return self._get_paged(path, "environments")

    def list_deployments(self, api_name: str) -> list[dict[str, Any]]:
        """Return all deployments for a given API."""
        path = self._workspace_path("apis", api_name, "deployments")
        return self._get_paged(path, f"api/{api_name}/deployments")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http is not None:
            self._http.close()
            self._http = None
