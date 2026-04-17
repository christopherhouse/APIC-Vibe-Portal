"""Unit tests for ApiCenterClient (data-plane wrapper)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from apic_client.exceptions import (
    ApiCenterAuthError,
    ApiCenterClientError,
    ApiCenterNotFoundError,
    ApiCenterUnavailableError,
)

from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
from tests.api_center_mocks import (
    MOCK_API_DEFINITIONS,
    MOCK_APIS,
    MOCK_DEPLOYMENTS,
    MOCK_ENVIRONMENTS,
    MOCK_SPEC_CONTENT,
    MOCK_VERSIONS,
)


def _make_client(mock_dp: MagicMock) -> ApiCenterClient:
    """Return an ApiCenterClient whose _dp_client is pre-wired."""
    client = ApiCenterClient(
        base_url="https://myapic.data.eastus.azure-apicenter.ms",
        credential=MagicMock(),
    )
    client._dp_client = mock_dp
    return client


def _mock_dp() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# list_apis
# ---------------------------------------------------------------------------


class TestListApis:
    def test_returns_list_of_apis(self) -> None:
        dp = _mock_dp()
        dp.list_apis.return_value = MOCK_APIS
        client = _make_client(dp)

        result = client.list_apis()

        assert result == MOCK_APIS
        dp.list_apis.assert_called_once()

    def test_passes_filter_str_is_accepted(self) -> None:
        """filter_str is accepted for interface compat but ignored by data plane."""
        dp = _mock_dp()
        dp.list_apis.return_value = []
        client = _make_client(dp)

        client.list_apis(filter_str="properties/kind eq 'rest'")

        dp.list_apis.assert_called_once()

    def test_not_found_raises_domain_error(self) -> None:
        dp = _mock_dp()
        dp.list_apis.side_effect = ApiCenterNotFoundError("not found")
        client = _make_client(dp)

        with pytest.raises(ApiCenterNotFoundError):
            client.list_apis()

    def test_auth_error_raises_domain_error(self) -> None:
        dp = _mock_dp()
        dp.list_apis.side_effect = ApiCenterAuthError("Unauthorized")
        client = _make_client(dp)

        with pytest.raises(ApiCenterAuthError):
            client.list_apis()

    def test_forbidden_raises_auth_error(self) -> None:
        dp = _mock_dp()
        dp.list_apis.side_effect = ApiCenterAuthError("Forbidden")
        client = _make_client(dp)

        with pytest.raises(ApiCenterAuthError):
            client.list_apis()

    def test_service_unavailable_raises_domain_error(self) -> None:
        dp = _mock_dp()
        dp.list_apis.side_effect = ApiCenterUnavailableError("Service Unavailable")
        client = _make_client(dp)

        with pytest.raises(ApiCenterUnavailableError):
            client.list_apis()

    def test_generic_http_error_raises_client_error(self) -> None:
        dp = _mock_dp()
        dp.list_apis.side_effect = ApiCenterClientError("Bad Request", status_code=400)
        client = _make_client(dp)

        with pytest.raises(ApiCenterClientError) as exc_info:
            client.list_apis()
        assert exc_info.value.status_code == 400

    def test_unexpected_error_propagates(self) -> None:
        dp = _mock_dp()
        dp.list_apis.side_effect = RuntimeError("oops")
        client = _make_client(dp)

        with pytest.raises(RuntimeError):
            client.list_apis()


# ---------------------------------------------------------------------------
# get_api
# ---------------------------------------------------------------------------


class TestGetApi:
    def test_returns_single_api(self) -> None:
        dp = _mock_dp()
        dp.get_api.return_value = MOCK_APIS[0]
        client = _make_client(dp)

        result = client.get_api("petstore-api")

        assert result == MOCK_APIS[0]
        dp.get_api.assert_called_once_with("petstore-api")

    def test_not_found_raises_domain_error(self) -> None:
        dp = _mock_dp()
        dp.get_api.side_effect = ApiCenterNotFoundError("missing-api")
        client = _make_client(dp)

        with pytest.raises(ApiCenterNotFoundError):
            client.get_api("missing-api")


# ---------------------------------------------------------------------------
# list_api_versions
# ---------------------------------------------------------------------------


class TestListApiVersions:
    def test_returns_list(self) -> None:
        dp = _mock_dp()
        dp.list_api_versions.return_value = MOCK_VERSIONS
        client = _make_client(dp)

        result = client.list_api_versions("petstore-api")

        assert result == MOCK_VERSIONS
        dp.list_api_versions.assert_called_once_with("petstore-api")

    def test_not_found_raises_domain_error(self) -> None:
        dp = _mock_dp()
        dp.list_api_versions.side_effect = ApiCenterNotFoundError("missing-api")
        client = _make_client(dp)

        with pytest.raises(ApiCenterNotFoundError):
            client.list_api_versions("missing-api")


# ---------------------------------------------------------------------------
# list_api_definitions
# ---------------------------------------------------------------------------


class TestListApiDefinitions:
    def test_returns_list(self) -> None:
        dp = _mock_dp()
        dp.list_api_definitions.return_value = MOCK_API_DEFINITIONS
        client = _make_client(dp)

        result = client.list_api_definitions("petstore-api", "v1")

        assert result == MOCK_API_DEFINITIONS
        dp.list_api_definitions.assert_called_once_with("petstore-api", "v1")


# ---------------------------------------------------------------------------
# export_api_specification
# ---------------------------------------------------------------------------


class TestExportApiSpecification:
    def test_returns_spec_content(self) -> None:
        dp = _mock_dp()
        dp.export_api_specification.return_value = MOCK_SPEC_CONTENT
        client = _make_client(dp)

        result = client.export_api_specification("petstore-api", "v1", "openapi")

        assert result == MOCK_SPEC_CONTENT

    def test_returns_none_when_empty(self) -> None:
        dp = _mock_dp()
        dp.export_api_specification.return_value = None
        client = _make_client(dp)

        result = client.export_api_specification("petstore-api", "v1", "openapi")

        assert result is None


# ---------------------------------------------------------------------------
# list_environments
# ---------------------------------------------------------------------------


class TestListEnvironments:
    def test_returns_list(self) -> None:
        dp = _mock_dp()
        dp.list_environments.return_value = MOCK_ENVIRONMENTS
        client = _make_client(dp)

        result = client.list_environments()

        assert result == MOCK_ENVIRONMENTS
        dp.list_environments.assert_called_once()

    def test_not_found_raises_domain_error(self) -> None:
        dp = _mock_dp()
        dp.list_environments.side_effect = ApiCenterNotFoundError("environments")
        client = _make_client(dp)

        with pytest.raises(ApiCenterNotFoundError):
            client.list_environments()


# ---------------------------------------------------------------------------
# list_deployments
# ---------------------------------------------------------------------------


class TestListDeployments:
    def test_returns_list(self) -> None:
        dp = _mock_dp()
        dp.list_deployments.return_value = MOCK_DEPLOYMENTS
        client = _make_client(dp)

        result = client.list_deployments("petstore-api")

        assert result == MOCK_DEPLOYMENTS
        dp.list_deployments.assert_called_once_with("petstore-api")


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_delegates_to_dp_client(self) -> None:
        dp = _mock_dp()
        client = _make_client(dp)

        client.close()

        dp.close.assert_called_once()

    def test_close_is_idempotent(self) -> None:
        client = ApiCenterClient(
            base_url="https://myapic.data.eastus.azure-apicenter.ms",
            credential=MagicMock(),
        )
        client.close()
        client.close()
