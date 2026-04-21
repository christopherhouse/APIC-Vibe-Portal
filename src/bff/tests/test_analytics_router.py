"""Unit tests for the analytics router."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.routers import analytics


def _make_user(roles: list[str]) -> AuthenticatedUser:
    return AuthenticatedUser(oid="u1", name="Test", email="test@example.com", roles=roles)


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the analytics router."""
    test_app = FastAPI()
    test_app.include_router(analytics.router)
    return test_app


@pytest.fixture
def admin_client(app: FastAPI) -> TestClient:
    """Test client with a Portal.Admin user injected."""
    app.dependency_overrides[analytics._require_analytics_role] = lambda: _make_user(["Portal.Admin"])
    return TestClient(app)


@pytest.fixture
def maintainer_client(app: FastAPI) -> TestClient:
    """Test client with a Portal.Maintainer user injected."""
    app.dependency_overrides[analytics._require_analytics_role] = lambda: _make_user(["Portal.Maintainer"])
    return TestClient(app)


@pytest.fixture
def unauth_client(app: FastAPI) -> TestClient:
    """Test client with no role override (dependency raises 403)."""

    def _deny():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Forbidden")

    app.dependency_overrides[analytics._require_analytics_role] = _deny
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/analytics/summary
# ---------------------------------------------------------------------------


class TestGetAnalyticsSummary:
    def test_returns_200_for_admin(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/summary")
        assert response.status_code == 200

    def test_returns_200_for_maintainer(self, maintainer_client: TestClient) -> None:
        response = maintainer_client.get("/api/analytics/summary")
        assert response.status_code == 200

    def test_returns_403_for_unauthorized(self, unauth_client: TestClient) -> None:
        response = unauth_client.get("/api/analytics/summary")
        assert response.status_code == 403

    def test_response_shape(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/summary")
        data = response.json()
        assert "totalUsers" in data
        assert "totalPageViews" in data
        assert "totalSearchQueries" in data
        assert "totalChatInteractions" in data
        assert "avgSessionDurationSeconds" in data

    def test_accepts_range_param(self, admin_client: TestClient) -> None:
        for r in ("7d", "30d", "90d", "1y"):
            response = admin_client.get(f"/api/analytics/summary?time_range={r}")
            assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/analytics/usage-trends
# ---------------------------------------------------------------------------


class TestGetUsageTrends:
    def test_returns_200(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/usage-trends")
        assert response.status_code == 200

    def test_response_shape(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/usage-trends")
        data = response.json()
        assert "range" in data
        assert "dataPoints" in data
        assert isinstance(data["dataPoints"], list)

    def test_range_reflected_in_response(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/usage-trends?time_range=7d")
        assert response.json()["range"] == "7d"


# ---------------------------------------------------------------------------
# GET /api/analytics/popular-apis
# ---------------------------------------------------------------------------


class TestGetPopularApis:
    def test_returns_200(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/popular-apis")
        assert response.status_code == 200

    def test_returns_list(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/popular-apis")
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# GET /api/analytics/search-trends
# ---------------------------------------------------------------------------


class TestGetSearchTrends:
    def test_returns_200(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/search-trends")
        assert response.status_code == 200

    def test_response_shape(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/analytics/search-trends").json()
        assert "dailyVolume" in data
        assert "topQueries" in data
        assert "zeroResultQueries" in data
        assert "clickThroughRate" in data
        assert "searchModeDistribution" in data


# ---------------------------------------------------------------------------
# GET /api/analytics/user-activity
# ---------------------------------------------------------------------------


class TestGetUserActivity:
    def test_returns_200(self, admin_client: TestClient) -> None:
        response = admin_client.get("/api/analytics/user-activity")
        assert response.status_code == 200

    def test_response_shape(self, admin_client: TestClient) -> None:
        data = admin_client.get("/api/analytics/user-activity").json()
        assert "dailyActiveUsers" in data
        assert "weeklyActiveUsers" in data
        assert "avgSessionDurationSeconds" in data
        assert "featureAdoption" in data

    def test_maintainer_can_access(self, maintainer_client: TestClient) -> None:
        response = maintainer_client.get("/api/analytics/user-activity")
        assert response.status_code == 200
