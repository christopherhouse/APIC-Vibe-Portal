"""Unit tests for governance router."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apic_vibe_portal_bff.routers import governance


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the governance router."""
    test_app = FastAPI()
    test_app.include_router(governance.router)
    return test_app


@pytest.fixture
def mock_service():
    """Create a mock governance dashboard service."""
    return MagicMock()


@pytest.fixture
def client(app: FastAPI, mock_service: MagicMock) -> TestClient:
    """Create a test client with mocked service."""
    app.dependency_overrides[governance._get_service] = lambda: mock_service
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/governance/summary
# ---------------------------------------------------------------------------


class TestGetGovernanceSummary:
    def test_returns_summary_data(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_summary.return_value = {
            "overallScore": 75.5,
            "compliantCount": 8,
            "totalCount": 10,
            "criticalIssues": 2,
            "improvement": 2.5,
        }

        response = client.get("/api/governance/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["overallScore"] == 75.5
        assert data["compliantCount"] == 8
        assert data["totalCount"] == 10


# ---------------------------------------------------------------------------
# GET /api/governance/scores
# ---------------------------------------------------------------------------


class TestGetGovernanceScores:
    def test_returns_scores_list(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_scores.return_value = [
            {
                "apiId": "api-1",
                "apiName": "Payments API",
                "score": 85.0,
                "category": "Good",
                "criticalFailures": 0,
                "lastChecked": "2026-04-20T18:00:00Z",
            }
        ]

        response = client.get("/api/governance/scores")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["apiId"] == "api-1"


# ---------------------------------------------------------------------------
# GET /api/governance/rules
# ---------------------------------------------------------------------------


class TestGetGovernanceRules:
    def test_returns_rules_list(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_rules.return_value = [
            {
                "ruleId": "metadata.description",
                "name": "API Description Required",
                "description": "The API must have a description",
                "severity": "warning",
                "remediation": "Add a description",
            }
        ]

        response = client.get("/api/governance/rules")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ruleId"] == "metadata.description"


# ---------------------------------------------------------------------------
# GET /api/governance/apis/{api_id}/compliance
# ---------------------------------------------------------------------------


class TestGetApiCompliance:
    def test_returns_compliance_report(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_api_compliance.return_value = {
            "apiId": "api-1",
            "apiName": "Payments API",
            "score": 85.0,
            "category": "Good",
            "criticalFailures": 0,
            "findings": [],
            "lastChecked": "2026-04-20T18:00:00Z",
        }

        response = client.get("/api/governance/apis/api-1/compliance")

        assert response.status_code == 200
        data = response.json()
        assert data["apiId"] == "api-1"

    def test_returns_403_when_permission_denied(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_api_compliance.side_effect = PermissionError("Access denied")

        response = client.get("/api/governance/apis/api-1/compliance")

        assert response.status_code == 403

    def test_returns_404_when_api_not_found(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_api_compliance.side_effect = ValueError("API not found")

        response = client.get("/api/governance/apis/api-1/compliance")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/governance/trends
# ---------------------------------------------------------------------------


class TestGetGovernanceTrends:
    def test_returns_trend_data(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_trends.return_value = {
            "dataPoints": [
                {"date": "2026-03-20T00:00:00Z", "averageScore": 73.0},
                {"date": "2026-04-20T00:00:00Z", "averageScore": 75.0},
            ],
            "summary": {"startScore": 73.0, "endScore": 75.0, "change": 2.0},
        }

        response = client.get("/api/governance/trends")

        assert response.status_code == 200
        data = response.json()
        assert len(data["dataPoints"]) == 2

    def test_accepts_days_parameter(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_trends.return_value = {"dataPoints": [], "summary": {}}

        response = client.get("/api/governance/trends?days=60")

        assert response.status_code == 200
        mock_service.get_trends.assert_called_once()


# ---------------------------------------------------------------------------
# GET /api/governance/distribution
# ---------------------------------------------------------------------------


class TestGetScoreDistribution:
    def test_returns_distribution_data(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_score_distribution.return_value = {
            "excellent": 2,
            "good": 3,
            "needsImprovement": 4,
            "poor": 1,
        }

        response = client.get("/api/governance/distribution")

        assert response.status_code == 200
        data = response.json()
        assert data["excellent"] == 2
        assert data["good"] == 3


# ---------------------------------------------------------------------------
# GET /api/governance/rule-compliance
# ---------------------------------------------------------------------------


class TestGetRuleCompliance:
    def test_returns_rule_compliance_data(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_rule_compliance.return_value = [
            {
                "ruleId": "metadata.description",
                "ruleName": "API Description Required",
                "severity": "warning",
                "passCount": 8,
                "failCount": 2,
                "complianceRate": 80.0,
            }
        ]

        response = client.get("/api/governance/rule-compliance")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ruleId"] == "metadata.description"
        assert data[0]["complianceRate"] == 80.0
