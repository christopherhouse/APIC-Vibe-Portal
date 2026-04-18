"""API catalog service — business logic for API discovery operations.

Orchestrates calls to :class:`ApiCenterClient`, applies the data mapper, and
caches results using a :class:`~apic_vibe_portal_bff.utils.cache.CacheBackend`
implementation (Redis in production, in-memory fallback for local development).

Implements **stale-while-revalidate** caching: when a cached value is still
valid but within the last 20 % of its TTL, the value is returned immediately
to the caller while a background thread refreshes the cache entry.  This
keeps user-facing latency low and avoids periodic cache nuking.
"""

from __future__ import annotations

import logging
import math
import threading
from collections.abc import Callable
from typing import Any

from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient, ApiCenterNotFoundError
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
        self._cache: CacheBackend = cache if cache is not None else InMemoryCache(default_ttl_seconds=cache_ttl_seconds)
        # Tracks keys that already have a background refresh in flight to
        # avoid spawning duplicate threads for the same key.
        self._refreshing: set[str] = set()
        self._refresh_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Background refresh helper
    # ------------------------------------------------------------------

    def _schedule_refresh(self, cache_key: str, refresh_fn: Callable[[], Any], ttl: float) -> None:
        """Fire a background daemon thread to refresh *cache_key*.

        If a refresh for this key is already in-flight the call is a no-op.
        """
        with self._refresh_lock:
            if cache_key in self._refreshing:
                return
            self._refreshing.add(cache_key)

        def _do_refresh() -> None:
            try:
                value = refresh_fn()
                self._cache.set(cache_key, value, ttl_seconds=ttl)
                logger.debug("Background cache refresh complete", extra={"key": cache_key})
            except Exception:  # noqa: BLE001
                logger.warning("Background cache refresh failed", extra={"key": cache_key}, exc_info=True)
            finally:
                with self._refresh_lock:
                    self._refreshing.discard(cache_key)

        thread = threading.Thread(target=_do_refresh, daemon=True, name=f"cache-refresh:{cache_key}")
        thread.start()

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------

    def list_apis(
        self,
        page: int = 1,
        page_size: int = 20,
        filter_str: str | None = None,
        sort_field: str | None = None,
        sort_reverse: bool = False,
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
        sort_field:
            Attribute name on :class:`ApiDefinition` to sort by
            (e.g. ``"name"``, ``"updated_at"``).  ``None`` keeps the
            order returned by the API Center SDK.
        sort_reverse:
            When ``True``, sort in descending order.
        """
        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if page_size < 1:
            raise ValueError(f"page_size must be >= 1, got {page_size}")

        cache_key = f"{_KEY_APIS}{filter_str or ''}:{sort_field}:{sort_reverse}:{page}:{page_size}"
        hit = self._cache.get_with_staleness(cache_key, _TTL_API_LIST)
        if hit.value is not None:
            logger.debug("list_apis cache hit", extra={"key": cache_key, "needs_refresh": hit.needs_refresh})
            if hit.needs_refresh:
                self._schedule_refresh(
                    cache_key,
                    lambda: self._fetch_api_list(filter_str, sort_field, sort_reverse, page, page_size),
                    _TTL_API_LIST,
                )
            return hit.value  # type: ignore[return-value]

        result = self._fetch_api_list(filter_str, sort_field, sort_reverse, page, page_size)
        self._cache.set(cache_key, result, ttl_seconds=_TTL_API_LIST)
        return result

    def _fetch_api_list(
        self,
        filter_str: str | None,
        sort_field: str | None,
        sort_reverse: bool,
        page: int,
        page_size: int,
    ) -> PaginatedResponse:
        """Fetch the API list from APIC and build a paginated response."""
        raw_apis = self._client.list_apis(filter_str=filter_str)
        definitions = [map_api_definition(raw) for raw in raw_apis]

        if sort_field is not None:
            definitions.sort(key=lambda x: getattr(x, sort_field, ""), reverse=sort_reverse)

        total_count = len(definitions)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0
        start = (page - 1) * page_size
        end = start + page_size
        page_items = definitions[start:end]

        return PaginatedResponse(
            items=page_items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_count=total_count,
                total_pages=total_pages,
            ),
        )

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
        hit = self._cache.get_with_staleness(cache_key, _TTL_API_DETAIL)
        if hit.value is not None:
            logger.debug("get_api cache hit", extra={"key": cache_key, "needs_refresh": hit.needs_refresh})
            if hit.needs_refresh:
                self._schedule_refresh(
                    cache_key,
                    lambda: self._fetch_api(api_name, include_versions, include_deployments),
                    _TTL_API_DETAIL,
                )
            return hit.value  # type: ignore[return-value]

        definition = self._fetch_api(api_name, include_versions, include_deployments)
        self._cache.set(cache_key, definition, ttl_seconds=_TTL_API_DETAIL)
        return definition

    def _fetch_api(self, api_name: str, include_versions: bool, include_deployments: bool) -> ApiDefinition:
        """Fetch a single API from APIC with optional sub-resources."""
        raw = self._client.get_api(api_name)

        versions: list[ApiVersion] = []
        if include_versions:
            versions = self.list_api_versions(api_name)

        deployments: list[ApiDeployment] = []
        if include_deployments:
            deployments = self.list_deployments(api_name)

        return map_api_definition(raw, versions=versions, deployments=deployments)

    def list_api_versions(self, api_name: str) -> list[ApiVersion]:
        """Return all versions for the given API."""
        cache_key = f"{_KEY_VERSIONS}{api_name}"
        hit = self._cache.get_with_staleness(cache_key, _TTL_API_DETAIL)
        if hit.value is not None:
            logger.debug("list_api_versions cache hit", extra={"key": cache_key, "needs_refresh": hit.needs_refresh})
            if hit.needs_refresh:
                self._schedule_refresh(
                    cache_key,
                    lambda: self._fetch_versions(api_name),
                    _TTL_API_DETAIL,
                )
            return hit.value  # type: ignore[return-value]

        versions = self._fetch_versions(api_name)
        self._cache.set(cache_key, versions, ttl_seconds=_TTL_API_DETAIL)
        return versions

    def _fetch_versions(self, api_name: str) -> list[ApiVersion]:
        raw_versions = self._client.list_api_versions(api_name)
        return [map_api_version(v) for v in raw_versions]

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
        hit = self._cache.get_with_staleness(cache_key, _TTL_SPEC)
        if hit.value is not None:
            logger.debug("get_api_definition cache hit", extra={"key": cache_key, "needs_refresh": hit.needs_refresh})
            if hit.needs_refresh:
                self._schedule_refresh(
                    cache_key,
                    lambda: self._fetch_spec(api_name, version_name, definition_name),
                    _TTL_SPEC,
                )
            return hit.value  # type: ignore[return-value]

        spec = self._fetch_spec(api_name, version_name, definition_name)
        self._cache.set(cache_key, spec, ttl_seconds=_TTL_SPEC)
        return spec

    def _fetch_spec(self, api_name: str, version_name: str, definition_name: str | None) -> ApiSpecification:
        raw_defs = self._client.list_api_definitions(api_name, version_name)
        if not raw_defs:
            raise ApiCenterNotFoundError(f"No definitions found for api/{api_name}/versions/{version_name}")

        def _get_name(obj: object) -> str:
            if isinstance(obj, dict):
                return obj.get("name") or ""
            return getattr(obj, "name", None) or ""

        if definition_name is None:
            target_raw = raw_defs[0]
        else:
            target_raw = next((d for d in raw_defs if _get_name(d) == definition_name), None)
            if target_raw is None:
                raise ApiCenterNotFoundError(
                    f"Definition '{definition_name}' not found for api/{api_name}/versions/{version_name}"
                )

        resolved_name = _get_name(target_raw)
        content = self._client.export_api_specification(api_name, version_name, resolved_name)
        return map_api_specification(target_raw, content=content)

    def list_environments(self) -> list[ApiEnvironment]:
        """Return all deployment environments."""
        hit = self._cache.get_with_staleness(_KEY_ENVS, _TTL_ENV)
        if hit.value is not None:
            logger.debug("list_environments cache hit", extra={"needs_refresh": hit.needs_refresh})
            if hit.needs_refresh:
                self._schedule_refresh(
                    _KEY_ENVS,
                    self._fetch_environments,
                    _TTL_ENV,
                )
            return hit.value  # type: ignore[return-value]

        environments = self._fetch_environments()
        self._cache.set(_KEY_ENVS, environments, ttl_seconds=_TTL_ENV)
        return environments

    def _fetch_environments(self) -> list[ApiEnvironment]:
        raw_envs = self._client.list_environments()
        return [map_environment(e) for e in raw_envs]

    def list_deployments(self, api_name: str) -> list[ApiDeployment]:
        """Return all deployments for the given API."""
        cache_key = f"{_KEY_DEPLOYMENTS}{api_name}"
        hit = self._cache.get_with_staleness(cache_key, _TTL_DEPLOYMENTS)
        if hit.value is not None:
            logger.debug("list_deployments cache hit", extra={"key": cache_key, "needs_refresh": hit.needs_refresh})
            if hit.needs_refresh:
                self._schedule_refresh(
                    cache_key,
                    lambda: self._fetch_deployments(api_name),
                    _TTL_DEPLOYMENTS,
                )
            return hit.value  # type: ignore[return-value]

        deployments = self._fetch_deployments(api_name)
        self._cache.set(cache_key, deployments, ttl_seconds=_TTL_DEPLOYMENTS)
        return deployments

    def _fetch_deployments(self, api_name: str) -> list[ApiDeployment]:
        raw_deps = self._client.list_deployments(api_name)
        return [map_deployment(d) for d in raw_deps]

    # ------------------------------------------------------------------
    # Cache warming
    # ------------------------------------------------------------------

    def warm_cache(self, page_size: int = 20) -> int:
        """Pre-populate the cache with fresh catalog data from APIC.

        Fetches all pages of the API list and environments.  Unlike a
        periodic nuke-and-refill, this only writes new entries; existing
        entries that are still fresh are overwritten with updated data.

        This method is intended to be called once at BFF startup so that
        the first user requests hit a warm cache.  Ongoing freshness is
        maintained by the stale-while-revalidate logic in each public
        method.

        Parameters
        ----------
        page_size:
            Items per page to warm.  Must match the ``pageSize`` used by
            the frontend so that user requests hit the cache.  Defaults to
            20 (the API catalog router default).

        Returns the total number of distinct API records fetched.
        """
        # Bust list and environments caches so the next call hits APIC.
        self._cache.invalidate_prefix(_KEY_APIS)
        self._cache.invalidate_prefix(_KEY_ENVS)

        # Warm page 1 to discover the total count, then warm remaining pages.
        first = self.list_apis(page=1, page_size=page_size)
        total = first.pagination.total_count
        total_pages = first.pagination.total_pages

        for page in range(2, total_pages + 1):
            self.list_apis(page=page, page_size=page_size)

        logger.info(
            "warm_cache: API list cached",
            extra={"total": total, "pages": total_pages, "page_size": page_size},
        )

        try:
            self.list_environments()
            logger.debug("warm_cache: environments cached")
        except Exception:  # noqa: BLE001
            logger.warning("warm_cache: failed to pre-cache environments")

        return total

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
