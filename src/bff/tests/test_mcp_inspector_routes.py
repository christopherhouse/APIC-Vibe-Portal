"""Integration tests for the MCP Inspector proxy routes.

All tests use ``httpx.AsyncClient`` against the FastAPI app with mocked
authentication and a mocked ``ApiCatalogService`` injected via
``app.dependency_overrides``.  The upstream MCP server is also mocked
using ``unittest.mock.patch`` so no real network calls are made.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.app import create_app
from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.models.api_center import (
    ApiDefinition,
    ApiDeployment,
    ApiEnvironment,
    ApiKind,
    DeploymentServer,
    EnvironmentKind,
)
from apic_vibe_portal_bff.routers.api_catalog import _get_service

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

_MOCK_USER = AuthenticatedUser(
    oid="test-user",
    name="Test User",
    email="test@example.com",
    roles=["Portal.User"],
    claims={},
)

_AUTH_HEADERS = {"Authorization": "Bearer test-token"}

_MCP_SERVER_URL = "https://mcp.example.com/sse"

_MOCK_TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    },
    {
        "name": "search_products",
        "description": "Search the product catalog",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

_MOCK_PROMPTS = [
    {
        "name": "summarize",
        "description": "Summarize a document",
        "arguments": [{"name": "text", "description": "Document text", "required": True}],
    }
]

_MOCK_RESOURCES = [
    {
        "uri": "resource://catalog/products",
        "name": "Product Catalog",
        "description": "Full product list",
        "mimeType": "application/json",
    }
]


def _make_mcp_api(
    name: str = "my-mcp-server",
    runtime_uri: list[str] | None = None,
) -> ApiDefinition:
    """Create a mock MCP ``ApiDefinition`` with one deployment."""
    uris = runtime_uri if runtime_uri is not None else [_MCP_SERVER_URL]
    deployment = ApiDeployment(
        id="/deployments/prod",
        title="Production",
        environment=ApiEnvironment(
            id="/environments/prod",
            name="prod",
            title="Production",
            kind=EnvironmentKind.PRODUCTION,
        ),
        server=DeploymentServer(runtime_uri=uris),
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )
    return ApiDefinition(
        id=f"/apis/{name}",
        name=name,
        title="My MCP Server",
        description="An MCP server",
        kind=ApiKind.MCP,
        lifecycle_stage="production",
        deployments=[deployment],
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


def _make_rest_api(name: str = "petstore") -> ApiDefinition:
    """Create a mock REST ``ApiDefinition`` (non-MCP)."""
    deployment = ApiDeployment(
        id="/deployments/prod",
        title="Production",
        environment=ApiEnvironment(
            id="/environments/prod",
            name="prod",
            title="Production",
            kind=EnvironmentKind.PRODUCTION,
        ),
        server=DeploymentServer(runtime_uri=["https://api.example.com"]),
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )
    return ApiDefinition(
        id=f"/apis/{name}",
        name=name,
        title="Petstore API",
        description="A REST API",
        kind="rest",
        lifecycle_stage="production",
        deployments=[deployment],
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_mcp_api():
    """Create the app with a mocked service returning an MCP API."""
    app = create_app()

    mock_service = MagicMock()
    mock_service.get_api.return_value = _make_mcp_api()

    app.dependency_overrides[_get_service] = lambda: mock_service

    with patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER):
        yield app

    app.dependency_overrides.clear()


@pytest.fixture
def app_with_rest_api():
    """Create the app with a mocked service returning a REST (non-MCP) API."""
    app = create_app()

    mock_service = MagicMock()
    mock_service.get_api.return_value = _make_rest_api()

    app.dependency_overrides[_get_service] = lambda: mock_service

    with patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER):
        yield app

    app.dependency_overrides.clear()


@pytest.fixture
def app_with_no_deployment():
    """Create the app with a mocked service returning an MCP API with no deployments."""
    app = create_app()

    mock_service = MagicMock()
    api = _make_mcp_api()
    api.deployments = []
    mock_service.get_api.return_value = api

    app.dependency_overrides[_get_service] = lambda: mock_service

    with patch("apic_vibe_portal_bff.middleware.auth.validate_token", return_value=_MOCK_USER):
        yield app

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/mcp/{api_id}/capabilities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_capabilities_returns_tools_prompts_resources(app_with_mcp_api):
    """Happy path: returns tools, prompts, and resources from the MCP server."""
    mock_client = AsyncMock()
    mock_client.initialize = AsyncMock(return_value={"protocolVersion": "2024-11-05"})
    mock_client.list_tools = AsyncMock(return_value=_MOCK_TOOLS)
    mock_client.list_prompts = AsyncMock(return_value=_MOCK_PROMPTS)
    mock_client.list_resources = AsyncMock(return_value=_MOCK_RESOURCES)

    with patch(
        "apic_vibe_portal_bff.routers.mcp_inspector.McpClient",
        return_value=mock_client,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mcp_api),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/mcp/my-mcp-server/capabilities", headers=_AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    data = body["data"]

    assert data["serverUrl"] == _MCP_SERVER_URL
    assert len(data["tools"]) == 2
    assert data["tools"][0]["name"] == "get_weather"
    assert data["tools"][0]["description"] == "Get current weather for a location"
    assert data["tools"][0]["inputSchema"]["properties"]["location"]["type"] == "string"
    assert data["tools"][0]["inputSchema"]["required"] == ["location"]

    assert len(data["prompts"]) == 1
    assert data["prompts"][0]["name"] == "summarize"

    assert len(data["resources"]) == 1
    assert data["resources"][0]["uri"] == "resource://catalog/products"
    assert data["resources"][0]["mimeType"] == "application/json"


@pytest.mark.asyncio
async def test_get_capabilities_partial_support(app_with_mcp_api):
    """If the server only supports tools (not prompts/resources), still returns tools."""
    from apic_vibe_portal_bff.clients.mcp_client import McpClientError

    mock_client = AsyncMock()
    mock_client.initialize = AsyncMock(return_value={})
    mock_client.list_tools = AsyncMock(return_value=_MOCK_TOOLS)
    mock_client.list_prompts = AsyncMock(side_effect=McpClientError("Method not found"))
    mock_client.list_resources = AsyncMock(side_effect=McpClientError("Method not found"))

    with patch(
        "apic_vibe_portal_bff.routers.mcp_inspector.McpClient",
        return_value=mock_client,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mcp_api),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/mcp/my-mcp-server/capabilities", headers=_AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert len(data["tools"]) == 2
    assert data["prompts"] == []
    assert data["resources"] == []


@pytest.mark.asyncio
async def test_get_capabilities_rejects_non_mcp_api(app_with_rest_api):
    """Returns 422 when the API is not of kind 'mcp'."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_rest_api),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/mcp/petstore/capabilities", headers=_AUTH_HEADERS)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "NOT_MCP"


@pytest.mark.asyncio
async def test_get_capabilities_no_deployment_returns_422(app_with_no_deployment):
    """Returns 422 when the MCP API has no deployments."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_no_deployment),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/mcp/my-mcp-server/capabilities", headers=_AUTH_HEADERS)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "NO_DEPLOYMENT"


@pytest.mark.asyncio
async def test_get_capabilities_upstream_error_returns_502(app_with_mcp_api):
    """Returns 502 when the upstream MCP server is unreachable."""
    from apic_vibe_portal_bff.clients.mcp_client import McpClientError

    mock_client = AsyncMock()
    mock_client.initialize = AsyncMock(side_effect=McpClientError("Connection refused", status_code=None))

    with patch(
        "apic_vibe_portal_bff.routers.mcp_inspector.McpClient",
        return_value=mock_client,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mcp_api),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/mcp/my-mcp-server/capabilities", headers=_AUTH_HEADERS)

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "MCP_ERROR"


@pytest.mark.asyncio
async def test_get_capabilities_requires_auth():
    """Returns 401 when no auth token is provided."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/mcp/my-mcp-server/capabilities")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/mcp/{api_id}/invoke
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invoke_tool_returns_result(app_with_mcp_api):
    """Happy path: invokes a tool and returns the result content."""
    mock_client = AsyncMock()
    mock_client.initialize = AsyncMock(return_value={})
    mock_client.call_tool = AsyncMock(
        return_value={
            "content": [{"type": "text", "text": "Sunny, 22°C"}],
            "isError": False,
        }
    )

    with patch(
        "apic_vibe_portal_bff.routers.mcp_inspector.McpClient",
        return_value=mock_client,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mcp_api),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/mcp/my-mcp-server/invoke",
                headers=_AUTH_HEADERS,
                json={"tool_name": "get_weather", "arguments": {"location": "London"}},
            )

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert data["isError"] is False
    assert len(data["content"]) == 1
    assert data["content"][0]["type"] == "text"
    assert data["content"][0]["text"] == "Sunny, 22°C"
    assert isinstance(data["durationMs"], float | int)

    mock_client.call_tool.assert_called_once_with("get_weather", {"location": "London"})


@pytest.mark.asyncio
async def test_invoke_tool_propagates_is_error(app_with_mcp_api):
    """When the tool result has isError=True, that flag is forwarded."""
    mock_client = AsyncMock()
    mock_client.initialize = AsyncMock(return_value={})
    mock_client.call_tool = AsyncMock(
        return_value={
            "content": [{"type": "text", "text": "Tool execution failed: bad input"}],
            "isError": True,
        }
    )

    with patch(
        "apic_vibe_portal_bff.routers.mcp_inspector.McpClient",
        return_value=mock_client,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mcp_api),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/mcp/my-mcp-server/invoke",
                headers=_AUTH_HEADERS,
                json={"tool_name": "broken_tool", "arguments": {}},
            )

    assert response.status_code == 200
    assert response.json()["data"]["isError"] is True


@pytest.mark.asyncio
async def test_invoke_tool_upstream_error_returns_502(app_with_mcp_api):
    """Returns 502 when the upstream MCP server raises an error during invocation."""
    from apic_vibe_portal_bff.clients.mcp_client import McpClientError

    mock_client = AsyncMock()
    mock_client.initialize = AsyncMock(return_value={})
    mock_client.call_tool = AsyncMock(side_effect=McpClientError("Tool not found"))

    with patch(
        "apic_vibe_portal_bff.routers.mcp_inspector.McpClient",
        return_value=mock_client,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_mcp_api),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/mcp/my-mcp-server/invoke",
                headers=_AUTH_HEADERS,
                json={"tool_name": "missing_tool", "arguments": {}},
            )

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "MCP_ERROR"


@pytest.mark.asyncio
async def test_invoke_tool_non_mcp_api_returns_422(app_with_rest_api):
    """Returns 422 when trying to invoke a tool on a non-MCP API."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_rest_api),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/mcp/petstore/invoke",
            headers=_AUTH_HEADERS,
            json={"tool_name": "list_pets", "arguments": {}},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NOT_MCP"


@pytest.mark.asyncio
async def test_invoke_tool_requires_auth():
    """Returns 401 when no auth token is provided."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/mcp/my-mcp-server/invoke",
            json={"tool_name": "get_weather", "arguments": {}},
        )
    assert response.status_code == 401
