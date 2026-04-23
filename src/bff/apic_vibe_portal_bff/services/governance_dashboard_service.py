"""Governance dashboard service — aggregate governance data for dashboard views.

Provides summary statistics, score distributions, rule compliance rates, trend
data, and per-API compliance details for the governance dashboard UI.

For aggregate endpoints (summary, scores, distribution, rule-compliance) the
service first attempts to load pre-computed snapshots from Cosmos DB (written
by the governance worker).  Only when no snapshots are available does it fall
back to computing results on demand from the API Center.
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
from apic_vibe_portal_bff.agents.governance_agent.rules.governance_rules import DEFAULT_RULES, RuleSeverity
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
            - overallScore: Average governance score across all APIs
            - compliantCount: Number of APIs with score >= 75
            - totalCount: Total number of APIs
            - criticalIssues: Count of APIs with critical failures
            - improvement: Score change over last 30 days (placeholder: 0)
        """
        snapshots = self._load_snapshots(accessible_api_ids)
        if snapshots is not None:
            return self._summary_from_snapshots(snapshots)

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
            - lastChecked: ISO-8601 timestamp
        """
        snapshots = self._load_snapshots(accessible_api_ids)
        if snapshots is not None:
            return self._scores_from_snapshots(snapshots)

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

        Always performs a live check against API Center so that the detail
        view reflects the current state of the API.

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
        snapshots = self._load_snapshots(accessible_api_ids)
        if snapshots is not None:
            return self._distribution_from_snapshots(snapshots)

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
        snapshots = self._load_snapshots(accessible_api_ids)
        if snapshots is not None:
            return self._rule_compliance_from_snapshots(snapshots)

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
    # Snapshot-based aggregation helpers
    # ------------------------------------------------------------------

    def _load_snapshots(self, accessible_api_ids: list[str] | None) -> list[dict[str, Any]] | None:
        """Load the latest governance snapshots from Cosmos DB.

        Returns ``None`` when the repository is unavailable, the query fails,
        or no snapshots exist — callers should then fall back to live computation.
        """
        if self._governance_repo is None:
            return None
        try:
            snapshots = self._governance_repo.list_latest_snapshots()
        except Exception:
            logger.warning(
                "GovernanceDashboardService: failed to load snapshots from Cosmos DB — falling back to live computation"
            )
            return None

        if not snapshots:
            return None

        if accessible_api_ids is not None:
            snapshots = [s for s in snapshots if s.get("apiId") in accessible_api_ids]

        return snapshots

    def _get_api_name_map(self) -> dict[str, str]:
        """Return a mapping of ``apiId → apiName`` fetched from API Center.

        This is a lightweight call (no per-API version/deployment enrichment)
        used to resolve human-readable names when building responses from
        snapshot data.  Falls back to an empty dict on error.
        """
        try:
            apis = self._api_center.list_apis()
            return {api.get("name", ""): api.get("title") or api.get("name", "") for api in apis if api.get("name")}
        except Exception:
            logger.warning("GovernanceDashboardService: failed to fetch API name map from API Center")
            return {}

    @staticmethod
    def _category_from_score(score: float) -> GovernanceCategory:
        """Map a numeric score to a :class:`GovernanceCategory`."""
        if score >= 90:
            return GovernanceCategory.EXCELLENT
        if score >= 75:
            return GovernanceCategory.GOOD
        if score >= 50:
            return GovernanceCategory.NEEDS_IMPROVEMENT
        return GovernanceCategory.POOR

    def _summary_from_snapshots(self, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        """Build the summary KPI dict from a list of snapshot documents."""
        if not snapshots:
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

        for snapshot in snapshots:
            score = float(snapshot.get("complianceScore", 0.0))
            scores.append(score)
            if score >= 75:
                compliant_count += 1
            has_critical_failure = any(
                not f.get("passed", True) and f.get("severity", "") == RuleSeverity.CRITICAL
                for f in snapshot.get("findings", [])
            )
            if has_critical_failure:
                critical_issues += 1

        overall_score = sum(scores) / len(scores) if scores else 0.0
        return {
            "overallScore": round(overall_score, 1),
            "compliantCount": compliant_count,
            "totalCount": len(snapshots),
            "criticalIssues": critical_issues,
            "improvement": 0.0,  # TODO: Calculate from historical snapshots
        }

    def _scores_from_snapshots(self, snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build the scores list from snapshot documents."""
        name_map = self._get_api_name_map()
        results = []
        for snapshot in snapshots:
            api_id = snapshot.get("apiId", "")
            score = float(snapshot.get("complianceScore", 0.0))
            category = self._category_from_score(score)
            critical_failures = sum(
                1
                for f in snapshot.get("findings", [])
                if not f.get("passed", True) and f.get("severity", "") == RuleSeverity.CRITICAL
            )
            results.append(
                {
                    "apiId": api_id,
                    "apiName": name_map.get(api_id, api_id),
                    "score": score,
                    "category": category.value,
                    "criticalFailures": critical_failures,
                    "lastChecked": snapshot.get("timestamp", ""),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def _distribution_from_snapshots(self, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        """Build score distribution counts from snapshot documents."""
        distribution = {"excellent": 0, "good": 0, "needsImprovement": 0, "poor": 0}
        for snapshot in snapshots:
            score = float(snapshot.get("complianceScore", 0.0))
            category = self._category_from_score(score)
            if category == GovernanceCategory.EXCELLENT:
                distribution["excellent"] += 1
            elif category == GovernanceCategory.GOOD:
                distribution["good"] += 1
            elif category == GovernanceCategory.NEEDS_IMPROVEMENT:
                distribution["needsImprovement"] += 1
            else:
                distribution["poor"] += 1
        return distribution

    def _rule_compliance_from_snapshots(self, snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build per-rule compliance rates from snapshot documents."""
        if not snapshots:
            return []

        # Build rule metadata lookup from DEFAULT_RULES
        rule_meta: dict[str, dict[str, str]] = {
            rule.rule_id: {"ruleName": rule.name, "severity": rule.severity.value} for rule in DEFAULT_RULES
        }

        rule_stats: dict[str, dict[str, Any]] = {}
        for snapshot in snapshots:
            for finding in snapshot.get("findings", []):
                rule_id = finding.get("ruleId", "")
                if not rule_id:
                    continue
                if rule_id not in rule_stats:
                    meta = rule_meta.get(rule_id, {"ruleName": rule_id, "severity": "info"})
                    rule_stats[rule_id] = {
                        "ruleId": rule_id,
                        "ruleName": meta["ruleName"],
                        "severity": meta["severity"],
                        "passCount": 0,
                        "failCount": 0,
                    }
                if finding.get("passed", True):
                    rule_stats[rule_id]["passCount"] += 1
                else:
                    rule_stats[rule_id]["failCount"] += 1

        total_apis = len(snapshots)
        results = []
        for stats in rule_stats.values():
            compliance_rate = (stats["passCount"] / total_apis * 100) if total_apis > 0 else 0.0
            results.append({**stats, "complianceRate": round(compliance_rate, 1)})

        results.sort(key=lambda x: x["complianceRate"])
        return results

    # ------------------------------------------------------------------
    # Internal helpers (live computation path)
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
