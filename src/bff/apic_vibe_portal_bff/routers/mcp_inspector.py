"""MCP Inspector proxy routes.

Acts as a secure proxy between the frontend MCP Inspector UI and the MCP
servers registered in the API catalog.  Security trimming is enforced before
any upstream MCP call is made, so users can only inspect servers they have
catalog access to.

Endpoints
---------
GET  /api/mcp/{api_id}/capabilities  — List tools, prompts, and resources
POST /api/mcp/{api_id}/invoke        — Invoke an MCP tool by name
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apic_vibe_portal_bff.clients.mcp_client import McpClient, McpClientError
from apic_vibe_portal_bff.middleware.rbac import require_any_role
from apic_vibe_portal_bff.middleware.security_trimming import make_accessible_ids_dep
from apic_vibe_portal_bff.models.api_center import ApiKind
from apic_vibe_portal_bff.models.mcp import (
    McpCapabilities,
    McpContentItem,
    McpInvokeRequest,
    McpInvokeResult,
    McpPrompt,
    McpPromptArgument,
    McpResource,
    McpTool,
    McpToolInputSchema,
)
from apic_vibe_portal_bff.routers.api_catalog import (
    ApiErrorResponse,
    ApiResponse,
    ErrorDetail,
    _get_service,
)
from apic_vibe_portal_bff.services.api_catalog_service import ApiAccessDeniedError, ApiCatalogService

logger = logging.getLogger(__name__)

_ALLOWED_ROLES = ["Portal.User", "Portal.Admin", "Portal.Maintainer"]

# Default HTTP status code returned when an upstream MCP call fails.
_DEFAULT_MCP_ERROR_STATUS = 502

router = APIRouter(tags=["mcp-inspector"])

# ---------------------------------------------------------------------------
# Custom exception + handler
# ---------------------------------------------------------------------------


class McpInspectorError(Exception):
    """Raised by route handlers to produce a structured error response."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def mcp_inspector_error_handler(_request: object, exc: McpInspectorError) -> JSONResponse:
    """Serialize :class:`McpInspectorError` into an ``ApiErrorResponse`` envelope."""
    body = ApiErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


def _raise_mcp_error(status_code: int, code: str, message: str) -> None:
    raise McpInspectorError(status_code=status_code, code=code, message=message)


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def _map_tool(raw: dict[str, Any]) -> McpTool:
    """Map a raw MCP tool dict to a :class:`McpTool` model."""
    raw_schema = raw.get("inputSchema") or {}
    schema = McpToolInputSchema(
        type=raw_schema.get("type", "object"),
        properties=raw_schema.get("properties") or {},
        required=raw_schema.get("required") or [],
        description=raw_schema.get("description"),
    )
    return McpTool(
        name=raw.get("name", ""),
        description=raw.get("description"),
        input_schema=schema,
    )


def _map_prompt(raw: dict[str, Any]) -> McpPrompt:
    """Map a raw MCP prompt dict to a :class:`McpPrompt` model."""
    raw_args = raw.get("arguments") or []
    args = [
        McpPromptArgument(
            name=a.get("name", ""),
            description=a.get("description"),
            required=bool(a.get("required", False)),
        )
        for a in raw_args
        if isinstance(a, dict)
    ]
    return McpPrompt(
        name=raw.get("name", ""),
        description=raw.get("description"),
        arguments=args,
    )


def _map_resource(raw: dict[str, Any]) -> McpResource:
    """Map a raw MCP resource dict to a :class:`McpResource` model."""
    return McpResource(
        uri=raw.get("uri", ""),
        name=raw.get("name", ""),
        description=raw.get("description"),
        mime_type=raw.get("mimeType"),
    )


def _map_content_item(raw: dict[str, Any]) -> McpContentItem:
    """Map a raw MCP content item dict to a :class:`McpContentItem` model."""
    return McpContentItem(
        type=raw.get("type", "text"),
        text=raw.get("text"),
        data=raw.get("data"),
        mime_type=raw.get("mimeType"),
    )


# ---------------------------------------------------------------------------
# Shared helper to resolve the MCP server URL
# ---------------------------------------------------------------------------


def _resolve_server_url(
    api_id: str,
    service: ApiCatalogService,
    accessible_api_ids: list[str] | None,
) -> str:
    """Return the first runtime URI for the API's primary deployment.

    Applies security trimming (raises :class:`McpInspectorError` 403 if denied)
    and validates that the API is of kind ``mcp``.
    """
    try:
        api = service.get_api(
            api_id,
            include_versions=False,
            include_deployments=True,
            accessible_api_ids=accessible_api_ids,
        )
    except ApiAccessDeniedError:
        _raise_mcp_error(403, "FORBIDDEN", f"Access to API '{api_id}' is not permitted")
    except Exception as exc:
        _raise_mcp_error(404, "NOT_FOUND", f"API '{api_id}' not found: {exc}")

    if api.kind != ApiKind.MCP:
        _raise_mcp_error(422, "NOT_MCP", f"API '{api_id}' is not an MCP API (kind={api.kind})")

    if not api.deployments:
        _raise_mcp_error(422, "NO_DEPLOYMENT", f"No deployments found for API '{api_id}'")

    uris = api.deployments[0].server.runtime_uri
    if not uris:
        _raise_mcp_error(422, "NO_SERVER_URL", f"No server URL configured for API '{api_id}'")

    return uris[0]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/api/mcp/{api_id}/capabilities",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
async def get_mcp_capabilities(
    api_id: str,
    service: ApiCatalogService = Depends(_get_service),  # noqa: B008
    accessible_api_ids: list[str] | None = Depends(make_accessible_ids_dep()),  # noqa: B008
) -> ApiResponse[McpCapabilities]:
    """Fetch the tools, prompts, and resources exposed by an MCP server.

    Resolves the server URL from the API's catalog deployment entry, then
    sends ``tools/list``, ``prompts/list``, and ``resources/list`` requests
    to the upstream MCP server.
    """
    start = time.monotonic()
    try:
        server_url = _resolve_server_url(api_id, service, accessible_api_ids)
        client = McpClient(server_url=server_url)

        await client.initialize()

        raw_tools, raw_prompts, raw_resources = await _fetch_all_capabilities(client)

        capabilities = McpCapabilities(
            server_url=server_url,
            tools=[_map_tool(t) for t in raw_tools if isinstance(t, dict)],
            prompts=[_map_prompt(p) for p in raw_prompts if isinstance(p, dict)],
            resources=[_map_resource(r) for r in raw_resources if isinstance(r, dict)],
        )
        return ApiResponse(data=capabilities)

    except McpInspectorError:
        raise
    except McpClientError as exc:
        logger.warning("get_mcp_capabilities: MCP error", extra={"api_id": api_id, "error": str(exc)})
        _raise_mcp_error(
            exc.status_code or _DEFAULT_MCP_ERROR_STATUS,
            "MCP_ERROR",
            f"Failed to fetch capabilities from MCP server: {exc}",
        )
    finally:
        elapsed = time.monotonic() - start
        logger.info(
            "api_response_time",
            extra={"endpoint": "get_mcp_capabilities", "api_id": api_id, "duration_ms": round(elapsed * 1000, 2)},
        )


async def _fetch_all_capabilities(
    client: McpClient,
) -> tuple[list[Any], list[Any], list[Any]]:
    """Fetch tools, prompts, and resources from the MCP server.

    Each list method is called independently so that a server that only
    supports some capability types does not block the others.
    """
    tools: list[Any] = []
    prompts: list[Any] = []
    resources: list[Any] = []

    try:
        tools = await client.list_tools()
    except McpClientError:
        logger.debug("list_tools not supported by MCP server")

    try:
        prompts = await client.list_prompts()
    except McpClientError:
        logger.debug("list_prompts not supported by MCP server")

    try:
        resources = await client.list_resources()
    except McpClientError:
        logger.debug("list_resources not supported by MCP server")

    return tools, prompts, resources


@router.post(
    "/api/mcp/{api_id}/invoke",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
async def invoke_mcp_tool(
    api_id: str,
    request: McpInvokeRequest,
    service: ApiCatalogService = Depends(_get_service),  # noqa: B008
    accessible_api_ids: list[str] | None = Depends(make_accessible_ids_dep()),  # noqa: B008
) -> ApiResponse[McpInvokeResult]:
    """Invoke an MCP tool by name.

    Resolves the server URL from the API catalog, sends a ``tools/call``
    request to the upstream MCP server, and returns the result.
    """
    start = time.monotonic()
    try:
        server_url = _resolve_server_url(api_id, service, accessible_api_ids)
        client = McpClient(server_url=server_url)

        await client.initialize()
        raw_result = await client.call_tool(request.tool_name, request.arguments)

        elapsed_ms = (time.monotonic() - start) * 1000
        is_error = bool(raw_result.get("isError", False))
        raw_content = raw_result.get("content") or []

        invoke_result = McpInvokeResult(
            content=[_map_content_item(c) for c in raw_content if isinstance(c, dict)],
            is_error=is_error,
            duration_ms=round(elapsed_ms, 2),
        )
        return ApiResponse(data=invoke_result)

    except McpInspectorError:
        raise
    except McpClientError as exc:
        logger.warning(
            "invoke_mcp_tool: MCP error",
            extra={"api_id": api_id, "tool": request.tool_name, "error": str(exc)},
        )
        _raise_mcp_error(
            exc.status_code or _DEFAULT_MCP_ERROR_STATUS,
            "MCP_ERROR",
            f"Failed to invoke tool '{request.tool_name}': {exc}",
        )
    finally:
        elapsed = time.monotonic() - start
        logger.info(
            "api_response_time",
            extra={
                "endpoint": "invoke_mcp_tool",
                "api_id": api_id,
                "tool_name": request.tool_name,
                "duration_ms": round(elapsed * 1000, 2),
            },
        )
