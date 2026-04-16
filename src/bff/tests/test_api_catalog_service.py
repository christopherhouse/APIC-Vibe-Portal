"""Unit tests for ApiCatalogService — caching and orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apic_vibe_portal_bff.clients.api_center_client import ApiCenterNotFoundError
from apic_vibe_portal_bff.services.api_catalog_service import ApiCatalogService
from tests.api_center_mocks import (
    MOCK_API_DEFINITIONS,
    MOCK_APIS,
    MOCK_DEPLOYMENTS,
    MOCK_ENVIRONMENTS,
    MOCK_SPEC_CONTENT,
    MOCK_VERSIONS,
)


def _make_service(mock_client: MagicMock | None = None) -> tuple[ApiCatalogService, MagicMock]:
    """Return a service wired to a mock client."""
    if mock_client is None:
        mock_client = MagicMock()
    service = ApiCatalogService(client=mock_client, cache_ttl_seconds=60.0)
    return service, mock_client


# ---------------------------------------------------------------------------
# list_apis
# ---------------------------------------------------------------------------


class TestListApis:
    def test_returns_paginated_result(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS

        result = service.list_apis()

        assert result.pagination.total_count == len(MOCK_APIS)
        assert len(result.items) == len(MOCK_APIS)

    def test_pagination_slices_correctly(self) -> None:
        # Create 5 mock APIs
        from tests.api_center_mocks import make_api

        raw_apis = [make_api(name=f"api-{i}") for i in range(5)]
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = raw_apis

        result = service.list_apis(page=2, page_size=2)

        assert result.pagination.page == 2
        assert result.pagination.page_size == 2
        assert result.pagination.total_count == 5
        assert result.pagination.total_pages == 3
        assert len(result.items) == 2  # items 3-4

    def test_result_is_cached_on_second_call(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS

        service.list_apis()
        service.list_apis()

        # SDK called only once
        mock_client.list_apis.assert_called_once()

    def test_different_filters_use_separate_cache_keys(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS

        service.list_apis(filter_str="kind eq 'rest'")
        service.list_apis(filter_str="kind eq 'graphql'")

        assert mock_client.list_apis.call_count == 2

    def test_empty_list_returns_zero_total_pages(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = []

        result = service.list_apis()

        assert result.pagination.total_count == 0
        assert result.pagination.total_pages == 0
        assert result.items == []

    def test_invalid_page_raises_value_error(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = []

        with pytest.raises(ValueError, match="page must be >= 1"):
            service.list_apis(page=0)

    def test_invalid_page_size_raises_value_error(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = []

        with pytest.raises(ValueError, match="page_size must be >= 1"):
            service.list_apis(page_size=0)

    def test_filter_forwarded_to_client(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = []

        service.list_apis(filter_str="properties/kind eq 'rest'")

        mock_client.list_apis.assert_called_once_with(filter_str="properties/kind eq 'rest'")


# ---------------------------------------------------------------------------
# get_api
# ---------------------------------------------------------------------------


class TestGetApi:
    def test_returns_api_definition(self) -> None:
        service, mock_client = _make_service()
        mock_client.get_api.return_value = MOCK_APIS[0]
        mock_client.list_api_versions.return_value = MOCK_VERSIONS
        mock_client.list_deployments.return_value = MOCK_DEPLOYMENTS

        result = service.get_api("petstore-api")

        assert result.name == "petstore-api"

    def test_versions_embedded_when_requested(self) -> None:
        service, mock_client = _make_service()
        mock_client.get_api.return_value = MOCK_APIS[0]
        mock_client.list_api_versions.return_value = MOCK_VERSIONS
        mock_client.list_deployments.return_value = []

        result = service.get_api("petstore-api", include_versions=True, include_deployments=False)

        assert len(result.versions) == len(MOCK_VERSIONS)
        mock_client.list_api_versions.assert_called_once()

    def test_versions_omitted_when_not_requested(self) -> None:
        service, mock_client = _make_service()
        mock_client.get_api.return_value = MOCK_APIS[0]
        mock_client.list_deployments.return_value = []

        result = service.get_api("petstore-api", include_versions=False, include_deployments=False)

        assert result.versions == []
        mock_client.list_api_versions.assert_not_called()

    def test_deployments_embedded_when_requested(self) -> None:
        service, mock_client = _make_service()
        mock_client.get_api.return_value = MOCK_APIS[0]
        mock_client.list_api_versions.return_value = []
        mock_client.list_deployments.return_value = MOCK_DEPLOYMENTS

        result = service.get_api("petstore-api", include_versions=False, include_deployments=True)

        assert len(result.deployments) == len(MOCK_DEPLOYMENTS)

    def test_result_is_cached(self) -> None:
        service, mock_client = _make_service()
        mock_client.get_api.return_value = MOCK_APIS[0]
        mock_client.list_api_versions.return_value = []
        mock_client.list_deployments.return_value = []

        service.get_api("petstore-api")
        service.get_api("petstore-api")

        mock_client.get_api.assert_called_once()

    def test_propagates_not_found_error(self) -> None:
        service, mock_client = _make_service()
        mock_client.get_api.side_effect = ApiCenterNotFoundError("api/missing")

        with pytest.raises(ApiCenterNotFoundError):
            service.get_api("missing")


# ---------------------------------------------------------------------------
# list_api_versions
# ---------------------------------------------------------------------------


class TestListApiVersions:
    def test_returns_versions(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_api_versions.return_value = MOCK_VERSIONS

        result = service.list_api_versions("petstore-api")

        assert len(result) == len(MOCK_VERSIONS)

    def test_versions_cached(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_api_versions.return_value = MOCK_VERSIONS

        service.list_api_versions("petstore-api")
        service.list_api_versions("petstore-api")

        mock_client.list_api_versions.assert_called_once()


# ---------------------------------------------------------------------------
# get_api_definition
# ---------------------------------------------------------------------------


class TestGetApiDefinition:
    def test_returns_first_definition_when_name_not_specified(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_api_definitions.return_value = MOCK_API_DEFINITIONS
        mock_client.export_api_specification.return_value = MOCK_SPEC_CONTENT

        result = service.get_api_definition("petstore-api", "v1")

        assert result.content == MOCK_SPEC_CONTENT

    def test_selects_definition_by_name(self) -> None:
        from tests.api_center_mocks import make_api_spec_definition

        defs = [
            make_api_spec_definition(name="openapi", title="OpenAPI"),
            make_api_spec_definition(name="asyncapi", title="AsyncAPI"),
        ]
        service, mock_client = _make_service()
        mock_client.list_api_definitions.return_value = defs
        mock_client.export_api_specification.return_value = "{}"

        result = service.get_api_definition("petstore-api", "v1", definition_name="asyncapi")

        assert result.name == "asyncapi"

    def test_raises_not_found_when_definition_name_not_matched(self) -> None:
        from tests.api_center_mocks import make_api_spec_definition

        service, mock_client = _make_service()
        mock_client.list_api_definitions.return_value = [
            make_api_spec_definition(name="openapi", title="OpenAPI"),
        ]

        with pytest.raises(ApiCenterNotFoundError):
            service.get_api_definition("petstore-api", "v1", definition_name="nonexistent")

    def test_raises_not_found_when_no_definitions(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_api_definitions.return_value = []

        with pytest.raises(ApiCenterNotFoundError):
            service.get_api_definition("petstore-api", "v1")

    def test_spec_cached(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_api_definitions.return_value = MOCK_API_DEFINITIONS
        mock_client.export_api_specification.return_value = MOCK_SPEC_CONTENT

        service.get_api_definition("petstore-api", "v1")
        service.get_api_definition("petstore-api", "v1")

        mock_client.list_api_definitions.assert_called_once()

    def test_content_none_when_export_returns_none(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_api_definitions.return_value = MOCK_API_DEFINITIONS
        mock_client.export_api_specification.return_value = None

        result = service.get_api_definition("petstore-api", "v1")

        assert result.content is None


# ---------------------------------------------------------------------------
# list_environments
# ---------------------------------------------------------------------------


class TestListEnvironments:
    def test_returns_environments(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        result = service.list_environments()

        assert len(result) == len(MOCK_ENVIRONMENTS)

    def test_environments_cached(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        service.list_environments()
        service.list_environments()

        mock_client.list_environments.assert_called_once()


# ---------------------------------------------------------------------------
# list_deployments
# ---------------------------------------------------------------------------


class TestListDeployments:
    def test_returns_deployments(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_deployments.return_value = MOCK_DEPLOYMENTS

        result = service.list_deployments("petstore-api")

        assert len(result) == len(MOCK_DEPLOYMENTS)

    def test_deployments_cached(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_deployments.return_value = MOCK_DEPLOYMENTS

        service.list_deployments("petstore-api")
        service.list_deployments("petstore-api")

        mock_client.list_deployments.assert_called_once()


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


class TestCacheInvalidation:
    def test_invalidate_api_busts_relevant_caches(self) -> None:
        service, mock_client = _make_service()
        mock_client.get_api.return_value = MOCK_APIS[0]
        mock_client.list_api_versions.return_value = MOCK_VERSIONS
        mock_client.list_deployments.return_value = MOCK_DEPLOYMENTS
        mock_client.list_apis.return_value = MOCK_APIS

        # Warm the caches
        service.list_apis()
        service.get_api("petstore-api")
        service.list_api_versions("petstore-api")
        service.list_deployments("petstore-api")

        # Invalidate
        service.invalidate_api("petstore-api")

        # Reset mocks so we can check new call counts
        mock_client.reset_mock()
        mock_client.get_api.return_value = MOCK_APIS[0]
        mock_client.list_api_versions.return_value = MOCK_VERSIONS
        mock_client.list_deployments.return_value = MOCK_DEPLOYMENTS
        mock_client.list_apis.return_value = MOCK_APIS

        # All caches should be cold
        service.list_apis()
        service.get_api("petstore-api")
        service.list_api_versions("petstore-api")
        service.list_deployments("petstore-api")

        assert mock_client.list_apis.call_count == 1
        assert mock_client.get_api.call_count == 1
        assert mock_client.list_api_versions.call_count == 1
        assert mock_client.list_deployments.call_count == 1

    def test_clear_cache_evicts_everything(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        # Warm caches
        service.list_apis()
        service.list_environments()

        service.clear_cache()

        mock_client.reset_mock()
        mock_client.list_apis.return_value = MOCK_APIS
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        service.list_apis()
        service.list_environments()

        assert mock_client.list_apis.call_count == 1
        assert mock_client.list_environments.call_count == 1
