"""Unit tests for the analytics router."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.middleware.rbac import get_current_user
from apic_vibe_portal_bff.routers import analytics
from apic_vibe_portal_bff.services.analytics_service import AnalyticsService


def _make_user(roles: list[str]) -> AuthenticatedUser:
    return AuthenticatedUser(oid="u1", name="Test", email="test@example.com", roles=roles)


def _no_repo_service() -> AnalyticsService:
    """Return an AnalyticsService without a Cosmos repository for unit tests."""
    return AnalyticsService()


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the analytics router."""
    test_app = FastAPI()
    test_app.include_router(analytics.router)
    # Override the service factory so tests never attempt a Cosmos connection.
    test_app.dependency_overrides[analytics._get_service] = _no_repo_service
    return test_app


@pytest.fixture
def admin_client(app: FastAPI) -> TestClient:
    """Test client with a Portal.Admin user injected."""
    app.dependency_overrides[analytics._require_analytics_role] = lambda: _make_user(["Portal.Admin"])
    app.dependency_overrides[get_current_user] = lambda: _make_user(["Portal.Admin"])
    return TestClient(app)


@pytest.fixture
def maintainer_client(app: FastAPI) -> TestClient:
    """Test client with a Portal.Maintainer user injected."""
    app.dependency_overrides[analytics._require_analytics_role] = lambda: _make_user(["Portal.Maintainer"])
    app.dependency_overrides[get_current_user] = lambda: _make_user(["Portal.Maintainer"])
    return TestClient(app)


@pytest.fixture
def regular_client(app: FastAPI) -> TestClient:
    """Test client with a regular authenticated user (no admin/maintainer role)."""
    app.dependency_overrides[get_current_user] = lambda: _make_user(["Portal.User"])
    return TestClient(app)


@pytest.fixture
def unauth_client(app: FastAPI) -> TestClient:
    """Test client that exercises default unauthenticated behavior.

    The ``get_current_user`` dependency raises 401 when no user is present
    in request state (no auth middleware is mounted in the test app).
    The analytics role dependency is also forced to 403 for the admin-only
    GET endpoints.
    """

    def _deny_role():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Forbidden")

    # Only override the analytics role guard — GET endpoints need it.
    # The POST /events endpoint only requires get_current_user, which will
    # naturally raise 401 since no auth middleware sets request.state.user.
    app.dependency_overrides[analytics._require_analytics_role] = _deny_role
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/analytics/events
# ---------------------------------------------------------------------------

_VALID_BATCH = {
    "events": [
        {
            "event": {"type": "page_view", "page": "/catalog"},
            "clientTimestamp": "2026-04-21T12:00:00Z",
            "pagePath": "/catalog",
            "sessionId": "sess-1",
        }
    ]
}


class TestPostAnalyticsEvents:
    def test_returns_202_for_authenticated_user(self, regular_client: TestClient) -> None:
        response = regular_client.post("/api/analytics/events", json=_VALID_BATCH)
        assert response.status_code == 202

    def test_returns_202_for_admin_user(self, admin_client: TestClient) -> None:
        response = admin_client.post("/api/analytics/events", json=_VALID_BATCH)
        assert response.status_code == 202

    def test_response_contains_accepted_count(self, regular_client: TestClient) -> None:
        response = regular_client.post("/api/analytics/events", json=_VALID_BATCH)
        data = response.json()
        assert "accepted" in data
        assert data["accepted"] == 1

    def test_accepts_multiple_events(self, regular_client: TestClient) -> None:
        batch = {
            "events": [
                {
                    "event": {"type": "page_view", "page": f"/page-{i}"},
                    "clientTimestamp": "2026-04-21T12:00:00Z",
                    "pagePath": f"/page-{i}",
                }
                for i in range(5)
            ]
        }
        response = regular_client.post("/api/analytics/events", json=batch)
        assert response.status_code == 202
        assert response.json()["accepted"] == 5

    def test_returns_422_for_empty_events_list(self, regular_client: TestClient) -> None:
        response = regular_client.post("/api/analytics/events", json={"events": []})
        assert response.status_code == 422

    def test_returns_422_for_missing_event_type(self, regular_client: TestClient) -> None:
        bad_batch = {
            "events": [
                {
                    "event": {"page": "/catalog"},  # missing 'type'
                    "clientTimestamp": "2026-04-21T12:00:00Z",
                    "pagePath": "/catalog",
                }
            ]
        }
        response = regular_client.post("/api/analytics/events", json=bad_batch)
        assert response.status_code == 422

    def test_returns_401_for_unauthenticated_request(self, unauth_client: TestClient) -> None:
        response = unauth_client.post("/api/analytics/events", json=_VALID_BATCH)
        assert response.status_code == 401

    def test_accepts_api_view_event(self, regular_client: TestClient) -> None:
        batch = {
            "events": [
                {
                    "event": {"type": "api_view", "apiId": "payments-api", "source": "search"},
                    "clientTimestamp": "2026-04-21T12:00:00Z",
                    "pagePath": "/api/payments-api",
                }
            ]
        }
        response = regular_client.post("/api/analytics/events", json=batch)
        assert response.status_code == 202
        assert response.json()["accepted"] == 1

    def test_accepts_search_query_event(self, regular_client: TestClient) -> None:
        batch = {
            "events": [
                {
                    "event": {
                        "type": "search_query",
                        "queryHash": "abc123",
                        "queryLength": 10,
                        "resultCount": 5,
                    },
                    "clientTimestamp": "2026-04-21T12:00:00Z",
                    "pagePath": "/search",
                }
            ]
        }
        response = regular_client.post("/api/analytics/events", json=batch)
        assert response.status_code == 202

    def test_returns_422_for_event_type_exceeding_max_length(self, regular_client: TestClient) -> None:
        batch = {
            "events": [
                {
                    "event": {"type": "x" * 65},
                    "clientTimestamp": "2026-04-21T12:00:00Z",
                    "pagePath": "/search",
                }
            ]
        }
        response = regular_client.post("/api/analytics/events", json=batch)
        assert response.status_code == 422

    def test_returns_422_for_extra_field_exceeding_max_length(self, regular_client: TestClient) -> None:
        batch = {
            "events": [
                {
                    "event": {"type": "page_view", "page": "x" * 501},
                    "clientTimestamp": "2026-04-21T12:00:00Z",
                    "pagePath": "/",
                }
            ]
        }
        response = regular_client.post("/api/analytics/events", json=batch)
        assert response.status_code == 422

    def test_returns_422_for_too_many_extra_fields(self, regular_client: TestClient) -> None:
        extra_fields = {f"field_{i}": f"value_{i}" for i in range(21)}
        batch = {
            "events": [
                {
                    "event": {"type": "page_view", **extra_fields},
                    "clientTimestamp": "2026-04-21T12:00:00Z",
                    "pagePath": "/",
                }
            ]
        }
        response = regular_client.post("/api/analytics/events", json=batch)
        assert response.status_code == 422


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
