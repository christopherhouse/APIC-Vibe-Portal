"""Search API endpoints.

Exposes Azure AI Search capabilities to the frontend via REST endpoints:

POST /api/search           — Full hybrid search with facets, highlights, captions
GET  /api/search/suggest   — Autocomplete suggestions based on a prefix

Request and response payloads are defined by the BFF Pydantic models used by
these routes. Keep those models in sync with any shared/frontend DTOs before
relying on wire-contract compatibility.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from apic_vibe_portal_bff.clients.ai_search_client import AISearchClientError
from apic_vibe_portal_bff.middleware.rbac import require_any_role
from apic_vibe_portal_bff.models.search import (
    SearchRequest,
    SearchResponse,
    SuggestResponse,
)
from apic_vibe_portal_bff.services.search_service import SearchService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service dependency — lazily created once per process
# ---------------------------------------------------------------------------

_service_instance: SearchService | None = None


def _get_search_service() -> SearchService:
    """Return a shared :class:`SearchService` instance.

    In production the service is created once with real Azure credentials.
    Tests override this dependency via ``app.dependency_overrides``.
    """
    global _service_instance  # noqa: PLW0603
    if _service_instance is None:
        from apic_vibe_portal_bff.clients.ai_search_client import AISearchClient
        from apic_vibe_portal_bff.config.settings import get_settings

        settings = get_settings()
        client = AISearchClient(
            endpoint=settings.ai_search_endpoint,
            index_name=settings.ai_search_index_name,
        )
        _service_instance = SearchService(client=client)
    return _service_instance


# ---------------------------------------------------------------------------
# Error models
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Structured error detail."""

    code: str
    message: str
    details: Any | None = None


class SearchApiErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail


class SearchApiError(Exception):
    """Raised by route handlers to produce a structured error response."""

    def __init__(self, status_code: int, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def search_api_error_handler(_request: object, exc: SearchApiError) -> JSONResponse:
    """Serialize :class:`SearchApiError` into a JSON error envelope."""
    body = SearchApiErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_ROLES = ["Portal.User", "Portal.Admin", "Portal.Maintainer"]


def _raise_error(status_code: int, code: str, message: str, details: Any | None = None) -> None:
    """Raise a :class:`SearchApiError` with a structured error body."""
    raise SearchApiError(status_code=status_code, code=code, message=message, details=details)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["search"])


@router.post(
    "/api/search",
    response_model=SearchResponse,
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def search(
    request: SearchRequest,
    service: SearchService = Depends(_get_search_service),  # noqa: B008
) -> SearchResponse:
    """Execute a search against the API catalog.

    Delegates search execution to the backend search service and returns
    results shaped to the shared search response DTO.
    """
    try:
        return service.search(request)
    except AISearchClientError as exc:
        logger.error("search failed", extra={"error": str(exc)})
        _raise_error(exc.status_code or 500, "SEARCH_ERROR", str(exc))


@router.get(
    "/api/search/suggest",
    response_model=SuggestResponse,
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def suggest(
    q: str = Query(description="Search prefix for autocomplete suggestions"),  # noqa: B008
    service: SearchService = Depends(_get_search_service),  # noqa: B008
) -> SuggestResponse:
    """Return autocomplete suggestions for the given prefix."""
    try:
        return service.suggest(prefix=q)
    except AISearchClientError as exc:
        logger.error("suggest failed", extra={"error": str(exc)})
        _raise_error(exc.status_code or 500, "SEARCH_ERROR", str(exc))
