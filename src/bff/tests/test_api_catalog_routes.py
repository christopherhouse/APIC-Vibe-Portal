"""Integration tests for the API catalog router endpoints.

All tests use ``httpx.AsyncClient`` against the FastAPI app with
mocked authentication (via ``validate_token``) and a mocked
:class:`ApiCatalogService` injected via ``app.dependency_overrides``.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.app import create_app
from apic_vibe_portal_bff.clients.api_center_client import (
    ApiCenterClientError,
    ApiCenterNotFoundError,
)
from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.models.api_center import (
    ApiDefinition,
    ApiDeployment,
    ApiEnvironment,
    ApiSpecification,
    ApiVersion,
    DeploymentServer,
    EnvironmentKind,
    PaginatedResponse,
    PaginationMeta,
)
from apic_vibe_portal_bff.routers.api_catalog import _get_service

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


def _make_api(name: str = "petstore-api", title: str = "Petstore API", **kwargs) -> ApiDefinition:
    """Create a test ``ApiDefinition``."""
    defaults = {
        "id": f"/apis/{name}",
        "name": name,
        "title": title,
        "description": f"A sample {name} API",
        "kind": "rest",
        "lifecycle_stage": "production",
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-03-20T14:30:00",
    }
    defaults.update(kwargs)
    return ApiDefinition(**defaults)


def _make_version(name: str = "v1", title: str = "Version 1") -> ApiVersion:
    return ApiVersion(
        id=f"/versions/{name}",
        name=name,
        title=title,
        lifecycle_stage="production",
        created_at="2024-01-15T10:00:00",
        updated_at="2024-03-20T14:30:00",
    )


def _make_deployment(name: str = "dep-v1", title: str = "v1 Deployment") -> ApiDeployment:
    return ApiDeployment(
        id=f"/deployments/{name}",
        title=title,
        environment=ApiEnvironment(
            id="/environments/prod",
            name="prod",
            title="Production",
            kind=EnvironmentKind.PRODUCTION,
        ),
        server=DeploymentServer(runtime_uri=["https://api.example.com/v1"]),
        created_at="2024-01-15T10:00:00",
        updated_at="2024-03-20T14:30:00",
    )


def _make_environment(name: str = "prod", title: str = "Production") -> ApiEnvironment:
    return ApiEnvironment(
        id=f"/environments/{name}",
        name=name,
        title=title,
        kind=EnvironmentKind.PRODUCTION,
    )


def _make_spec(name: str = "openapi") -> ApiSpecification:
    return ApiSpecification(
        id=f"/specs/{name}",
        name=name,
        title="OpenAPI Definition",
        specification_type="openapi",
        specification_version="3.0.1",
        content='{"openapi": "3.0.1", "info": {"title": "Petstore", "version": "1.0"}}',
    )


def _paginated(items: list[ApiDefinition], page: int = 1, page_size: int = 20) -> PaginatedResponse:
    total = len(items)
    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=math.ceil(total / page_size) if total else 0,
        ),
    )


@pytest.fixture
def mock_service():
    """Return a ``MagicMock`` for ``ApiCatalogService``."""
    return MagicMock()


@pytest.fixture
async def client(mock_service):
    """Yield an async ``httpx`` client with mocked service + auth."""
    app = create_app()
    app.dependency_overrides[_get_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    with patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER):
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


# ===================================================================
# GET /api/catalog — List APIs
# ===================================================================


class TestListApis:
    """Tests for ``GET /api/catalog``."""

    @pytest.mark.asyncio
    async def test_returns_paginated_list(self, client: AsyncClient, mock_service: MagicMock) -> None:
        apis = [_make_api("api-1", "API One"), _make_api("api-2", "API Two")]
        mock_service.list_apis.return_value = _paginated(apis)

        resp = await client.get("/api/catalog", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert len(body["data"]) == 2
        assert body["meta"]["page"] == 1
        assert body["meta"]["totalCount"] == 2

    @pytest.mark.asyncio
    async def test_default_pagination(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([])

        await client.get("/api/catalog", headers=_AUTH_HEADERS)

        mock_service.list_apis.assert_called_once_with(
            page=1, page_size=20, filter_str=None, sort_field=None, sort_reverse=False
        )

    @pytest.mark.asyncio
    async def test_custom_pagination(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([], page=2, page_size=50)

        await client.get("/api/catalog?page=2&pageSize=50", headers=_AUTH_HEADERS)

        mock_service.list_apis.assert_called_once_with(
            page=2, page_size=50, filter_str=None, sort_field=None, sort_reverse=False
        )

    @pytest.mark.asyncio
    async def test_max_page_size_enforced(self, client: AsyncClient, mock_service: MagicMock) -> None:
        resp = await client.get("/api/catalog?pageSize=200", headers=_AUTH_HEADERS)
        assert resp.status_code == 422  # FastAPI validation error

    @pytest.mark.asyncio
    async def test_page_must_be_positive(self, client: AsyncClient, mock_service: MagicMock) -> None:
        resp = await client.get("/api/catalog?page=0", headers=_AUTH_HEADERS)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_filter_by_lifecycle(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([_make_api(lifecycle_stage="production")])

        resp = await client.get("/api/catalog?lifecycle=production", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        call_kwargs = mock_service.list_apis.call_args.kwargs
        assert "lifecycleStage" in call_kwargs["filter_str"]
        assert "'production'" in call_kwargs["filter_str"]

    @pytest.mark.asyncio
    async def test_filter_by_kind(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([_make_api(kind="graphql")])

        resp = await client.get("/api/catalog?kind=graphql", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        call_kwargs = mock_service.list_apis.call_args.kwargs
        assert "kind" in call_kwargs["filter_str"]
        assert "'graphql'" in call_kwargs["filter_str"]

    @pytest.mark.asyncio
    async def test_filter_by_lifecycle_and_kind(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([])

        resp = await client.get("/api/catalog?lifecycle=production&kind=rest", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        filter_str = mock_service.list_apis.call_args.kwargs["filter_str"]
        assert "lifecycleStage" in filter_str
        assert "kind" in filter_str
        assert " and " in filter_str

    @pytest.mark.asyncio
    async def test_sort_by_name_asc(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([_make_api("alpha-api", "Alpha")])

        resp = await client.get("/api/catalog?sort=name&direction=asc", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        call_kwargs = mock_service.list_apis.call_args.kwargs
        assert call_kwargs["sort_field"] == "name"
        assert call_kwargs["sort_reverse"] is False

    @pytest.mark.asyncio
    async def test_sort_by_name_desc(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([_make_api("alpha-api", "Alpha")])

        resp = await client.get("/api/catalog?sort=name&direction=desc", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        call_kwargs = mock_service.list_apis.call_args.kwargs
        assert call_kwargs["sort_field"] == "name"
        assert call_kwargs["sort_reverse"] is True

    @pytest.mark.asyncio
    async def test_invalid_lifecycle_returns_422(self, client: AsyncClient, mock_service: MagicMock) -> None:
        resp = await client.get("/api/catalog?lifecycle=invalid_stage", headers=_AUTH_HEADERS)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_sort_returns_422(self, client: AsyncClient, mock_service: MagicMock) -> None:
        resp = await client.get("/api/catalog?sort=invalid_field", headers=_AUTH_HEADERS)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_service_error_returns_error_envelope(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.side_effect = ApiCenterClientError("Service unavailable", status_code=503)

        resp = await client.get("/api/catalog", headers=_AUTH_HEADERS)

        assert resp.status_code == 503
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "CATALOG_ERROR"

    @pytest.mark.asyncio
    async def test_response_envelope_structure(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([_make_api()])

        resp = await client.get("/api/catalog", headers=_AUTH_HEADERS)

        body = resp.json()
        assert "data" in body
        assert "meta" in body
        meta = body["meta"]
        assert "page" in meta
        assert "pageSize" in meta
        assert "totalCount" in meta
        assert "totalPages" in meta

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, mock_service: MagicMock) -> None:
        """Requests without Authorization header get 401 from auth middleware."""
        resp = await client.get("/api/catalog")
        assert resp.status_code == 401


# ===================================================================
# GET /api/catalog/{api_id} — Get API Detail
# ===================================================================


class TestGetApi:
    """Tests for ``GET /api/catalog/{api_id}``."""

    @pytest.mark.asyncio
    async def test_returns_api_detail(self, client: AsyncClient, mock_service: MagicMock) -> None:
        api = _make_api("petstore-api", "Petstore API")
        mock_service.get_api.return_value = api

        resp = await client.get("/api/catalog/petstore-api", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["name"] == "petstore-api"
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.get_api.side_effect = ApiCenterNotFoundError("api/nonexistent")

        resp = await client.get("/api/catalog/nonexistent", headers=_AUTH_HEADERS)

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_service_error_returns_error_envelope(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.get_api.side_effect = ApiCenterClientError("Internal error", status_code=500)

        resp = await client.get("/api/catalog/some-api", headers=_AUTH_HEADERS)

        assert resp.status_code == 500


# ===================================================================
# GET /api/catalog/{api_id}/versions — List API Versions
# ===================================================================


class TestListApiVersions:
    """Tests for ``GET /api/catalog/{api_id}/versions``."""

    @pytest.mark.asyncio
    async def test_returns_versions_list(self, client: AsyncClient, mock_service: MagicMock) -> None:
        versions = [_make_version("v1", "Version 1"), _make_version("v2", "Version 2")]
        mock_service.list_api_versions.return_value = versions

        resp = await client.get("/api/catalog/petstore-api/versions", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["data"][0]["name"] == "v1"
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_api_versions.side_effect = ApiCenterNotFoundError("api/nonexistent/versions")

        resp = await client.get("/api/catalog/nonexistent/versions", headers=_AUTH_HEADERS)

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_versions_list(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_api_versions.return_value = []

        resp = await client.get("/api/catalog/petstore-api/versions", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["data"] == []


# ===================================================================
# GET /api/catalog/{api_id}/versions/{version_id}/definition
# ===================================================================


class TestGetApiDefinition:
    """Tests for ``GET /api/catalog/{api_id}/versions/{version_id}/definition``."""

    @pytest.mark.asyncio
    async def test_returns_spec(self, client: AsyncClient, mock_service: MagicMock) -> None:
        spec = _make_spec()
        mock_service.get_api_definition.return_value = spec

        resp = await client.get("/api/catalog/petstore-api/versions/v1/definition", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["name"] == "openapi"
        assert body["data"]["content"] is not None
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.get_api_definition.side_effect = ApiCenterNotFoundError("definition not found")

        resp = await client.get("/api/catalog/petstore-api/versions/v99/definition", headers=_AUTH_HEADERS)

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_service_error_returns_error_envelope(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.get_api_definition.side_effect = ApiCenterClientError("Oops", status_code=500)

        resp = await client.get("/api/catalog/petstore-api/versions/v1/definition", headers=_AUTH_HEADERS)

        assert resp.status_code == 500


# ===================================================================
# GET /api/catalog/{api_id}/deployments — List API Deployments
# ===================================================================


class TestListApiDeployments:
    """Tests for ``GET /api/catalog/{api_id}/deployments``."""

    @pytest.mark.asyncio
    async def test_returns_deployments_list(self, client: AsyncClient, mock_service: MagicMock) -> None:
        deployments = [_make_deployment("dep-v1"), _make_deployment("dep-v2", "v2 Deployment")]
        mock_service.list_deployments.return_value = deployments

        resp = await client.get("/api/catalog/petstore-api/deployments", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_deployments.side_effect = ApiCenterNotFoundError("api/nonexistent/deployments")

        resp = await client.get("/api/catalog/nonexistent/deployments", headers=_AUTH_HEADERS)

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_deployments(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_deployments.return_value = []

        resp = await client.get("/api/catalog/petstore-api/deployments", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["data"] == []


# ===================================================================
# GET /api/environments — List Environments
# ===================================================================


class TestListEnvironments:
    """Tests for ``GET /api/environments``."""

    @pytest.mark.asyncio
    async def test_returns_environments_list(self, client: AsyncClient, mock_service: MagicMock) -> None:
        envs = [
            _make_environment("dev", "Development"),
            _make_environment("prod", "Production"),
        ]
        mock_service.list_environments.return_value = envs

        resp = await client.get("/api/environments", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["data"][0]["name"] == "dev"
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_empty_environments(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_environments.return_value = []

        resp = await client.get("/api/environments", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_service_error_returns_error_envelope(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_environments.side_effect = ApiCenterClientError("Boom", status_code=503)

        resp = await client.get("/api/environments", headers=_AUTH_HEADERS)

        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == "CATALOG_ERROR"


# ===================================================================
# Cross-cutting: response envelope consistency
# ===================================================================


class TestResponseEnvelope:
    """Verify all endpoints return the standard ``{data, meta}`` envelope."""

    @pytest.mark.asyncio
    async def test_list_endpoint_has_meta(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_apis.return_value = _paginated([_make_api()])

        resp = await client.get("/api/catalog", headers=_AUTH_HEADERS)
        body = resp.json()

        assert "data" in body
        assert "meta" in body
        assert body["meta"] is not None

    @pytest.mark.asyncio
    async def test_detail_endpoint_no_meta(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.get_api.return_value = _make_api()

        resp = await client.get("/api/catalog/petstore-api", headers=_AUTH_HEADERS)
        body = resp.json()

        assert "data" in body
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_versions_endpoint_no_meta(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_api_versions.return_value = [_make_version()]

        resp = await client.get("/api/catalog/petstore-api/versions", headers=_AUTH_HEADERS)
        body = resp.json()

        assert "data" in body
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_deployments_endpoint_no_meta(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_deployments.return_value = [_make_deployment()]

        resp = await client.get("/api/catalog/petstore-api/deployments", headers=_AUTH_HEADERS)
        body = resp.json()

        assert "data" in body
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_environments_endpoint_no_meta(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.list_environments.return_value = [_make_environment()]

        resp = await client.get("/api/environments", headers=_AUTH_HEADERS)
        body = resp.json()

        assert "data" in body
        assert body["meta"] is None

    @pytest.mark.asyncio
    async def test_spec_endpoint_no_meta(self, client: AsyncClient, mock_service: MagicMock) -> None:
        mock_service.get_api_definition.return_value = _make_spec()

        resp = await client.get("/api/catalog/petstore-api/versions/v1/definition", headers=_AUTH_HEADERS)
        body = resp.json()

        assert "data" in body
        assert body["meta"] is None
