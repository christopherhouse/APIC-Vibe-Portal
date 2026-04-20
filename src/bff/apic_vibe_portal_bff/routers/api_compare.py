"""API comparison endpoints.

Exposes structured multi-API comparison data and optional AI-powered narrative
analysis.

Endpoints
---------
POST /api/compare                   — Compare 2-5 APIs (structured data only)
POST /api/compare/ai-analysis       — Compare with AI-generated narrative
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from apic_vibe_portal_bff.middleware.rbac import require_any_role
from apic_vibe_portal_bff.middleware.security_trimming import make_accessible_ids_dep
from apic_vibe_portal_bff.routers.api_catalog import CatalogApiError, _get_service
from apic_vibe_portal_bff.services.api_catalog_service import ApiAccessDeniedError, ApiCatalogService
from apic_vibe_portal_bff.services.api_compare_service import (
    ALL_ASPECTS,
    ApiCompareService,
    CompareAspect,
    CompareResponse,
)

logger = logging.getLogger(__name__)

_ALLOWED_ROLES = ["Portal.User", "Portal.Admin", "Portal.Maintainer"]

# ---------------------------------------------------------------------------
# Service dependency — lazily created once per process
# ---------------------------------------------------------------------------

_compare_service_instance: ApiCompareService | None = None


def _get_compare_service(
    catalog_service: ApiCatalogService = Depends(_get_service),  # noqa: B008
) -> ApiCompareService:
    """Return a shared :class:`ApiCompareService` instance.

    In production a real OpenAI client is injected; tests override this
    dependency via ``app.dependency_overrides``.
    """
    global _compare_service_instance  # noqa: PLW0603
    if _compare_service_instance is None:
        try:
            from apic_vibe_portal_bff.clients.openai_client import OpenAIClient
            from apic_vibe_portal_bff.config.settings import get_settings

            settings = get_settings()
            if settings.openai_endpoint and settings.openai_chat_deployment:
                openai_client: Any | None = OpenAIClient(
                    endpoint=settings.openai_endpoint,
                    deployment=settings.openai_chat_deployment,
                    api_version=settings.openai_api_version,
                )
            else:
                openai_client = None
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialize OpenAI client for API comparison.")
            openai_client = None

        _compare_service_instance = ApiCompareService(
            catalog_service=catalog_service,
            openai_client=openai_client,
        )
    return _compare_service_instance


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CompareRequest(BaseModel):
    """Request body for the compare endpoints."""

    api_ids: list[str] = Field(alias="apiIds", min_length=2, max_length=5)
    aspects: list[CompareAspect] | None = Field(default=None)

    model_config = {"populate_by_name": True}

    @field_validator("api_ids")
    @classmethod
    def validate_api_ids(cls, v: list[str]) -> list[str]:
        if len(v) < 2:  # noqa: PLR2004
            raise ValueError("At least 2 API IDs are required")
        if len(v) > 5:  # noqa: PLR2004
            raise ValueError("At most 5 API IDs are allowed")
        return v


class ErrorDetail(BaseModel):
    """Structured error detail."""

    code: str
    message: str
    details: Any | None = None


class CompareApiErrorResponse(BaseModel):
    """Standard error envelope for compare endpoints."""

    error: ErrorDetail


def compare_api_error_handler(_request: object, exc: CatalogApiError) -> JSONResponse:
    """Re-use :class:`CatalogApiError` for comparison errors."""
    body = CompareApiErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


def _raise_error(status_code: int, code: str, message: str, details: Any | None = None) -> None:
    raise CatalogApiError(status_code=status_code, code=code, message=message, details=details)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["compare"])


@router.post(
    "/api/compare",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
    response_model=CompareResponse,
)
def compare_apis(
    body: CompareRequest,
    service: ApiCompareService = Depends(_get_compare_service),  # noqa: B008
    accessible_api_ids: list[str] | None = Depends(make_accessible_ids_dep()),  # noqa: B008
) -> CompareResponse:
    """Compare 2–5 APIs and return structured aspect comparison data."""
    try:
        aspects = body.aspects if body.aspects else ALL_ASPECTS
        return service.compare(body.api_ids, aspects, accessible_api_ids=accessible_api_ids)
    except ApiAccessDeniedError as exc:
        _raise_error(403, "FORBIDDEN", f"Access to API '{exc.api_name}' is not permitted")
    except ValueError as exc:
        _raise_error(422, "INVALID_REQUEST", str(exc))
    except Exception as exc:
        logger.error("compare_apis failed", extra={"error": str(exc)})
        _raise_error(500, "COMPARE_ERROR", "An error occurred while comparing APIs")


@router.post(
    "/api/compare/ai-analysis",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
    response_model=CompareResponse,
)
async def compare_apis_with_ai(
    body: CompareRequest,
    service: ApiCompareService = Depends(_get_compare_service),  # noqa: B008
    accessible_api_ids: list[str] | None = Depends(make_accessible_ids_dep()),  # noqa: B008
) -> CompareResponse:
    """Compare 2–5 APIs and include an AI-generated narrative analysis."""
    try:
        aspects = body.aspects if body.aspects else ALL_ASPECTS
        return await service.compare_with_ai(body.api_ids, aspects, accessible_api_ids=accessible_api_ids)
    except ApiAccessDeniedError as exc:
        _raise_error(403, "FORBIDDEN", f"Access to API '{exc.api_name}' is not permitted")
    except ValueError as exc:
        _raise_error(422, "INVALID_REQUEST", str(exc))
    except Exception as exc:
        logger.error("compare_apis_with_ai failed", extra={"error": str(exc)})
        _raise_error(500, "COMPARE_ERROR", "An error occurred while generating comparison")
