"""API catalog endpoints.

Exposes Azure API Center data to the frontend via a consistent REST API.
All responses use a standard envelope with ``data`` and optional ``meta``
(pagination) keys.  Error responses use the ``ApiErrorResponse`` shape
directly (top-level ``{error: {code, message, details}}``).

Endpoints
---------
GET /api/catalog                                           — List APIs (paginated, filterable, sortable)
GET /api/catalog/{api_id}                                  — Get API details
GET /api/catalog/{api_id}/versions                         — List API versions
GET /api/catalog/{api_id}/versions/{version_id}/definition — Get API specification
GET /api/catalog/{api_id}/deployments                      — List API deployments
GET /api/environments                                      — List environments
"""

from __future__ import annotations

import logging
import time
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from apic_vibe_portal_bff.clients.api_center_client import (
    ApiCenterClientError,
    ApiCenterNotFoundError,
)
from apic_vibe_portal_bff.middleware.rbac import require_any_role
from apic_vibe_portal_bff.models.api_center import (
    ApiDefinition,
    ApiDeployment,
    ApiEnvironment,
    ApiKind,
    ApiLifecycle,
    ApiSpecification,
    ApiVersion,
)
from apic_vibe_portal_bff.services.api_catalog_service import ApiCatalogService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service dependency — lazily created once per process
# ---------------------------------------------------------------------------

_service_instance: ApiCatalogService | None = None


def _get_service() -> ApiCatalogService:
    """Return a shared :class:`ApiCatalogService` instance.

    In production the service is created once with real Azure credentials.
    When ``REDIS_HOST`` is configured, the service uses
    :class:`RedisCacheBackend` for shared caching across replicas;
    otherwise it falls back to :class:`InMemoryCache`.
    Tests override this dependency via ``app.dependency_overrides``.
    """
    global _service_instance  # noqa: PLW0603
    if _service_instance is None:
        from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
        from apic_vibe_portal_bff.config.settings import get_settings
        from apic_vibe_portal_bff.utils.cache import CacheBackend

        settings = get_settings()
        client = ApiCenterClient(
            base_url=settings.api_center_endpoint,
            workspace_name=settings.api_center_workspace_name,
        )

        cache: CacheBackend | None = None
        if settings.redis_host:
            from apic_vibe_portal_bff.clients.redis_cache_client import RedisCacheBackend

            cache = RedisCacheBackend(
                host=settings.redis_host,
                port=settings.redis_port,
                default_ttl_seconds=settings.cache_ttl_seconds,
            )
            logger.info(
                "Using Redis cache backend",
                extra={"host": settings.redis_host, "port": settings.redis_port},
            )

        _service_instance = ApiCatalogService(
            client=client,
            cache=cache,
            cache_ttl_seconds=settings.cache_ttl_seconds,
        )
    return _service_instance


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SortField(StrEnum):
    """Sortable fields for the API catalog list."""

    NAME = "name"
    UPDATED_AT = "updatedAt"
    CREATED_AT = "createdAt"


class SortDirection(StrEnum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


class PaginationMetaOut(BaseModel):
    """Pagination metadata included in list responses.

    Uses camelCase aliases for the JSON contract while keeping snake_case
    field names in Python.  Not to be confused with
    :class:`~apic_vibe_portal_bff.models.api_center.PaginationMeta` which
    is the internal model used by the service layer.
    """

    page: int
    page_size: int = Field(alias="pageSize")
    total_count: int = Field(alias="totalCount")
    total_pages: int = Field(alias="totalPages")

    model_config = {"populate_by_name": True}


class ApiResponse[T](BaseModel):
    """Standard response envelope for all successful responses."""

    data: T
    meta: PaginationMetaOut | None = None


class ErrorDetail(BaseModel):
    """Structured error detail."""

    code: str
    message: str
    details: Any | None = None


class ApiErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail


# ---------------------------------------------------------------------------
# Custom exception for structured error responses
# ---------------------------------------------------------------------------


class CatalogApiError(Exception):
    """Raised by route handlers to produce a structured error response.

    The companion exception handler (registered in ``app.py``) serialises
    this into ``{"error": {"code": …, "message": …, "details": …}}``.
    """

    def __init__(self, status_code: int, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def catalog_api_error_handler(_request: object, exc: CatalogApiError) -> JSONResponse:
    """Serialize :class:`CatalogApiError` into an ``ApiErrorResponse`` envelope."""
    body = ApiErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_ROLES = ["Portal.User", "Portal.Admin", "Portal.Maintainer"]

# Maps the API-facing sort field enum to the ApiDefinition model attribute.
_SORT_FIELD_MAP: dict[SortField, str] = {
    SortField.NAME: "name",
    SortField.UPDATED_AT: "updated_at",
    SortField.CREATED_AT: "created_at",
}


def _build_filter(
    lifecycle: ApiLifecycle | None,
    kind: ApiKind | None,
) -> str | None:
    """Build an OData filter expression from query parameters."""
    parts: list[str] = []
    if lifecycle is not None:
        parts.append(f"properties/lifecycleStage eq '{lifecycle.value}'")
    if kind is not None:
        parts.append(f"properties/kind eq '{kind.value}'")
    return " and ".join(parts) if parts else None


def _raise_error(status_code: int, code: str, message: str, details: Any | None = None) -> None:
    """Raise a :class:`CatalogApiError` with a structured error body."""
    raise CatalogApiError(status_code=status_code, code=code, message=message, details=details)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["catalog"])


@router.get(
    "/api/catalog",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def list_apis(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),  # noqa: B008
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize", description="Items per page (max 100)"),  # noqa: B008
    sort: SortField | None = Query(default=None, description="Sort field"),  # noqa: B008
    direction: SortDirection = Query(default=SortDirection.ASC, description="Sort direction"),  # noqa: B008
    lifecycle: ApiLifecycle | None = Query(default=None, description="Filter by lifecycle stage"),  # noqa: B008
    kind: ApiKind | None = Query(default=None, description="Filter by API kind"),  # noqa: B008
    service: ApiCatalogService = Depends(_get_service),  # noqa: B008
) -> ApiResponse[list[ApiDefinition]]:
    """List APIs from the catalog with pagination, filtering, and sorting."""
    start = time.monotonic()
    try:
        filter_str = _build_filter(lifecycle, kind)
        sort_attr = _SORT_FIELD_MAP[sort] if sort is not None else None
        result = service.list_apis(
            page=page,
            page_size=page_size,
            filter_str=filter_str,
            sort_field=sort_attr,
            sort_reverse=(direction == SortDirection.DESC),
        )
        meta = PaginationMetaOut(
            page=result.pagination.page,
            pageSize=result.pagination.page_size,
            totalCount=result.pagination.total_count,
            totalPages=result.pagination.total_pages,
        )
        return ApiResponse(data=result.items, meta=meta)
    except ApiCenterClientError as exc:
        logger.error("list_apis failed", extra={"error": str(exc)})
        _raise_error(exc.status_code or 500, "CATALOG_ERROR", str(exc))
    finally:
        elapsed = time.monotonic() - start
        logger.info("api_response_time", extra={"endpoint": "list_apis", "duration_ms": round(elapsed * 1000, 2)})


@router.get(
    "/api/catalog/{api_id}",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def get_api(
    api_id: str,
    service: ApiCatalogService = Depends(_get_service),  # noqa: B008
) -> ApiResponse[ApiDefinition]:
    """Get detailed information for a specific API."""
    start = time.monotonic()
    try:
        definition = service.get_api(api_id)
        return ApiResponse(data=definition)
    except ApiCenterNotFoundError:
        _raise_error(404, "NOT_FOUND", f"API '{api_id}' not found")
    except ApiCenterClientError as exc:
        logger.error("get_api failed", extra={"api_id": api_id, "error": str(exc)})
        _raise_error(exc.status_code or 500, "CATALOG_ERROR", str(exc))
    finally:
        elapsed = time.monotonic() - start
        logger.info("api_response_time", extra={"endpoint": "get_api", "duration_ms": round(elapsed * 1000, 2)})


@router.get(
    "/api/catalog/{api_id}/versions",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def list_api_versions(
    api_id: str,
    service: ApiCatalogService = Depends(_get_service),  # noqa: B008
) -> ApiResponse[list[ApiVersion]]:
    """List all versions for a specific API."""
    start = time.monotonic()
    try:
        versions = service.list_api_versions(api_id)
        return ApiResponse(data=versions)
    except ApiCenterNotFoundError:
        _raise_error(404, "NOT_FOUND", f"API '{api_id}' not found")
    except ApiCenterClientError as exc:
        logger.error("list_api_versions failed", extra={"api_id": api_id, "error": str(exc)})
        _raise_error(exc.status_code or 500, "CATALOG_ERROR", str(exc))
    finally:
        elapsed = time.monotonic() - start
        logger.info(
            "api_response_time", extra={"endpoint": "list_api_versions", "duration_ms": round(elapsed * 1000, 2)}
        )


@router.get(
    "/api/catalog/{api_id}/versions/{version_id}/definition",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def get_api_definition(
    api_id: str,
    version_id: str,
    service: ApiCatalogService = Depends(_get_service),  # noqa: B008
) -> ApiResponse[ApiSpecification]:
    """Get the API specification document for a specific version."""
    start = time.monotonic()
    try:
        spec = service.get_api_definition(api_id, version_id)
        return ApiResponse(data=spec)
    except ApiCenterNotFoundError:
        _raise_error(
            404,
            "NOT_FOUND",
            f"Definition not found for API '{api_id}' version '{version_id}'",
        )
    except ApiCenterClientError as exc:
        logger.error(
            "get_api_definition failed",
            extra={"api_id": api_id, "version_id": version_id, "error": str(exc)},
        )
        _raise_error(exc.status_code or 500, "CATALOG_ERROR", str(exc))
    finally:
        elapsed = time.monotonic() - start
        logger.info(
            "api_response_time", extra={"endpoint": "get_api_definition", "duration_ms": round(elapsed * 1000, 2)}
        )


@router.get(
    "/api/catalog/{api_id}/deployments",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def list_api_deployments(
    api_id: str,
    service: ApiCatalogService = Depends(_get_service),  # noqa: B008
) -> ApiResponse[list[ApiDeployment]]:
    """List all deployments for a specific API."""
    start = time.monotonic()
    try:
        deployments = service.list_deployments(api_id)
        return ApiResponse(data=deployments)
    except ApiCenterNotFoundError:
        _raise_error(404, "NOT_FOUND", f"API '{api_id}' not found")
    except ApiCenterClientError as exc:
        logger.error("list_api_deployments failed", extra={"api_id": api_id, "error": str(exc)})
        _raise_error(exc.status_code or 500, "CATALOG_ERROR", str(exc))
    finally:
        elapsed = time.monotonic() - start
        logger.info(
            "api_response_time", extra={"endpoint": "list_api_deployments", "duration_ms": round(elapsed * 1000, 2)}
        )


@router.get(
    "/api/environments",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def list_environments(
    service: ApiCatalogService = Depends(_get_service),  # noqa: B008
) -> ApiResponse[list[ApiEnvironment]]:
    """List all deployment environments."""
    start = time.monotonic()
    try:
        environments = service.list_environments()
        return ApiResponse(data=environments)
    except ApiCenterClientError as exc:
        logger.error("list_environments failed", extra={"error": str(exc)})
        _raise_error(exc.status_code or 500, "CATALOG_ERROR", str(exc))
    finally:
        elapsed = time.monotonic() - start
        logger.info(
            "api_response_time", extra={"endpoint": "list_environments", "duration_ms": round(elapsed * 1000, 2)}
        )
