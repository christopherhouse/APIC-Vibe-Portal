"""Unit tests for metadata router."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apic_vibe_portal_bff.routers import metadata


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the metadata router."""
    test_app = FastAPI()
    test_app.include_router(metadata.router)
    return test_app


@pytest.fixture
def mock_completeness_service():
    """Create a mock metadata completeness service."""
    return MagicMock()


@pytest.fixture
def mock_recommendations_service():
    """Create a mock metadata recommendations service."""
    return MagicMock()


@pytest.fixture
def client(
    app: FastAPI,
    mock_completeness_service: MagicMock,
    mock_recommendations_service: MagicMock,
) -> TestClient:
    """Create a test client with mocked services and bypassed auth."""
    app.dependency_overrides[metadata._get_completeness_service] = lambda: mock_completeness_service
    app.dependency_overrides[metadata._get_recommendations_service] = lambda: mock_recommendations_service
    app.dependency_overrides[metadata._accessible_ids_dep] = lambda: None
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/metadata/overview
# ---------------------------------------------------------------------------


class TestGetMetadataOverview:
    def test_returns_overview_data(self, client: TestClient, mock_completeness_service: MagicMock) -> None:
        mock_completeness_service.get_overview.return_value = {
            "averageScore": 72.5,
            "averageGrade": "C",
            "totalApis": 10,
            "distribution": {"A": 2, "B": 3, "C": 3, "D": 1, "F": 1},
            "dimensionAverages": [
                {"key": "basicInfo", "name": "Basic Info", "weight": 0.20, "averageScore": 80.0},
            ],
        }

        response = client.get("/api/metadata/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["averageScore"] == 72.5
        assert data["totalApis"] == 10
        assert data["distribution"]["A"] == 2


# ---------------------------------------------------------------------------
# GET /api/metadata/leaderboard
# ---------------------------------------------------------------------------


class TestGetMetadataLeaderboard:
    def test_returns_leaderboard_data(self, client: TestClient, mock_completeness_service: MagicMock) -> None:
        mock_completeness_service.get_leaderboard.return_value = {
            "top": [
                {"apiId": "api-best", "apiName": "Best API", "score": 95.0, "grade": "A"},
            ],
            "bottom": [
                {"apiId": "api-worst", "apiName": "Worst API", "score": 15.0, "grade": "F"},
            ],
        }

        response = client.get("/api/metadata/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert len(data["top"]) == 1
        assert data["top"][0]["apiId"] == "api-best"
        assert len(data["bottom"]) == 1
        assert data["bottom"][0]["apiId"] == "api-worst"


# ---------------------------------------------------------------------------
# GET /api/metadata/{api_id}/score
# ---------------------------------------------------------------------------


class TestGetMetadataScore:
    def test_returns_score_for_api(self, client: TestClient, mock_completeness_service: MagicMock) -> None:
        mock_completeness_service.get_score.return_value = {
            "apiId": "api-1",
            "apiName": "Payments API",
            "overallScore": 85.0,
            "grade": "B",
            "dimensions": [
                {"key": "basicInfo", "name": "Basic Info", "weight": 0.20, "score": 90.0},
            ],
            "lastChecked": "2026-04-20T18:00:00Z",
        }

        response = client.get("/api/metadata/api-1/score")

        assert response.status_code == 200
        data = response.json()
        assert data["apiId"] == "api-1"
        assert data["overallScore"] == 85.0
        assert data["grade"] == "B"

    def test_returns_403_when_permission_denied(self, client: TestClient, mock_completeness_service: MagicMock) -> None:
        mock_completeness_service.get_score.side_effect = PermissionError("Access denied")

        response = client.get("/api/metadata/api-1/score")

        assert response.status_code == 403

    def test_returns_404_when_api_not_found(self, client: TestClient, mock_completeness_service: MagicMock) -> None:
        mock_completeness_service.get_score.side_effect = ValueError("API not found")

        response = client.get("/api/metadata/api-1/score")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/metadata/{api_id}/recommendations
# ---------------------------------------------------------------------------


class TestGetMetadataRecommendations:
    def test_returns_recommendations_for_api(self, client: TestClient, mock_recommendations_service: MagicMock) -> None:
        mock_recommendations_service.get_recommendations.return_value = {
            "apiId": "api-1",
            "apiName": "Payments API",
            "overallScore": 65.0,
            "grade": "C",
            "recommendations": [
                {
                    "dimension": "documentation",
                    "priority": "high",
                    "title": "Add external documentation",
                    "description": "Link external docs for better discoverability.",
                }
            ],
            "generatedAt": "2026-04-20T18:00:00Z",
        }

        response = client.get("/api/metadata/api-1/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data["apiId"] == "api-1"
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["priority"] == "high"

    def test_returns_403_when_permission_denied(
        self, client: TestClient, mock_recommendations_service: MagicMock
    ) -> None:
        mock_recommendations_service.get_recommendations.side_effect = PermissionError("Access denied")

        response = client.get("/api/metadata/api-1/recommendations")

        assert response.status_code == 403

    def test_returns_404_when_api_not_found(self, client: TestClient, mock_recommendations_service: MagicMock) -> None:
        mock_recommendations_service.get_recommendations.side_effect = ValueError("API not found")

        response = client.get("/api/metadata/api-1/recommendations")

        assert response.status_code == 404
