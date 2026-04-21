"""Metadata completeness scoring and recommendations API routes.

Provides endpoints for metadata completeness scoring, AI-powered
recommendations, and organization-wide metadata quality insights.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path

from apic_vibe_portal_bff.middleware.security_trimming import make_accessible_ids_dep
from apic_vibe_portal_bff.services.metadata_completeness_service import MetadataCompletenessService
from apic_vibe_portal_bff.services.metadata_recommendations_service import MetadataRecommendationsService

router = APIRouter(prefix="/api/metadata", tags=["metadata"])

# Service singletons
_completeness_service_instance: MetadataCompletenessService | None = None
_recommendations_service_instance: MetadataRecommendationsService | None = None

# Dependency callables — exposed at module level so tests can override them
_accessible_ids_dep = make_accessible_ids_dep()


def _get_completeness_service() -> MetadataCompletenessService:
    """Lazy-initialize and return the metadata completeness service singleton."""
    global _completeness_service_instance  # noqa: PLW0603
    if _completeness_service_instance is None:
        from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
        from apic_vibe_portal_bff.config.settings import get_settings

        settings = get_settings()
        api_center_client = ApiCenterClient(
            base_url=settings.api_center_endpoint,
            workspace_name=settings.api_center_workspace_name,
        )
        _completeness_service_instance = MetadataCompletenessService(
            api_center_client=api_center_client,
        )
    return _completeness_service_instance


def _get_recommendations_service() -> MetadataRecommendationsService:
    """Lazy-initialize and return the metadata recommendations service singleton."""
    global _recommendations_service_instance  # noqa: PLW0603
    if _recommendations_service_instance is None:
        from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
        from apic_vibe_portal_bff.config.settings import get_settings

        settings = get_settings()
        api_center_client = ApiCenterClient(
            base_url=settings.api_center_endpoint,
            workspace_name=settings.api_center_workspace_name,
        )
        completeness_svc = _get_completeness_service()
        _recommendations_service_instance = MetadataRecommendationsService(
            metadata_completeness_service=completeness_svc,
            api_center_client=api_center_client,
        )
    return _recommendations_service_instance


CompletenessServiceDep = Annotated[MetadataCompletenessService, Depends(_get_completeness_service)]
RecommendationsServiceDep = Annotated[MetadataRecommendationsService, Depends(_get_recommendations_service)]
AccessibleApiIdsDep = Annotated[list[str] | None, Depends(_accessible_ids_dep)]


# ---------------------------------------------------------------------------
# Routes — static paths MUST come before parameterized paths so that
# "overview" and "leaderboard" are not captured as {api_id}.
# ---------------------------------------------------------------------------


@router.get("/overview")
async def get_metadata_overview(
    service: CompletenessServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> dict[str, Any]:
    """Get organization-wide completeness overview.

    Returns
    -------
    - averageScore: Average completeness score across all APIs
    - averageGrade: Grade for average score
    - totalApis: Total number of APIs
    - distribution: Count of APIs per grade (A, B, C, D, F)
    - dimensionAverages: Average scores per dimension
    """
    return service.get_overview(accessible_api_ids=accessible_api_ids)


@router.get("/leaderboard")
async def get_metadata_leaderboard(
    service: CompletenessServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> dict[str, Any]:
    """Get top and bottom APIs by completeness.

    Returns
    -------
    - top: List of top 5 most complete APIs
    - bottom: List of bottom 5 least complete APIs
    """
    return service.get_leaderboard(accessible_api_ids=accessible_api_ids)


@router.get("/{api_id}/score")
async def get_metadata_score(
    api_id: Annotated[str, Path(description="API identifier")],
    service: CompletenessServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> dict[str, Any]:
    """Get completeness score for a single API.

    Returns
    -------
    - apiId: API identifier
    - apiName: API title
    - overallScore: Weighted overall score (0-100)
    - grade: Letter grade (A, B, C, D, F)
    - dimensions: List of dimension scores
    - lastChecked: ISO-8601 timestamp
    """
    try:
        return service.get_score(api_id=api_id, accessible_api_ids=accessible_api_ids)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{api_id}/recommendations")
async def get_metadata_recommendations(
    api_id: Annotated[str, Path(description="API identifier")],
    service: RecommendationsServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> dict[str, Any]:
    """Get AI recommendations for improving API metadata.

    Returns
    -------
    - apiId: API identifier
    - apiName: API title
    - overallScore: Current completeness score
    - grade: Letter grade
    - recommendations: Prioritized list of improvement recommendations
    - generatedAt: ISO-8601 timestamp
    """
    try:
        return service.get_recommendations(api_id=api_id, accessible_api_ids=accessible_api_ids)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
