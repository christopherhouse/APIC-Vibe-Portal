"""Governance dashboard API routes.

Provides endpoints for the governance dashboard UI:
- Summary statistics (KPIs)
- All API governance scores
- Available governance rules
- Single API compliance details
- Governance trends over time
- Score distribution
- Rule compliance rates
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path

from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClientError
from apic_vibe_portal_bff.middleware.security_trimming import make_accessible_ids_dep
from apic_vibe_portal_bff.services.governance_dashboard_service import GovernanceDashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/governance", tags=["governance"])

# Service singleton
_service_instance: GovernanceDashboardService | None = None

# Dependency callables — exposed at module level so tests can override them
_accessible_ids_dep = make_accessible_ids_dep()


def _get_service() -> GovernanceDashboardService:
    """Lazy-initialize and return the governance dashboard service singleton."""
    global _service_instance  # noqa: PLW0603
    if _service_instance is None:
        from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
        from apic_vibe_portal_bff.config.settings import get_settings

        settings = get_settings()
        api_center_client = ApiCenterClient(
            base_url=settings.api_center_endpoint,
            workspace_name=settings.api_center_workspace_name,
        )

        governance_repo = None
        if settings.cosmos_db_endpoint.strip():
            try:
                from apic_vibe_portal_bff.data.cosmos_client import get_container
                from apic_vibe_portal_bff.data.repositories.governance_repository import GovernanceRepository

                governance_repo = GovernanceRepository(get_container(settings.cosmos_db_governance_container))
            except Exception:  # noqa: BLE001 — graceful degradation: snapshots are optional
                logger.warning(
                    "GovernanceDashboardService: failed to connect to Cosmos DB — governance snapshots disabled"
                )
        else:
            logger.warning(
                "GovernanceDashboardService: COSMOS_DB_ENDPOINT not configured — governance snapshots disabled"
            )

        _service_instance = GovernanceDashboardService(
            api_center_client=api_center_client,
            governance_repository=governance_repo,
        )
    return _service_instance


GovernanceServiceDep = Annotated[GovernanceDashboardService, Depends(_get_service)]
AccessibleApiIdsDep = Annotated[list[str] | None, Depends(_accessible_ids_dep)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/summary")
async def get_governance_summary(
    service: GovernanceServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> dict[str, Any]:
    """Get overall governance summary with KPIs.

    Returns
    -------
    - overallScore: Average governance score across all APIs
    - compliantCount: Number of APIs with score >= 75
    - totalCount: Total number of APIs
    - criticalIssues: Count of APIs with critical failures
    - improvement: Score change over last 30 days
    """
    try:
        return service.get_summary(accessible_api_ids=accessible_api_ids)
    except ApiCenterClientError as exc:
        logger.error("get_governance_summary failed", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Failed to retrieve governance data from API Center") from exc


@router.get("/scores")
async def get_governance_scores(
    service: GovernanceServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> list[dict[str, Any]]:
    """Get governance scores for all APIs.

    Returns list of:
    - apiId: API identifier
    - apiName: API title
    - score: Governance score (0-100)
    - category: Governance category (Excellent, Good, Needs Improvement, Poor)
    - criticalFailures: Count of critical rule failures
    - lastChecked: ISO-8601 timestamp
    """
    try:
        return service.get_scores(accessible_api_ids=accessible_api_ids)
    except ApiCenterClientError as exc:
        logger.error("get_governance_scores failed", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Failed to retrieve governance scores from API Center") from exc


@router.get("/rules")
async def get_governance_rules(
    service: GovernanceServiceDep,
    _auth: AccessibleApiIdsDep,  # Enforces authentication; value not used by rules endpoint
) -> list[dict[str, Any]]:
    """Get available governance rules.

    Returns list of:
    - ruleId: Rule identifier
    - name: Human-readable rule name
    - description: Rule description
    - severity: Rule severity (critical, warning, info)
    - remediation: Remediation guidance
    """
    return service.get_rules()


@router.get("/apis/{api_id}/compliance")
async def get_api_compliance(
    api_id: Annotated[str, Path(description="API identifier")],
    service: GovernanceServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> dict[str, Any]:
    """Get compliance report for a single API.

    Returns:
    - apiId: API identifier
    - apiName: API title
    - score: Governance score (0-100)
    - category: Governance category
    - criticalFailures: Count of critical failures
    - findings: List of rule evaluation results
    - lastChecked: ISO-8601 timestamp
    """
    try:
        return service.get_api_compliance(api_id=api_id, accessible_api_ids=accessible_api_ids)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ApiCenterClientError as exc:
        logger.error("get_api_compliance failed", extra={"api_id": api_id, "error": str(exc)})
        raise HTTPException(status_code=502, detail="Failed to retrieve compliance data from API Center") from exc


@router.get("/trends")
async def get_governance_trends(
    service: GovernanceServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
    days: int = 30,
) -> dict[str, Any]:
    """Get governance score trends over time.

    Parameters
    ----------
    days:
        Number of days to include in trend data (default: 30)

    Returns
    -------
    - dataPoints: List of {date, averageScore} dicts
    - summary: {startScore, endScore, change} dict
    """
    try:
        return service.get_trends(accessible_api_ids=accessible_api_ids, days=days)
    except ApiCenterClientError as exc:
        logger.error("get_governance_trends failed", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Failed to retrieve governance trends from API Center") from exc


@router.get("/distribution")
async def get_score_distribution(
    service: GovernanceServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> dict[str, Any]:
    """Get score distribution across categories.

    Returns:
    - excellent: Count of APIs with score >= 90
    - good: Count of APIs with 75 <= score < 90
    - needsImprovement: Count of APIs with 50 <= score < 75
    - poor: Count of APIs with score < 50
    """
    try:
        return service.get_score_distribution(accessible_api_ids=accessible_api_ids)
    except ApiCenterClientError as exc:
        logger.error("get_score_distribution failed", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Failed to retrieve score distribution from API Center") from exc


@router.get("/rule-compliance")
async def get_rule_compliance(
    service: GovernanceServiceDep,
    accessible_api_ids: AccessibleApiIdsDep,
) -> list[dict[str, Any]]:
    """Get compliance rates per governance rule.

    Returns list of:
    - ruleId: Rule identifier
    - ruleName: Rule name
    - severity: Rule severity
    - passCount: Number of APIs passing this rule
    - failCount: Number of APIs failing this rule
    - complianceRate: Percentage of APIs passing (0-100)
    """
    try:
        return service.get_rule_compliance(accessible_api_ids=accessible_api_ids)
    except ApiCenterClientError as exc:
        logger.error("get_rule_compliance failed", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Failed to retrieve rule compliance data from API Center") from exc
