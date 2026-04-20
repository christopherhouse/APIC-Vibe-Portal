"""Integration tests for the API comparison router endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.app import create_app
from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.models.api_center import ApiDefinition
from apic_vibe_portal_bff.routers.api_compare import _get_compare_service
from apic_vibe_portal_bff.services.api_compare_service import (
    AspectComparison,
    AspectValue,
    CompareApiSummary,
    CompareResponse,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_MOCK_USER = AuthenticatedUser(
    oid="test-user",
    name="Test User",
    email="test@example.com",
    roles=["Portal.User"],
    claims={},
)

_AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def _make_compare_response(ai_analysis: str | None = None) -> CompareResponse:
    return CompareResponse(
        apis=[
            CompareApiSummary(
                id="/apis/api-1",
                name="api-1",
                title="API One",
                description="First API",
                kind="rest",
                lifecycle_stage="production",
            ),
            CompareApiSummary(
                id="/apis/api-2",
                name="api-2",
                title="API Two",
                description="Second API",
                kind="graphql",
                lifecycle_stage="development",
            ),
        ],
        aspects=[
            AspectComparison(
                aspect="metadata.kind",
                label="API Kind",
                values=[
                    AspectValue(value="rest", display="rest"),
                    AspectValue(value="graphql", display="graphql"),
                ],
                all_equal=False,
            )
        ],
        similarity_score=0.3,
        ai_analysis=ai_analysis,
    )


@pytest.fixture
def mock_compare_service():
    return MagicMock()


@pytest.fixture
async def client(mock_compare_service):
    app = create_app()
    app.dependency_overrides[_get_compare_service] = lambda: mock_compare_service

    transport = ASGITransport(app=app)
    with patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER):
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


# ---------------------------------------------------------------------------
# POST /api/compare
# ---------------------------------------------------------------------------


class TestCompareEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200_with_valid_request(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        mock_compare_service.compare.return_value = _make_compare_response()

        resp = await client.post(
            "/api/compare",
            json={"apiIds": ["api-1", "api-2"]},
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "apis" in body
        assert "aspects" in body
        assert len(body["apis"]) == 2

    @pytest.mark.asyncio
    async def test_returns_422_for_single_api_id(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        resp = await client.post(
            "/api/compare",
            json={"apiIds": ["api-1"]},
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_422_for_more_than_five_ids(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        resp = await client.post(
            "/api/compare",
            json={"apiIds": ["api-1", "api-2", "api-3", "api-4", "api-5", "api-6"]},
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_passes_aspects_to_service(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        mock_compare_service.compare.return_value = _make_compare_response()

        await client.post(
            "/api/compare",
            json={"apiIds": ["api-1", "api-2"], "aspects": ["metadata", "versions"]},
            headers=_AUTH_HEADERS,
        )

        call_kwargs = mock_compare_service.compare.call_args
        assert "metadata" in str(call_kwargs) or "aspects" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        resp = await client.post(
            "/api/compare",
            json={"apiIds": ["api-1", "api-2"]},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_includes_similarity_score(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        mock_compare_service.compare.return_value = _make_compare_response()

        resp = await client.post(
            "/api/compare",
            json={"apiIds": ["api-1", "api-2"]},
            headers=_AUTH_HEADERS,
        )

        body = resp.json()
        assert "similarityScore" in body
        assert body["similarityScore"] == 0.3

    @pytest.mark.asyncio
    async def test_returns_500_on_service_error(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        mock_compare_service.compare.side_effect = RuntimeError("unexpected")

        resp = await client.post(
            "/api/compare",
            json={"apiIds": ["api-1", "api-2"]},
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 500
        body = resp.json()
        assert body["error"]["code"] == "COMPARE_ERROR"


# ---------------------------------------------------------------------------
# POST /api/compare/ai-analysis
# ---------------------------------------------------------------------------


class TestCompareAiAnalysisEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200_with_ai_analysis(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        mock_compare_service.compare_with_ai.return_value = _make_compare_response(
            ai_analysis="This is an AI analysis."
        )

        resp = await client.post(
            "/api/compare/ai-analysis",
            json={"apiIds": ["api-1", "api-2"]},
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["aiAnalysis"] == "This is an AI analysis."

    @pytest.mark.asyncio
    async def test_returns_422_for_single_api_id(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        resp = await client.post(
            "/api/compare/ai-analysis",
            json={"apiIds": ["api-1"]},
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ai_analysis_null_when_not_available(
        self, client: AsyncClient, mock_compare_service: MagicMock
    ) -> None:
        mock_compare_service.compare_with_ai.return_value = _make_compare_response(ai_analysis=None)

        resp = await client.post(
            "/api/compare/ai-analysis",
            json={"apiIds": ["api-1", "api-2"]},
            headers=_AUTH_HEADERS,
        )

        body = resp.json()
        assert body["aiAnalysis"] is None
