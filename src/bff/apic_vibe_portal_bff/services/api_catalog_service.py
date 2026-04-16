"""API catalog service — business logic for API discovery operations.

Orchestrates calls to :class:`ApiCenterClient`, applies the data mapper, and
caches results using a :class:`~apic_vibe_portal_bff.utils.cache.CacheBackend`
implementation (Redis in production, in-memory fallback for local development).
"""

from __future__ import annotations

import logging
import math

from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
from apic_vibe_portal_bff.clients.api_center_mapper import (
    map_api_definition,
    map_api_specification,
    map_api_version,
    map_deployment,
    map_environment,
)
from apic_vibe_portal_bff.models.api_center import (
    ApiDefinition,
    ApiDeployment,
    ApiEnvironment,
    ApiSpecification,
    ApiVersion,
    PaginatedResponse,
    PaginationMeta,
)
from apic_vibe_portal_bff.utils.cache import CacheBackend, InMemoryCache

logger = logging.getLogger(__name__)

# Cache key prefixes
_KEY_APIS = "apis:"
_KEY_API = "api:"
_KEY_VERSIONS = "versions:"
_KEY_SPEC = "spec:"
_KEY_ENVS = "environments"
_KEY_DEPLOYMENTS = "deployments:"

# Default TTLs (seconds)
_TTL_API_LIST = 120  # 2 minutes
_TTL_API_DETAIL = 300  # 5 minutes
_TTL_SPEC = 600  # 10 minutes
_TTL_ENV = 900  # 15 minutes
_TTL_DEPLOYMENTS = 900  # 15 minutes


class ApiCatalogService:
    """High-level service for the API catalog.

    Parameters
    ----------
    client:
        :class:`ApiCenterClient` instance used to communicate with Azure
        API Center.
    cache:
        Cache backend to use.  Pass a :class:`RedisCacheBackend` in
        production; defaults to :class:`InMemoryCache` (suitable for local
        development and single-instance deployments).
    cache_ttl_seconds:
        Default cache TTL used when *cache* is ``None`` and an
        :class:`InMemoryCache` is created automatically.
    """

    def __init__(
        self,
        client: ApiCenterClient,
        cache: CacheBackend | None = None,
        cache_ttl_seconds: float = 300.0,
    ) -> None:
        self._client = client
        self._cache: CacheBackend = (
            cache if cache is not None else InMemoryCache(default_ttl_seconds=cache_ttl_seconds)
        )

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------

    def list_apis(
        self,
        page: int = 1,
        page_size: int = 20,
        filter_str: str | None = None,
    ) -> PaginatedResponse:
        """Return a paginated list of API definitions.

        Parameters
        ----------
        page:
            1-based page number.
        page_size:
            Number of items per page.
        filter_str:
            Optional OData filter to pass to API Center.
        """
        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if page_size < 1:
            raise ValueError(f"page_size must be >= 1, got {page_size}")

        cache_key = f"{_KEY_APIS}{filter_str or ''}:{page}:{page_size}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("list_apis cache hit", extra={"key": cache_key})
            return cached  # type: ignore[return-value]

        raw_apis = self._client.list_apis(filter_str=filter_str)

        # Apply in-process pagination (API Center SDK lists all items)
        total_count = len(raw_apis)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0
        start = (page - 1) * page_size
        end = start + page_size
        page_items = raw_apis[start:end]

        definitions = [map_api_definition(raw) for raw in page_items]

        result = PaginatedResponse(
            items=definitions,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_count=total_count,
                total_pages=total_pages,
            ),
        )
        self._cache.set(cache_key, result, ttl_seconds=_TTL_API_LIST)
        return result

    def get_api(self, api_name: str, include_versions: bool = True, include_deployments: bool = True) -> ApiDefinition:
        """Return a single API definition with optional versions and deployments.

        Parameters
        ----------
        api_name:
            The API Center API name (not the display title).
        include_versions:
            When ``True``, fetch and embed version objects.
        include_deployments:
            When ``True``, fetch and embed deployment objects.
        """
        cache_key = f"{_KEY_API}{api_name}:{include_versions}:{include_deployments}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("get_api cache hit", extra={"key": cache_key})
            return cached  # type: ignore[return-value]

        raw = self._client.get_api(api_name)

        versions: list[ApiVersion] = []
        if include_versions:
            versions = self.list_api_versions(api_name)

        deployments: list[ApiDeployment] = []
        if include_deployments:
            deployments = self.list_deployments(api_name)

        definition = map_api_definition(raw, versions=versions, deployments=deployments)
        self._cache.set(cache_key, definition, ttl_seconds=_TTL_API_DETAIL)
        return definition

    def list_api_versions(self, api_name: str) -> list[ApiVersion]:
        """Return all versions for the given API."""
        cache_key = f"{_KEY_VERSIONS}{api_name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("list_api_versions cache hit", extra={"key": cache_key})
            return cached  # type: ignore[return-value]

        raw_versions = self._client.list_api_versions(api_name)
        versions = [map_api_version(v) for v in raw_versions]
        self._cache.set(cache_key, versions, ttl_seconds=_TTL_API_DETAIL)
        return versions

    def get_api_definition(
        self,
        api_name: str,
        version_name: str,
        definition_name: str | None = None,
    ) -> ApiSpecification:
        """Return an API specification document.

        If *definition_name* is ``None``, the first available definition for
        the version is used.

        Parameters
        ----------
        api_name:
            API Center API name.
        version_name:
            Version name.
        definition_name:
            Optional definition name; defaults to the first available.
        """
        cache_key = f"{_KEY_SPEC}{api_name}:{version_name}:{definition_name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("get_api_definition cache hit", extra={"key": cache_key})
            return cached  # type: ignore[return-value]

        raw_defs = self._client.list_api_definitions(api_name, version_name)
        if not raw_defs:
            from apic_vibe_portal_bff.clients.api_center_client import ApiCenterNotFoundError

            raise ApiCenterNotFoundError(f"No definitions found for api/{api_name}/versions/{version_name}")

        def _get_name(obj: object) -> str:
            """Extract the ``name`` attribute from an SDK object or dict."""
            if isinstance(obj, dict):
                return obj.get("name") or ""
            return getattr(obj, "name", None) or ""

        # Resolve target definition
        if definition_name is None:
            target_raw = raw_defs[0]
        else:
            target_raw = next((d for d in raw_defs if _get_name(d) == definition_name), None)
            if target_raw is None:
                from apic_vibe_portal_bff.clients.api_center_client import ApiCenterNotFoundError

                raise ApiCenterNotFoundError(
                    f"Definition '{definition_name}' not found for api/{api_name}/versions/{version_name}"
                )

        resolved_name = _get_name(target_raw)
        content = self._client.export_api_specification(api_name, version_name, resolved_name)
        spec = map_api_specification(target_raw, content=content)
        self._cache.set(cache_key, spec, ttl_seconds=_TTL_SPEC)
        return spec

    def list_environments(self) -> list[ApiEnvironment]:
        """Return all deployment environments."""
        cached = self._cache.get(_KEY_ENVS)
        if cached is not None:
            logger.debug("list_environments cache hit")
            return cached  # type: ignore[return-value]

        raw_envs = self._client.list_environments()
        environments = [map_environment(e) for e in raw_envs]
        self._cache.set(_KEY_ENVS, environments, ttl_seconds=_TTL_ENV)
        return environments

    def list_deployments(self, api_name: str) -> list[ApiDeployment]:
        """Return all deployments for the given API."""
        cache_key = f"{_KEY_DEPLOYMENTS}{api_name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("list_deployments cache hit", extra={"key": cache_key})
            return cached  # type: ignore[return-value]

        raw_deps = self._client.list_deployments(api_name)
        deployments = [map_deployment(d) for d in raw_deps]
        self._cache.set(cache_key, deployments, ttl_seconds=_TTL_DEPLOYMENTS)
        return deployments

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate_api(self, api_name: str) -> None:
        """Invalidate all cache entries related to a specific API."""
        self._cache.invalidate_prefix(f"{_KEY_API}{api_name}")
        self._cache.invalidate_prefix(f"{_KEY_VERSIONS}{api_name}")
        self._cache.invalidate_prefix(f"{_KEY_SPEC}{api_name}")
        self._cache.invalidate_prefix(f"{_KEY_DEPLOYMENTS}{api_name}")
        # Also bust the list cache so new APIs appear
        self._cache.invalidate_prefix(_KEY_APIS)

    def clear_cache(self) -> None:
        """Evict all cached data."""
        self._cache.clear()
