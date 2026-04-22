"""Governance dashboard service — aggregate governance data for dashboard views.

Provides summary statistics, score distributions, rule compliance rates, trend
data, and per-API compliance details for the governance dashboard UI.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from apic_vibe_portal_bff.agents.governance_agent.definition import GovernanceAgent
from apic_vibe_portal_bff.agents.governance_agent.rules.compliance_checker import (
    ComplianceChecker,
    ComplianceResult,
    GovernanceCategory,
)
from apic_vibe_portal_bff.agents.governance_agent.rules.governance_rules import DEFAULT_RULES
from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
from apic_vibe_portal_bff.data.repositories.governance_repository import GovernanceRepository

logger = logging.getLogger(__name__)


class GovernanceDashboardService:
    """Service for governance dashboard data aggregation.

    Parameters
    ----------
    api_center_client:
        Client for fetching API definitions.
    governance_repository:
        Repository for governance snapshot data.
    governance_agent:
        Governance agent for compliance checks (optional).
    """

    def __init__(
        self,
        api_center_client: ApiCenterClient,
        governance_repository: GovernanceRepository | None = None,
        governance_agent: GovernanceAgent | None = None,
    ) -> None:
        self._api_center = api_center_client
        self._governance_repo = governance_repository
        self._governance_agent = governance_agent
        self._checker = ComplianceChecker()

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------

    def get_summary(self, accessible_api_ids: list[str] | None = None) -> dict[str, Any]:
        """Return overall governance summary with KPIs.

        Returns
        -------
        dict with keys:
            - overall_score: Average governance score across all APIs
            - compliant_count: Number of APIs with score >= 75
            - total_count: Total number of APIs
            - critical_issues: Count of APIs with critical failures
            - improvement: Score change over last 30 days (placeholder: 0)
        """
        all_apis = self._get_accessible_apis(accessible_api_ids)
        if not all_apis:
            return {
                "overallScore": 0.0,
                "compliantCount": 0,
                "totalCount": 0,
                "criticalIssues": 0,
                "improvement": 0.0,
            }

        scores = []
        compliant_count = 0
        critical_issues = 0

        for api in all_apis:
            result = self._check_api_compliance(api)
            scores.append(result.score)
            if result.score >= 75:
                compliant_count += 1
            if result.critical_failures:
                critical_issues += 1

        overall_score = sum(scores) / len(scores) if scores else 0.0

        return {
            "overallScore": round(overall_score, 1),
            "compliantCount": compliant_count,
            "totalCount": len(all_apis),
            "criticalIssues": critical_issues,
            "improvement": 0.0,  # TODO: Calculate from historical snapshots
        }

    def get_scores(self, accessible_api_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Return governance scores for all APIs.

        Returns
        -------
        List of dicts with keys:
            - apiId: API identifier
            - apiName: API title
            - score: Governance score (0-100)
            - category: Governance category (Excellent, Good, Needs Improvement, Poor)
            - criticalFailures: Count of critical rule failures
            - lastChecked: ISO-8601 timestamp (current time)
        """
        all_apis = self._get_accessible_apis(accessible_api_ids)
        results = []

        for api in all_apis:
            result = self._check_api_compliance(api)
            results.append(
                {
                    "apiId": result.api_id,
                    "apiName": result.api_name,
                    "score": result.score,
                    "category": result.category.value,
                    "criticalFailures": len(result.critical_failures),
                    "lastChecked": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                }
            )

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def get_rules(self) -> list[dict[str, Any]]:
        """Return available governance rules.

        Returns
        -------
        List of dicts with keys:
            - ruleId: Rule identifier
            - name: Human-readable rule name
            - description: Rule description
            - severity: Rule severity (critical, warning, info)
            - remediation: Remediation guidance
        """
        return [
            {
                "ruleId": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity.value,
                "remediation": rule.remediation,
            }
            for rule in DEFAULT_RULES
        ]

    def get_api_compliance(self, api_id: str, accessible_api_ids: list[str] | None = None) -> dict[str, Any]:
        """Return compliance report for a single API.

        Parameters
        ----------
        api_id:
            API identifier (name).
        accessible_api_ids:
            Optional list of API IDs the user can access.

        Returns
        -------
        dict with keys:
            - apiId: API identifier
            - apiName: API title
            - score: Governance score (0-100)
            - category: Governance category
            - criticalFailures: Count of critical failures
            - findings: List of rule evaluation results
            - lastChecked: ISO-8601 timestamp

        Raises
        ------
        PermissionError:
            If the API is not in the accessible list.
        ValueError:
            If the API is not found.
        """
        if accessible_api_ids is not None and api_id not in accessible_api_ids:
            raise PermissionError(f"Access denied to API: {api_id}")

        try:
            api = self._api_center.get_api(api_id)
        except Exception as e:
            raise ValueError(f"API not found: {api_id}") from e

        # Enrich with versions and deployments
        api = self._enrich_api(api)
        result = self._check_api_compliance(api)

        return {
            "apiId": result.api_id,
            "apiName": result.api_name,
            "score": result.score,
            "category": result.category.value,
            "criticalFailures": len(result.critical_failures),
            "findings": [
                {
                    "ruleId": r.rule_id,
                    "ruleName": r.rule_name,
                    "severity": r.severity.value,
                    "passed": r.passed,
                    "message": r.message,
                    "remediation": r.remediation,
                }
                for r in result.rule_results
            ],
            "lastChecked": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }

    def get_trends(self, accessible_api_ids: list[str] | None = None, days: int = 30) -> dict[str, Any]:
        """Return governance score trends over time.

        Parameters
        ----------
        accessible_api_ids:
            Optional list of API IDs the user can access.
        days:
            Number of days to include in trend data.

        Returns
        -------
        dict with keys:
            - dataPoints: List of {date, averageScore} dicts
            - summary: {startScore, endScore, change} dict
        """
        # TODO: Implement trend calculation from governance snapshots
        # For now, return placeholder data
        now = datetime.now(UTC)
        data_points = []

        # Generate weekly data points
        for i in range(5):
            date = now - timedelta(days=i * 7)
            data_points.append(
                {
                    "date": date.isoformat().replace("+00:00", "Z"),
                    "averageScore": 75.0,  # Placeholder
                }
            )

        data_points.reverse()

        return {
            "dataPoints": data_points,
            "summary": {
                "startScore": 75.0,
                "endScore": 75.0,
                "change": 0.0,
            },
        }

    def get_score_distribution(self, accessible_api_ids: list[str] | None = None) -> dict[str, Any]:
        """Return score distribution across categories.

        Returns
        -------
        dict with keys:
            - excellent: Count of APIs with score >= 90
            - good: Count of APIs with 75 <= score < 90
            - needsImprovement: Count of APIs with 50 <= score < 75
            - poor: Count of APIs with score < 50
        """
        all_apis = self._get_accessible_apis(accessible_api_ids)
        distribution = {
            "excellent": 0,
            "good": 0,
            "needsImprovement": 0,
            "poor": 0,
        }

        for api in all_apis:
            result = self._check_api_compliance(api)
            if result.category == GovernanceCategory.EXCELLENT:
                distribution["excellent"] += 1
            elif result.category == GovernanceCategory.GOOD:
                distribution["good"] += 1
            elif result.category == GovernanceCategory.NEEDS_IMPROVEMENT:
                distribution["needsImprovement"] += 1
            else:
                distribution["poor"] += 1

        return distribution

    def get_rule_compliance(self, accessible_api_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Return compliance rates per governance rule.

        Returns
        -------
        List of dicts with keys:
            - ruleId: Rule identifier
            - ruleName: Rule name
            - severity: Rule severity
            - passCount: Number of APIs passing this rule
            - failCount: Number of APIs failing this rule
            - complianceRate: Percentage of APIs passing (0-100)
        """
        all_apis = self._get_accessible_apis(accessible_api_ids)
        if not all_apis:
            return []

        # Count passes and fails per rule
        rule_stats: dict[str, dict[str, Any]] = {}
        for rule in DEFAULT_RULES:
            rule_stats[rule.rule_id] = {
                "ruleId": rule.rule_id,
                "ruleName": rule.name,
                "severity": rule.severity.value,
                "passCount": 0,
                "failCount": 0,
            }

        for api in all_apis:
            result = self._check_api_compliance(api)
            for rule_result in result.rule_results:
                if rule_result.passed:
                    rule_stats[rule_result.rule_id]["passCount"] += 1
                else:
                    rule_stats[rule_result.rule_id]["failCount"] += 1

        # Calculate compliance rates
        total_apis = len(all_apis)
        results = []
        for stats in rule_stats.values():
            compliance_rate = (stats["passCount"] / total_apis * 100) if total_apis > 0 else 0.0
            results.append(
                {
                    **stats,
                    "complianceRate": round(compliance_rate, 1),
                }
            )

        # Sort by compliance rate ascending (worst first)
        results.sort(key=lambda x: x["complianceRate"])
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_accessible_apis(self, accessible_api_ids: list[str] | None) -> list[dict[str, Any]]:
        """Fetch all accessible APIs and enrich with versions/deployments."""
        all_apis: list[dict[str, Any]] = self._api_center.list_apis()

        # Apply security trimming
        if accessible_api_ids is not None:
            all_apis = [api for api in all_apis if api.get("name") in accessible_api_ids]

        # Enrich each API with versions and deployments
        return [self._enrich_api(api) for api in all_apis]

    def _enrich_api(self, api: dict[str, Any]) -> dict[str, Any]:
        """Enrich an API dict with versions and deployments."""
        api_id = api.get("name", "")
        if not api_id:
            return api

        # Fetch versions
        try:
            api["versions"] = self._api_center.list_api_versions(api_id)
        except Exception:
            logger.warning(f"Failed to fetch versions for API: {api_id}")
            api["versions"] = []

        # Fetch deployments
        try:
            api["deployments"] = self._api_center.list_deployments(api_id)
        except Exception:
            logger.warning(f"Failed to fetch deployments for API: {api_id}")
            api["deployments"] = []

        return api

    def _check_api_compliance(self, api: dict[str, Any]) -> ComplianceResult:
        """Run compliance check on an API."""
        return self._checker.check_api(api)
