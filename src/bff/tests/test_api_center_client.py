"""Unit tests for ApiCenterClient error handling and method delegation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

from apic_vibe_portal_bff.clients.api_center_client import (
    ApiCenterAuthError,
    ApiCenterClient,
    ApiCenterClientError,
    ApiCenterNotFoundError,
    ApiCenterUnavailableError,
)
from tests.api_center_mocks import (
    MOCK_API_DEFINITIONS,
    MOCK_APIS,
    MOCK_DEPLOYMENTS,
    MOCK_ENVIRONMENTS,
    MOCK_SPEC_CONTENT,
    MOCK_VERSIONS,
)


def _make_client(mock_mgmt: MagicMock) -> ApiCenterClient:
    """Return an ApiCenterClient whose _mgmt_client is pre-wired."""
    client = ApiCenterClient(
        subscription_id="sub-123",
        resource_group="rg-test",
        service_name="apic-test",
        credential=MagicMock(),
    )
    client._mgmt_client = mock_mgmt
    return client


def _mock_mgmt() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# list_apis
# ---------------------------------------------------------------------------


class TestListApis:
    def test_returns_list_of_apis(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.apis.list.return_value = iter(MOCK_APIS)
        client = _make_client(mgmt)

        result = client.list_apis()

        assert result == MOCK_APIS
        mgmt.apis.list.assert_called_once_with(
            resource_group_name="rg-test",
            service_name="apic-test",
            filter=None,
        )

    def test_passes_filter_to_sdk(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.apis.list.return_value = iter([])
        client = _make_client(mgmt)

        client.list_apis(filter_str="properties/kind eq 'rest'")

        mgmt.apis.list.assert_called_once_with(
            resource_group_name="rg-test",
            service_name="apic-test",
            filter="properties/kind eq 'rest'",
        )

    def test_not_found_raises_domain_error(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.apis.list.side_effect = ResourceNotFoundError("not found")
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterNotFoundError):
            client.list_apis()

    def test_auth_error_raises_domain_error(self) -> None:
        mgmt = _mock_mgmt()
        err = HttpResponseError(message="Unauthorized")
        err.status_code = 401
        mgmt.apis.list.side_effect = err
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterAuthError):
            client.list_apis()

    def test_forbidden_raises_auth_error(self) -> None:
        mgmt = _mock_mgmt()
        err = HttpResponseError(message="Forbidden")
        err.status_code = 403
        mgmt.apis.list.side_effect = err
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterAuthError):
            client.list_apis()

    def test_service_unavailable_raises_domain_error(self) -> None:
        mgmt = _mock_mgmt()
        err = HttpResponseError(message="Service Unavailable")
        err.status_code = 503
        mgmt.apis.list.side_effect = err
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterUnavailableError):
            client.list_apis()

    def test_generic_http_error_raises_client_error(self) -> None:
        mgmt = _mock_mgmt()
        err = HttpResponseError(message="Bad Request")
        err.status_code = 400
        mgmt.apis.list.side_effect = err
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterClientError) as exc_info:
            client.list_apis()
        assert exc_info.value.status_code == 400

    def test_unexpected_error_raises_client_error(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.apis.list.side_effect = RuntimeError("oops")
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterClientError):
            client.list_apis()


# ---------------------------------------------------------------------------
# get_api
# ---------------------------------------------------------------------------


class TestGetApi:
    def test_returns_single_api(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.apis.get.return_value = MOCK_APIS[0]
        client = _make_client(mgmt)

        result = client.get_api("petstore-api")

        assert result == MOCK_APIS[0]
        mgmt.apis.get.assert_called_once_with(
            resource_group_name="rg-test",
            service_name="apic-test",
            api_name="petstore-api",
        )

    def test_not_found_raises_domain_error(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.apis.get.side_effect = ResourceNotFoundError("not found")
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterNotFoundError):
            client.get_api("missing-api")


# ---------------------------------------------------------------------------
# list_api_versions
# ---------------------------------------------------------------------------


class TestListApiVersions:
    def test_returns_list(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.api_versions.list.return_value = iter(MOCK_VERSIONS)
        client = _make_client(mgmt)

        result = client.list_api_versions("petstore-api")

        assert result == MOCK_VERSIONS
        mgmt.api_versions.list.assert_called_once()

    def test_not_found_raises_domain_error(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.api_versions.list.side_effect = ResourceNotFoundError("not found")
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterNotFoundError):
            client.list_api_versions("missing-api")


# ---------------------------------------------------------------------------
# list_api_definitions
# ---------------------------------------------------------------------------


class TestListApiDefinitions:
    def test_returns_list(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.api_definitions.list.return_value = iter(MOCK_API_DEFINITIONS)
        client = _make_client(mgmt)

        result = client.list_api_definitions("petstore-api", "v1")

        assert result == MOCK_API_DEFINITIONS
        mgmt.api_definitions.list.assert_called_once_with(
            resource_group_name="rg-test",
            service_name="apic-test",
            api_name="petstore-api",
            version_name="v1",
        )


# ---------------------------------------------------------------------------
# export_api_specification
# ---------------------------------------------------------------------------


class TestExportApiSpecification:
    def test_returns_spec_content(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.api_definitions.export_specification.return_value = SimpleNamespace(value=MOCK_SPEC_CONTENT)
        client = _make_client(mgmt)

        result = client.export_api_specification("petstore-api", "v1", "openapi")

        assert result == MOCK_SPEC_CONTENT

    def test_returns_none_when_empty(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.api_definitions.export_specification.return_value = SimpleNamespace(value=None)
        client = _make_client(mgmt)

        result = client.export_api_specification("petstore-api", "v1", "openapi")

        assert result is None

    def test_returns_none_when_result_is_none(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.api_definitions.export_specification.return_value = None
        client = _make_client(mgmt)

        result = client.export_api_specification("petstore-api", "v1", "openapi")

        assert result is None


# ---------------------------------------------------------------------------
# list_environments
# ---------------------------------------------------------------------------


class TestListEnvironments:
    def test_returns_list(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.environments.list.return_value = iter(MOCK_ENVIRONMENTS)
        client = _make_client(mgmt)

        result = client.list_environments()

        assert result == MOCK_ENVIRONMENTS
        mgmt.environments.list.assert_called_once_with(
            resource_group_name="rg-test",
            service_name="apic-test",
        )

    def test_not_found_raises_domain_error(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.environments.list.side_effect = ResourceNotFoundError("not found")
        client = _make_client(mgmt)

        with pytest.raises(ApiCenterNotFoundError):
            client.list_environments()


# ---------------------------------------------------------------------------
# list_deployments
# ---------------------------------------------------------------------------


class TestListDeployments:
    def test_returns_list(self) -> None:
        mgmt = _mock_mgmt()
        mgmt.deployments.list.return_value = iter(MOCK_DEPLOYMENTS)
        client = _make_client(mgmt)

        result = client.list_deployments("petstore-api")

        assert result == MOCK_DEPLOYMENTS
        mgmt.deployments.list.assert_called_once_with(
            resource_group_name="rg-test",
            service_name="apic-test",
            api_name="petstore-api",
        )


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_clears_mgmt_client(self) -> None:
        mgmt = _mock_mgmt()
        client = _make_client(mgmt)

        client.close()

        mgmt.close.assert_called_once()
        assert client._mgmt_client is None

    def test_close_is_idempotent(self) -> None:
        client = ApiCenterClient(
            subscription_id="sub",
            resource_group="rg",
            service_name="svc",
            credential=MagicMock(),
        )
        client.close()  # No mgmt client created, should not raise
        client.close()  # Second call also safe
