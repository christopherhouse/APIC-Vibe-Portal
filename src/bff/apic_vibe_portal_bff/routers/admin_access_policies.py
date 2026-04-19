"""Admin endpoints for managing API access policies.

These endpoints allow portal administrators to configure which Entra ID groups
may access which APIs.  All endpoints require the ``Portal.Admin`` role.

Endpoints
---------
GET    /api/admin/access-policies              — List all access policies
GET    /api/admin/access-policies/{api_name}   — Get policy for a specific API
PUT    /api/admin/access-policies/{api_name}   — Create or replace a policy
DELETE /api/admin/access-policies/{api_name}   — Delete a policy (API becomes public)
POST   /api/admin/access-policies/cache/invalidate — Force cache refresh

## Access model

An API with *no* policy document is accessible to all authenticated users
(public by default).  Once a policy is created the access rules in the
``allowedGroups`` list control who can see the API.

Setting ``isPublic: true`` on a policy makes the API publicly accessible to
all authenticated users regardless of group membership.

Admin users (``Portal.Admin`` role) always see all APIs regardless of policies.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from apic_vibe_portal_bff.data.models.api_access_policy import ApiAccessPolicyDocument
from apic_vibe_portal_bff.middleware.rbac import require_role
from apic_vibe_portal_bff.middleware.security_trimming import _get_user_context_service
from apic_vibe_portal_bff.services.user_context_service import UserContextService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AccessPolicyRequest(BaseModel):
    """Request body for creating or replacing an API access policy."""

    allowed_groups: list[str] = Field(
        default_factory=list,
        alias="allowedGroups",
        description=(
            "Entra ID group object IDs (OIDs) whose members may access this API. "
            "An empty list with isPublic=false makes the API inaccessible to non-admins."
        ),
    )
    is_public: bool = Field(
        default=False,
        alias="isPublic",
        description="When true, all authenticated users can access this API.",
    )
    api_id: str = Field(
        default="",
        alias="apiId",
        description="Full Azure resource ID of the API (informational).",
    )

    model_config = {"populate_by_name": True}


class AccessPolicyResponse(BaseModel):
    """Response body for an API access policy."""

    api_name: str = Field(..., alias="apiName")
    api_id: str = Field(default="", alias="apiId")
    allowed_groups: list[str] = Field(default_factory=list, alias="allowedGroups")
    is_public: bool = Field(default=False, alias="isPublic")
    created_at: str = Field(default="", alias="createdAt")
    updated_at: str = Field(default="", alias="updatedAt")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_document(cls, doc: ApiAccessPolicyDocument) -> AccessPolicyResponse:
        """Build a response from an :class:`ApiAccessPolicyDocument`."""
        return cls(
            apiName=doc.api_name,
            apiId=doc.api_id,
            allowedGroups=doc.allowed_groups,
            isPublic=doc.is_public,
            createdAt=doc.created_at,
            updatedAt=doc.updated_at,
        )


class ErrorDetail(BaseModel):
    """Structured error detail."""

    code: str
    message: str
    details: Any | None = None


class AdminApiErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["admin"])

_ADMIN_ROLE = "Portal.Admin"

# Pattern that matches characters that must not appear in log messages to
# prevent log-injection attacks (newlines, carriage returns, and other ASCII
# control characters).
_LOG_UNSAFE = re.compile(r"[\x00-\x1f\x7f]")


def _safe(value: str) -> str:
    """Return *value* with control characters removed for safe log output."""
    return _LOG_UNSAFE.sub("", value)


def _get_svc() -> UserContextService:
    """Return the shared :class:`UserContextService` instance."""
    return _get_user_context_service()


@router.get(
    "/api/admin/access-policies",
    response_model=list[AccessPolicyResponse],
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="List all API access policies",
)
def list_access_policies(
    svc: UserContextService = Depends(_get_svc),  # noqa: B008
) -> list[AccessPolicyResponse]:
    """Return all configured API access policies.

    APIs not in this list are publicly accessible to all authenticated users.
    """
    try:
        policies = svc._repo.list_all_policies()  # noqa: SLF001
        return [AccessPolicyResponse.from_document(p) for p in policies]
    except Exception as exc:
        logger.exception("list_access_policies failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "POLICY_ERROR", "message": str(exc)},
        ) from exc


@router.get(
    "/api/admin/access-policies/{api_name}",
    response_model=AccessPolicyResponse,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Get access policy for a specific API",
)
def get_access_policy(
    api_name: str,
    svc: UserContextService = Depends(_get_svc),  # noqa: B008
) -> AccessPolicyResponse:
    """Return the access policy for the named API.

    Returns 404 if no explicit policy has been set (the API is public by
    default when no policy exists).
    """
    try:
        policy = svc._repo.get_policy(api_name)  # noqa: SLF001
    except Exception as exc:
        logger.exception("get_access_policy failed: api_name=%s", _safe(api_name))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "POLICY_ERROR", "message": str(exc)},
        ) from exc

    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "POLICY_NOT_FOUND",
                "message": (f"No access policy found for API '{api_name}'. The API is publicly accessible by default."),
            },
        )
    return AccessPolicyResponse.from_document(policy)


@router.put(
    "/api/admin/access-policies/{api_name}",
    response_model=AccessPolicyResponse,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Create or replace access policy for an API",
)
def upsert_access_policy(
    api_name: str,
    body: AccessPolicyRequest,
    svc: UserContextService = Depends(_get_svc),  # noqa: B008
) -> AccessPolicyResponse:
    """Create or replace the access policy for the named API.

    After a successful write the in-memory policy cache is invalidated so
    subsequent requests immediately reflect the new policy.
    """
    doc = ApiAccessPolicyDocument.new(
        api_name=api_name,
        api_id=body.api_id,
        allowed_groups=body.allowed_groups,
        is_public=body.is_public,
    )
    try:
        saved = svc._repo.upsert_policy(doc)  # noqa: SLF001
        svc.invalidate_policy_cache()
        logger.info(
            "admin.upsert_access_policy",
            extra={"api_name": _safe(api_name), "is_public": body.is_public, "group_count": len(body.allowed_groups)},
        )
        return AccessPolicyResponse.from_document(saved)
    except Exception as exc:
        logger.exception("upsert_access_policy failed: api_name=%s", _safe(api_name))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "POLICY_ERROR", "message": str(exc)},
        ) from exc


@router.delete(
    "/api/admin/access-policies/{api_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Delete access policy for an API (API becomes public)",
)
def delete_access_policy(
    api_name: str,
    svc: UserContextService = Depends(_get_svc),  # noqa: B008
) -> None:
    """Delete the access policy for the named API.

    After deletion the API is accessible to all authenticated users.
    The in-memory cache is invalidated after a successful delete.
    """
    try:
        deleted = svc._repo.delete_policy(api_name)  # noqa: SLF001
        svc.invalidate_policy_cache()
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "POLICY_NOT_FOUND",
                    "message": f"No access policy found for API '{api_name}'.",
                },
            )
        logger.info("admin.delete_access_policy", extra={"api_name": _safe(api_name)})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("delete_access_policy failed: api_name=%s", _safe(api_name))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "POLICY_ERROR", "message": str(exc)},
        ) from exc


@router.post(
    "/api/admin/access-policies/cache/invalidate",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Force immediate refresh of the access policy cache",
)
def invalidate_policy_cache(
    svc: UserContextService = Depends(_get_svc),  # noqa: B008
) -> None:
    """Invalidate the in-memory access policy cache.

    The next request to any secured endpoint will reload policies from
    Cosmos DB.  Useful when policies have been modified externally (e.g.
    via the Azure Portal or another admin replica).
    """
    svc.invalidate_policy_cache()
    logger.info("admin.invalidate_policy_cache")
