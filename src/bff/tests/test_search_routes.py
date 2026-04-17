"""Integration tests for the search router endpoints.

All tests use ``httpx.AsyncClient`` against the FastAPI app with
mocked authentication (via ``validate_token``) and a mocked
:class:`SearchService` injected via ``app.dependency_overrides``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.app import create_app
from apic_vibe_portal_bff.clients.ai_search_client import AISearchClientError
from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.models.search import (
    SearchDocument,
    SearchFacet,
    SearchFacets,
    SearchFacetValue,
    SearchResponse,
    SearchResult,
    SuggestResponse,
    SuggestResult,
)
from apic_vibe_portal_bff.routers.search import _get_search_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MOCK_USER = AuthenticatedUser(
    oid="test-user",
    name="Test User",
    email="test@example.com",
    roles=["Portal.User"],
    claims={},
)

_AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def _make_search_response(
    count: int = 1,
    query_duration: float = 5.0,
) -> SearchResponse:
    """Create a test SearchResponse."""
    doc = SearchDocument(
        id="1",
        apiName="petstore",
        title="Petstore API",
        description="A sample API",
        kind="rest",
        lifecycleStage="production",
    )
    result = SearchResult(
        document=doc,
        score=1.5,
        highlights={"title": ["<em>Petstore</em> API"]},
        captions=["The Petstore API manages pets"],
    )
    facets = SearchFacets(
        facets=[
            SearchFacet(field="kind", values=[SearchFacetValue(value="rest", count=1)]),
        ]
    )
    return SearchResponse(
        items=[result],
        totalCount=count,
        facets=facets,
        queryDuration=query_duration,
    )


def _make_suggest_response() -> SuggestResponse:
    """Create a test SuggestResponse."""
    return SuggestResponse(
        suggestions=[
            SuggestResult(text="Petstore API", apiName="petstore"),
        ],
        query_prefix="pet",
    )


@pytest.fixture
def app():
    """Return a fresh FastAPI application instance with mocked service."""
    application = create_app()
    mock_service = MagicMock()
    application.dependency_overrides[_get_search_service] = lambda: mock_service
    return application


@pytest.fixture
def mock_service(app):
    """Return the mocked SearchService from the app overrides."""
    return app.dependency_overrides[_get_search_service]()


@pytest.fixture
async def client(app):
    """Yield an async httpx client bound to the test application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ---------------------------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_search_returns_results(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.search.return_value = _make_search_response()

        response = await client.post(
            "/api/search",
            json={"query": "petstore"},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["totalCount"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["document"]["apiName"] == "petstore"
        assert data["items"][0]["score"] == 1.5
        assert data["queryDuration"] == 5.0

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_search_with_filters(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.search.return_value = _make_search_response()

        response = await client.post(
            "/api/search",
            json={
                "query": "api",
                "filters": {
                    "kind": ["rest"],
                    "lifecycleStage": ["production"],
                },
            },
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        mock_service.search.assert_called_once()

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_search_with_pagination(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.search.return_value = _make_search_response(count=50)

        response = await client.post(
            "/api/search",
            json={
                "query": "api",
                "pagination": {"page": 2, "pageSize": 10},
            },
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["totalCount"] == 50

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_search_empty_query(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.search.return_value = SearchResponse(
            items=[],
            totalCount=0,
            facets=SearchFacets(facets=[]),
            queryDuration=1.0,
        )

        response = await client.post(
            "/api/search",
            json={"query": ""},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["totalCount"] == 0

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_search_returns_facets(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.search.return_value = _make_search_response()

        response = await client.post(
            "/api/search",
            json={"query": "test"},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["facets"] is not None
        assert len(data["facets"]["facets"]) == 1
        assert data["facets"]["facets"][0]["field"] == "kind"

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_search_returns_highlights(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.search.return_value = _make_search_response()

        response = await client.post(
            "/api/search",
            json={"query": "petstore"},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["highlights"]["title"] == ["<em>Petstore</em> API"]

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_search_returns_captions(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.search.return_value = _make_search_response()

        response = await client.post(
            "/api/search",
            json={"query": "petstore"},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["captions"] == ["The Petstore API manages pets"]

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_search_service_error(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.search.side_effect = AISearchClientError("Service error", status_code=500)

        response = await client.post(
            "/api/search",
            json={"query": "test"},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "SEARCH_ERROR"

    async def test_search_requires_auth(self, client):
        response = await client.post("/api/search", json={"query": "test"})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/search/suggest
# ---------------------------------------------------------------------------


class TestSuggestEndpoint:
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_suggest_returns_suggestions(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.suggest.return_value = _make_suggest_response()

        response = await client.get(
            "/api/search/suggest",
            params={"q": "pet"},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["text"] == "Petstore API"
        assert data["suggestions"][0]["apiName"] == "petstore"

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_suggest_service_error(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER
        mock_service.suggest.side_effect = AISearchClientError("Error", status_code=500)

        response = await client.get(
            "/api/search/suggest",
            params={"q": "test"},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "SEARCH_ERROR"

    async def test_suggest_requires_auth(self, client):
        response = await client.get("/api/search/suggest", params={"q": "test"})
        assert response.status_code == 401

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_suggest_returns_empty_for_missing_q(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER

        response = await client.get(
            "/api/search/suggest",
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []
        mock_service.suggest.assert_not_called()

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_suggest_returns_empty_for_short_q(self, mock_validate, client, mock_service):
        mock_validate.return_value = _MOCK_USER

        response = await client.get(
            "/api/search/suggest",
            params={"q": "a"},
            headers=_AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []
        mock_service.suggest.assert_not_called()
