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


# ---------------------------------------------------------------------------
# warm_cache
# ---------------------------------------------------------------------------


class TestWarmCache:
    def test_returns_api_count(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        count = service.warm_cache()

        assert count == len(MOCK_APIS)

    def test_always_fetches_from_apic_even_when_cache_is_warm(self) -> None:
        """warm_cache must bypass an existing warm list cache."""
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        # First call warms the cache via normal list_apis path
        service.list_apis()
        assert mock_client.list_apis.call_count == 1

        # warm_cache should bust the list cache and fetch again
        service.warm_cache()
        assert mock_client.list_apis.call_count == 2

    def test_warms_environments_cache(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        service.warm_cache()

        # environments should now be cached — second call must not hit client
        mock_client.reset_mock()
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS
        service.list_environments()
        mock_client.list_environments.assert_not_called()

    def test_subsequent_list_apis_uses_warmed_cache(self) -> None:
        """After warm_cache, a normal list_apis call must hit the cache."""
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        service.warm_cache()
        mock_client.reset_mock()
        mock_client.list_apis.return_value = MOCK_APIS

        service.list_apis()

        mock_client.list_apis.assert_not_called()

    def test_environments_failure_does_not_raise(self) -> None:
        """A failure warming environments must not propagate."""
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS
        mock_client.list_environments.side_effect = RuntimeError("APIC unavailable")

        # Should complete without raising
        count = service.warm_cache()

        assert count == len(MOCK_APIS)

    def test_custom_page_size_forwarded(self) -> None:
        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS
        mock_client.list_environments.return_value = MOCK_ENVIRONMENTS

        service.warm_cache(page_size=50)

        mock_client.list_apis.assert_called_once()

    def test_busts_previously_cached_list(self) -> None:
        """Verifies that a stale (deleted-API) list is replaced on warm."""
        from tests.api_center_mocks import make_api

        service, mock_client = _make_service()
        # Seed cache with 3 APIs
        three_apis = [make_api(name=f"api-{i}") for i in range(3)]
        mock_client.list_apis.return_value = three_apis
        mock_client.list_environments.return_value = []
        service.list_apis()

        # APIC now only has 2 APIs (one was deleted)
        two_apis = three_apis[:2]
        mock_client.list_apis.return_value = two_apis
        service.warm_cache()

        # The fresh result should reflect the deletion
        mock_client.reset_mock()
        mock_client.list_apis.return_value = two_apis
        result = service.list_apis()
        assert result.pagination.total_count == 2
        mock_client.list_apis.assert_not_called()  # served from warm cache


# ---------------------------------------------------------------------------
# Stale-while-revalidate
# ---------------------------------------------------------------------------


class TestStaleWhileRevalidate:
    def test_returns_stale_value_and_schedules_refresh(self) -> None:
        """When a cache entry is near expiry, the stale value is returned
        and a background refresh is scheduled."""
        import time

        from apic_vibe_portal_bff.utils.cache import InMemoryCache

        cache: InMemoryCache[object] = InMemoryCache(default_ttl_seconds=60.0)
        service, mock_client = _make_service()
        service._cache = cache
        mock_client.list_apis.return_value = MOCK_APIS

        # Seed with a very short TTL so it becomes "near expiry" quickly
        service.list_apis()
        assert mock_client.list_apis.call_count == 1

        # Manually expire the entry to near-expiry (set entry's expires_at
        # to be within the 20% threshold)
        for entry in cache._store.values():
            entry.expires_at = time.monotonic() + (entry.ttl_seconds * 0.1)

        # Next call should return stale value AND trigger background refresh
        result = service.list_apis()
        assert result.pagination.total_count == len(MOCK_APIS)

        # Give the background thread a moment to run
        time.sleep(0.1)

        # Background refresh should have called list_apis again
        assert mock_client.list_apis.call_count == 2

    def test_no_duplicate_refresh_threads(self) -> None:
        """Only one refresh thread should be spawned per key."""
        import time

        from apic_vibe_portal_bff.utils.cache import InMemoryCache

        cache: InMemoryCache[object] = InMemoryCache(default_ttl_seconds=60.0)
        service, mock_client = _make_service()
        service._cache = cache
        mock_client.list_apis.return_value = MOCK_APIS

        service.list_apis()

        # Make near-expiry
        for entry in cache._store.values():
            entry.expires_at = time.monotonic() + (entry.ttl_seconds * 0.1)

        # Call twice rapidly — should only spawn one refresh thread
        service.list_apis()
        service.list_apis()

        time.sleep(0.1)

        # Only 1 extra call (the background refresh), not 2
        assert mock_client.list_apis.call_count == 2

    def test_fresh_entry_does_not_trigger_refresh(self) -> None:
        """A fresh cache entry (well within TTL) should not spawn a refresh."""
        import time

        service, mock_client = _make_service()
        mock_client.list_apis.return_value = MOCK_APIS

        service.list_apis()
        assert mock_client.list_apis.call_count == 1

        # Second call — entry is still fresh
        service.list_apis()
        time.sleep(0.05)

        # No additional APIC call should have happened
        assert mock_client.list_apis.call_count == 1

    def test_background_refresh_failure_does_not_propagate(self) -> None:
        """If the background refresh fails, the stale value is still served."""
        import time

        from apic_vibe_portal_bff.utils.cache import InMemoryCache

        cache: InMemoryCache[object] = InMemoryCache(default_ttl_seconds=60.0)
        service, mock_client = _make_service()
        service._cache = cache
        mock_client.list_apis.return_value = MOCK_APIS

        service.list_apis()

        # Make near-expiry and make the next APIC call fail
        for entry in cache._store.values():
            entry.expires_at = time.monotonic() + (entry.ttl_seconds * 0.1)

        mock_client.list_apis.side_effect = RuntimeError("APIC down")

        # Should still return stale value without raising
        result = service.list_apis()
        assert result.pagination.total_count == len(MOCK_APIS)

        time.sleep(0.1)
        # Background thread ran but failed — no crash
