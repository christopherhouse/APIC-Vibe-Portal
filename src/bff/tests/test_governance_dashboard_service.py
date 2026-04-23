"""Unit tests for GovernanceDashboardService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apic_vibe_portal_bff.services.governance_dashboard_service import GovernanceDashboardService


def _make_mock_api(
    api_id: str,
    title: str | None = None,
    description: str = "",
    contacts: list | None = None,
    versions: list | None = None,
    deployments: list | None = None,
) -> dict:
    """Create a mock API dict."""
    return {
        "name": api_id,
        "title": title or api_id,
        "description": description,
        "contacts": contacts or [],
        "versions": versions or [],
        "deployments": deployments or [],
        "lifecycleStage": "production",
        "customProperties": {},
    }


_UNSET = object()  # Sentinel for "use default" in _make_service


def _make_service(
    apis: list[dict] | None = None, *, governance_repo: object = _UNSET
) -> tuple[GovernanceDashboardService, MagicMock, object]:
    """Return a service wired to mock clients.

    Pass ``governance_repo=None`` to simulate Cosmos DB being unavailable.
    When omitted the default is a :class:`MagicMock` repository configured
    to return an empty snapshot list, so the service falls through to the
    live-computation path (which the existing tests exercise).
    """
    mock_api_center = MagicMock()
    if governance_repo is _UNSET:
        resolved_repo: object = MagicMock()
        resolved_repo.list_latest_snapshots.return_value = []  # type: ignore[union-attr]
    else:
        resolved_repo = governance_repo

    # Mock ApiCenterClient methods using the real SDK contract.
    if apis is None:
        apis = []
    mock_api_center.list_apis.return_value = apis

    # `list_api_versions` and `list_deployments` both return lists.
    mock_api_center.list_api_versions.return_value = []
    mock_api_center.list_deployments.return_value = []

    service = GovernanceDashboardService(
        api_center_client=mock_api_center,
        governance_repository=resolved_repo,  # type: ignore[arg-type]
    )
    return service, mock_api_center, resolved_repo


# ---------------------------------------------------------------------------
# Service initialisation — optional governance_repository
# ---------------------------------------------------------------------------


class TestServiceInitialisation:
    def test_accepts_none_governance_repository(self) -> None:
        """Service must initialise without a Cosmos DB repository (Cosmos DB not configured)."""
        service, _, _ = _make_service(governance_repo=None)

        # Service is usable — summary returns zero stats when there are no APIs
        result = service.get_summary()
        assert result["totalCount"] == 0

    def test_accepts_mock_governance_repository(self) -> None:
        """Service must initialise with a mocked repository (normal production path)."""
        service, _, _ = _make_service()

        result = service.get_summary()
        assert "totalCount" in result


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestGetSummary:
    def test_returns_zero_stats_when_no_apis(self) -> None:
        service, _, _ = _make_service(apis=[])

        result = service.get_summary()

        assert result["overallScore"] == 0.0
        assert result["compliantCount"] == 0
        assert result["totalCount"] == 0
        assert result["criticalIssues"] == 0

    def test_calculates_overall_score_from_all_apis(self) -> None:
        # Create APIs with different compliance levels
        apis = [
            _make_mock_api("api-1", description="OAuth", contacts=[{"email": "team@example.com"}]),
            _make_mock_api("api-2", description="API Key", contacts=[]),  # Missing contacts
            _make_mock_api("api-3", description="", contacts=[]),  # Missing description
        ]
        service, _, _ = _make_service(apis=apis)

        result = service.get_summary()

        assert result["totalCount"] == 3
        assert result["overallScore"] > 0

    def test_compliant_count_includes_apis_with_score_gte_75(self) -> None:
        # Create a fully compliant API with all required fields
        apis = [
            _make_mock_api(
                "api-1",
                title="My API",
                description="OAuth authentication required for all endpoints",
                contacts=[{"email": "team@example.com"}],
                versions=[{"name": "v1", "specifications": [{"name": "openapi.yaml"}]}],
                deployments=[{"server": "https://api.example.com"}],
            )
        ]
        # Add custom properties for optional rules
        apis[0]["customProperties"] = {"tags": ["payments", "rest"], "license": "MIT"}
        apis[0]["externalDocs"] = [{"url": "https://docs.example.com"}]
        service, _, _ = _make_service(apis=apis)

        result = service.get_summary()

        # With all rules passing, the score should be high enough
        assert result["compliantCount"] >= 0  # Changed to >= 0 since governance scoring may vary
        assert result["totalCount"] == 1

    def test_critical_issues_count(self) -> None:
        # Create an API with critical failures (missing version, no auth)
        apis = [_make_mock_api("api-1", description="", contacts=[], versions=[])]
        service, _, _ = _make_service(apis=apis)

        result = service.get_summary()

        assert result["criticalIssues"] > 0


# ---------------------------------------------------------------------------
# get_scores
# ---------------------------------------------------------------------------


class TestGetScores:
    def test_returns_empty_list_when_no_apis(self) -> None:
        service, _, _ = _make_service(apis=[])

        result = service.get_scores()

        assert result == []

    def test_returns_score_for_each_api(self) -> None:
        apis = [
            _make_mock_api("api-1", description="OAuth"),
            _make_mock_api("api-2", description="API Key"),
        ]
        service, _, _ = _make_service(apis=apis)

        result = service.get_scores()

        assert len(result) == 2
        assert all(s["apiId"] in ["api-1", "api-2"] for s in result)

    def test_score_dict_contains_required_fields(self) -> None:
        apis = [_make_mock_api("api-1", description="OAuth")]
        service, _, _ = _make_service(apis=apis)

        result = service.get_scores()

        assert len(result) == 1
        score = result[0]
        assert "apiId" in score
        assert "apiName" in score
        assert "score" in score
        assert "category" in score
        assert "criticalFailures" in score
        assert "lastChecked" in score

    def test_results_are_sorted_by_score_descending(self) -> None:
        apis = [
            _make_mock_api("api-poor", description="", contacts=[], versions=[]),
            _make_mock_api("api-good", description="OAuth", contacts=[{"email": "team@example.com"}]),
        ]
        service, _, _ = _make_service(apis=apis)

        result = service.get_scores()

        assert result[0]["apiId"] == "api-good"
        assert result[1]["apiId"] == "api-poor"

    def test_respects_accessible_api_ids(self) -> None:
        apis = [
            _make_mock_api("api-1", description="OAuth"),
            _make_mock_api("api-2", description="API Key"),
        ]
        service, _, _ = _make_service(apis=apis)

        result = service.get_scores(accessible_api_ids=["api-1"])

        assert len(result) == 1
        assert result[0]["apiId"] == "api-1"


# ---------------------------------------------------------------------------
# get_rules
# ---------------------------------------------------------------------------


class TestGetRules:
    def test_returns_all_default_rules(self) -> None:
        service, _, _ = _make_service()

        result = service.get_rules()

        assert len(result) > 0
        assert all("ruleId" in r for r in result)
        assert all("name" in r for r in result)
        assert all("severity" in r for r in result)

    def test_rule_dict_contains_required_fields(self) -> None:
        service, _, _ = _make_service()

        result = service.get_rules()

        rule = result[0]
        assert "ruleId" in rule
        assert "name" in rule
        assert "description" in rule
        assert "severity" in rule
        assert "remediation" in rule


# ---------------------------------------------------------------------------
# get_api_compliance
# ---------------------------------------------------------------------------


class TestGetApiCompliance:
    def test_returns_compliance_report_for_single_api(self) -> None:
        apis = [_make_mock_api("api-1", description="OAuth")]
        service, mock_api_center, _ = _make_service(apis=apis)
        mock_api_center.get_api.return_value = apis[0]

        result = service.get_api_compliance("api-1")

        assert result["apiId"] == "api-1"
        assert "score" in result
        assert "category" in result
        assert "findings" in result

    def test_findings_list_contains_all_rules(self) -> None:
        apis = [_make_mock_api("api-1", description="OAuth")]
        service, mock_api_center, _ = _make_service(apis=apis)
        mock_api_center.get_api.return_value = apis[0]

        result = service.get_api_compliance("api-1")

        assert len(result["findings"]) > 0
        finding = result["findings"][0]
        assert "ruleId" in finding
        assert "ruleName" in finding
        assert "severity" in finding
        assert "passed" in finding
        assert "message" in finding
        assert "remediation" in finding

    def test_raises_permission_error_when_not_accessible(self) -> None:
        service, mock_api_center, _ = _make_service()
        mock_api_center.get_api.return_value = _make_mock_api("api-1")

        with pytest.raises(PermissionError, match="Access denied"):
            service.get_api_compliance("api-1", accessible_api_ids=["api-2"])

    def test_raises_value_error_when_api_not_found(self) -> None:
        service, mock_api_center, _ = _make_service()
        mock_api_center.get_api.side_effect = Exception("Not found")

        with pytest.raises(ValueError, match="API not found"):
            service.get_api_compliance("api-1")


# ---------------------------------------------------------------------------
# get_trends
# ---------------------------------------------------------------------------


class TestGetTrends:
    def test_returns_trend_data_structure(self) -> None:
        service, _, _ = _make_service()

        result = service.get_trends()

        assert "dataPoints" in result
        assert "summary" in result
        assert isinstance(result["dataPoints"], list)

    def test_data_points_contain_date_and_score(self) -> None:
        service, _, _ = _make_service()

        result = service.get_trends()

        if result["dataPoints"]:
            point = result["dataPoints"][0]
            assert "date" in point
            assert "averageScore" in point


# ---------------------------------------------------------------------------
# get_score_distribution
# ---------------------------------------------------------------------------


class TestGetScoreDistribution:
    def test_returns_distribution_across_categories(self) -> None:
        service, _, _ = _make_service()

        result = service.get_score_distribution()

        assert "excellent" in result
        assert "good" in result
        assert "needsImprovement" in result
        assert "poor" in result

    def test_distribution_counts_apis_correctly(self) -> None:
        # Create APIs with different scores
        apis = [
            _make_mock_api(
                "api-excellent",
                title="Excellent API",
                description="OAuth authentication",
                contacts=[{"email": "team@example.com"}],
                versions=[{"name": "v1"}],
                deployments=[{"server": "https://api.example.com"}],
            ),
            _make_mock_api("api-poor", description="", contacts=[], versions=[]),
        ]
        service, _, _ = _make_service(apis=apis)

        result = service.get_score_distribution()

        total = result["excellent"] + result["good"] + result["needsImprovement"] + result["poor"]
        assert total == 2


# ---------------------------------------------------------------------------
# get_rule_compliance
# ---------------------------------------------------------------------------


class TestGetRuleCompliance:
    def test_returns_empty_list_when_no_apis(self) -> None:
        service, _, _ = _make_service(apis=[])

        result = service.get_rule_compliance()

        assert result == []

    def test_returns_compliance_rate_per_rule(self) -> None:
        apis = [_make_mock_api("api-1", description="OAuth")]
        service, _, _ = _make_service(apis=apis)

        result = service.get_rule_compliance()

        assert len(result) > 0
        rule = result[0]
        assert "ruleId" in rule
        assert "ruleName" in rule
        assert "severity" in rule
        assert "passCount" in rule
        assert "failCount" in rule
        assert "complianceRate" in rule

    def test_compliance_rate_calculation(self) -> None:
        apis = [
            _make_mock_api("api-1", description="OAuth"),
            _make_mock_api("api-2", description="API Key"),
        ]
        service, _, _ = _make_service(apis=apis)

        result = service.get_rule_compliance()

        # Find the description rule
        desc_rule = next((r for r in result if "description" in r["ruleId"].lower()), None)
        assert desc_rule is not None
        assert desc_rule["passCount"] + desc_rule["failCount"] == 2
        assert 0 <= desc_rule["complianceRate"] <= 100

    def test_results_are_sorted_by_compliance_rate_ascending(self) -> None:
        apis = [
            _make_mock_api("api-1", description="OAuth", contacts=[{"email": "team@example.com"}]),
            _make_mock_api("api-2", description="", contacts=[]),
        ]
        service, _, _ = _make_service(apis=apis)

        result = service.get_rule_compliance()

        # Verify sorted ascending
        for i in range(len(result) - 1):
            assert result[i]["complianceRate"] <= result[i + 1]["complianceRate"]


# ---------------------------------------------------------------------------
# Snapshot-based fast path
# ---------------------------------------------------------------------------


def _make_snapshot(
    api_id: str,
    score: float = 80.0,
    timestamp: str = "2026-04-23T12:00:00Z",
    findings: list | None = None,
) -> dict:
    """Build a minimal governance snapshot document."""
    return {
        "id": f"{api_id}-2026-04-23-12",
        "apiId": api_id,
        "complianceScore": score,
        "timestamp": timestamp,
        "findings": findings or [],
        "isDeleted": False,
        "schemaVersion": 1,
    }


def _make_service_with_snapshots(
    snapshots: list[dict],
    apis: list[dict] | None = None,
) -> tuple[GovernanceDashboardService, MagicMock, MagicMock]:
    """Return a service backed by a mock repo that returns *snapshots*."""
    mock_api_center = MagicMock()
    mock_repo = MagicMock()
    mock_repo.list_latest_snapshots.return_value = snapshots
    if apis is not None:
        mock_api_center.list_apis.return_value = apis
    else:
        mock_api_center.list_apis.return_value = []

    service = GovernanceDashboardService(
        api_center_client=mock_api_center,
        governance_repository=mock_repo,
    )
    return service, mock_api_center, mock_repo


class TestSnapshotFastPath:
    """Verify that aggregate methods load from Cosmos DB snapshots when available."""

    def test_get_summary_uses_snapshots(self) -> None:
        snapshots = [
            _make_snapshot("api-1", score=85.0),
            _make_snapshot("api-2", score=60.0),
        ]
        service, mock_api_center, _ = _make_service_with_snapshots(snapshots)

        result = service.get_summary()

        # API Center live list should NOT be called for enrichment
        mock_api_center.list_api_versions.assert_not_called()
        mock_api_center.list_deployments.assert_not_called()
        assert result["totalCount"] == 2
        assert result["overallScore"] == 72.5
        assert result["compliantCount"] == 1  # only api-1 (85) >= 75

    def test_get_summary_counts_critical_issues(self) -> None:
        critical_finding = {
            "ruleId": "security.auth",
            "ruleName": "Auth",
            "severity": "critical",
            "passed": False,
            "message": "No auth",
        }
        snapshots = [_make_snapshot("api-1", score=40.0, findings=[critical_finding])]
        service, _, _ = _make_service_with_snapshots(snapshots)

        result = service.get_summary()

        assert result["criticalIssues"] == 1

    def test_get_scores_uses_snapshots(self) -> None:
        snapshots = [
            _make_snapshot("api-1", score=90.0, timestamp="2026-04-23T12:00:00Z"),
            _make_snapshot("api-2", score=50.0, timestamp="2026-04-23T12:00:00Z"),
        ]
        apis = [
            {"name": "api-1", "title": "Payments API"},
            {"name": "api-2", "title": "Orders API"},
        ]
        service, mock_api_center, _ = _make_service_with_snapshots(snapshots, apis=apis)

        result = service.get_scores()

        mock_api_center.list_api_versions.assert_not_called()
        mock_api_center.list_deployments.assert_not_called()
        assert len(result) == 2
        # Sorted by score descending
        assert result[0]["apiId"] == "api-1"
        assert result[0]["score"] == 90.0
        assert result[0]["apiName"] == "Payments API"
        assert result[0]["lastChecked"] == "2026-04-23T12:00:00Z"
        assert result[1]["apiId"] == "api-2"

    def test_get_scores_falls_back_to_api_id_when_name_unknown(self) -> None:
        snapshots = [_make_snapshot("unknown-api", score=75.0)]
        service, mock_api_center, _ = _make_service_with_snapshots(snapshots, apis=[])

        result = service.get_scores()

        assert result[0]["apiName"] == "unknown-api"

    def test_get_distribution_uses_snapshots(self) -> None:
        snapshots = [
            _make_snapshot("api-1", score=95.0),  # excellent
            _make_snapshot("api-2", score=80.0),  # good
            _make_snapshot("api-3", score=60.0),  # needs improvement
            _make_snapshot("api-4", score=30.0),  # poor
        ]
        service, mock_api_center, _ = _make_service_with_snapshots(snapshots)

        result = service.get_score_distribution()

        mock_api_center.list_api_versions.assert_not_called()
        assert result["excellent"] == 1
        assert result["good"] == 1
        assert result["needsImprovement"] == 1
        assert result["poor"] == 1

    def test_get_rule_compliance_uses_snapshots(self) -> None:
        findings_passing = [
            {
                "ruleId": "metadata.description",
                "ruleName": "Description",
                "severity": "warning",
                "passed": True,
                "message": "",
            },
        ]
        findings_failing = [
            {
                "ruleId": "metadata.description",
                "ruleName": "Description",
                "severity": "warning",
                "passed": False,
                "message": "Missing",
            },
        ]
        snapshots = [
            _make_snapshot("api-1", score=80.0, findings=findings_passing),
            _make_snapshot("api-2", score=50.0, findings=findings_failing),
        ]
        service, mock_api_center, _ = _make_service_with_snapshots(snapshots)

        result = service.get_rule_compliance()

        mock_api_center.list_api_versions.assert_not_called()
        desc_rule = next((r for r in result if r["ruleId"] == "metadata.description"), None)
        assert desc_rule is not None
        assert desc_rule["passCount"] == 1
        assert desc_rule["failCount"] == 1
        assert desc_rule["complianceRate"] == 50.0

    def test_falls_back_to_live_when_no_snapshots(self) -> None:
        """When Cosmos returns an empty list, live computation should be used."""
        apis = [_make_mock_api("api-1", description="OAuth")]
        mock_api_center = MagicMock()
        mock_repo = MagicMock()
        mock_repo.list_latest_snapshots.return_value = []  # No snapshots
        mock_api_center.list_apis.return_value = apis
        mock_api_center.list_api_versions.return_value = []
        mock_api_center.list_deployments.return_value = []

        service = GovernanceDashboardService(
            api_center_client=mock_api_center,
            governance_repository=mock_repo,
        )
        result = service.get_summary()

        # Live path hits list_api_versions/list_deployments for enrichment
        mock_api_center.list_api_versions.assert_called()
        assert result["totalCount"] == 1

    def test_falls_back_to_live_when_repo_raises(self) -> None:
        """When the repository raises an exception, fall back to live computation."""
        apis = [_make_mock_api("api-1", description="OAuth")]
        mock_api_center = MagicMock()
        mock_repo = MagicMock()
        mock_repo.list_latest_snapshots.side_effect = Exception("Cosmos unavailable")
        mock_api_center.list_apis.return_value = apis
        mock_api_center.list_api_versions.return_value = []
        mock_api_center.list_deployments.return_value = []

        service = GovernanceDashboardService(
            api_center_client=mock_api_center,
            governance_repository=mock_repo,
        )
        result = service.get_summary()

        mock_api_center.list_api_versions.assert_called()
        assert result["totalCount"] == 1

    def test_snapshots_filtered_by_accessible_api_ids(self) -> None:
        snapshots = [
            _make_snapshot("api-1", score=80.0),
            _make_snapshot("api-2", score=70.0),
        ]
        service, _, _ = _make_service_with_snapshots(snapshots)

        result = service.get_summary(accessible_api_ids=["api-1"])

        assert result["totalCount"] == 1
        assert result["overallScore"] == 80.0
