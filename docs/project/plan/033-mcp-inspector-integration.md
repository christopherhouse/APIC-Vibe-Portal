# Task 033 — MCP Inspector Integration

> 🔄 **Status: In Progress**

## Overview

Integrates an MCP (Model Context Protocol) Inspector directly into the API detail page for MCP-kind APIs. Developers can click the **Inspector** tab on any MCP API's detail page, browse the server's tools / prompts / resources, fill in parameters via an auto-generated form, invoke a tool, and see the result — all without leaving the portal.

---

## Status History

| Date       | Status      | Notes                                              |
| ---------- | ----------- | -------------------------------------------------- |
| 2026-04-23 | 🔄 In Progress | Initial implementation complete; awaiting review |

---

## Motivation & Design Decision

**Option chosen: "Inspector" tab on the MCP API detail page** (native MUI UI + BFF proxy).

- **Why not an iframe?** The official `@modelcontextprotocol/inspector` ships as a standalone app. Embedding it in an iframe would introduce CSP, auth token passthrough, and styling mismatch issues that outweigh the savings.
- **Why not a global `/mcp/inspector` page?** A standalone page disconnects the inspector from the catalog context. Users would have to know the server URL and navigate separately. A contextual tab provides zero-friction access.
- **Transport: Streamable HTTP** (`Content-Type: application/json` POST → JSON-RPC). This is the modern MCP transport (spec 2024-11-05). Legacy SSE-only servers will return a transport error surfaced in the UI.

---

## What Was Built

### BFF (Python / FastAPI)

| File | Description |
|------|-------------|
| `apic_vibe_portal_bff/models/mcp.py` | Pydantic models: `McpTool`, `McpPrompt`, `McpResource`, `McpCapabilities`, `McpInvokeRequest`, `McpInvokeResult`, plus nested schema types |
| `apic_vibe_portal_bff/clients/mcp_client.py` | Async `McpClient` using `aiohttp` for Streamable HTTP JSON-RPC. Handles plain-JSON and SSE-streamed responses. Exposes `initialize`, `list_tools`, `list_prompts`, `list_resources`, `call_tool`. |
| `apic_vibe_portal_bff/routers/mcp_inspector.py` | Two endpoints: `GET /api/mcp/{api_id}/capabilities` and `POST /api/mcp/{api_id}/invoke`. Both enforce RBAC and security trimming before resolving the server URL from the API catalog. Also validates the API is of kind `mcp`. |
| `apic_vibe_portal_bff/app.py` | Registers `mcp_inspector_router` and `McpInspectorError` exception handler. |
| `tests/test_mcp_inspector_routes.py` | 11 pytest tests covering happy paths, partial server support, non-MCP API rejection, no-deployment 422, upstream 502 propagation, and auth enforcement. |

### Frontend (Next.js / React / MUI)

| File | Description |
|------|-------------|
| `lib/mcp-inspector-api.ts` | Typed `fetchMcpCapabilities` and `invokeMcpTool` wrappers over `apiClient`. Exports all response types. |
| `app/catalog/[apiId]/components/ApiTabs.tsx` | Added `showInspector` and `inspectorEnabled` optional props. Inspector tab rendered conditionally, disabled with tooltip when no deployment URL is available. |
| `app/catalog/[apiId]/components/McpInspectorTab.tsx` | Two-panel inspector UI: left rail with Tools/Prompts/Resources tabs + list; right pane with schema-driven form, Invoke button, and result panel. MUI v9 compatible (`slotProps.htmlInput`, `slotProps.secondary`). |
| `app/catalog/[apiId]/page.tsx` | Passes `showInspector={isMcp}` and `inspectorEnabled={!!mcpServerUrl}` to `ApiTabs`. Renders `<McpInspectorTab>` when the inspector tab is active. |
| `app/catalog/[apiId]/components/__tests__/McpInspectorTab.test.tsx` | 15 Jest + RTL unit tests covering loading, error, retry, connection UI, tool/prompt/resource list rendering, schema form, invoke result, invoke error, tab switching, and refresh. |
| `e2e/mock-server/index.ts` | Added `GET /api/mcp/:apiId/capabilities` and `POST /api/mcp/:apiId/invoke` endpoints to the standalone mock server. |
| `e2e/api-detail.spec.ts` | 7 new Playwright e2e tests: Inspector tab visibility (MCP + non-MCP), disabled state when no deployment, loading the panel, listing tools, invoking a tool, switching to prompts/resources. |

---

## API Contract

### `GET /api/mcp/{api_id}/capabilities`

Returns the aggregated capabilities of the MCP server registered for `api_id`.

**Response:**
```json
{
  "data": {
    "serverUrl": "https://mcp.example.com/sse",
    "tools": [
      {
        "name": "get_weather",
        "description": "Get current weather",
        "inputSchema": {
          "type": "object",
          "properties": {
            "location": { "type": "string", "description": "City name" }
          },
          "required": ["location"]
        }
      }
    ],
    "prompts": [...],
    "resources": [...]
  }
}
```

**Error codes:**
| Code | HTTP | Meaning |
|------|------|---------|
| `NOT_FOUND` | 404 | API not in catalog |
| `FORBIDDEN` | 403 | Security trimming denied access |
| `NOT_MCP` | 422 | API is not of kind `mcp` |
| `NO_DEPLOYMENT` | 422 | API has no deployments |
| `NO_SERVER_URL` | 422 | Deployment has no server URI |
| `MCP_ERROR` | 502 | Upstream MCP server unreachable or returned an error |

### `POST /api/mcp/{api_id}/invoke`

**Request:**
```json
{ "tool_name": "get_weather", "arguments": { "location": "London" } }
```

**Response:**
```json
{
  "data": {
    "content": [{ "type": "text", "text": "Sunny, 22°C" }],
    "isError": false,
    "durationMs": 142.3
  }
}
```

---

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| `aiohttp` for upstream HTTP (no new dep) | Already in `pyproject.toml` production deps |
| `initialize` before every list/invoke | Stateless BFF — no persistent MCP session; each request re-handshakes |
| Partial capability support | `list_tools/list_prompts/list_resources` failures are swallowed individually so a server that only supports tools still returns them |
| `slotProps.htmlInput` + `slotProps.secondary` | MUI v9 deprecated `inputProps` and `secondaryTypographyProps` |
| Inspector tab disabled (not hidden) when no URL | Communicates affordance exists but requires a deployment, consistent with `InstallInVsCodeButton` pattern |

---

## Deviations from Plan

None. Implemented exactly as specified in the plan.

---

## Testing & Acceptance Criteria

- [x] BFF: `GET /api/mcp/{api_id}/capabilities` returns tools, prompts, resources
- [x] BFF: `POST /api/mcp/{api_id}/invoke` invokes a tool and returns result
- [x] BFF: RBAC enforced (401 without token)
- [x] BFF: Security trimming / kind check enforced
- [x] BFF: Upstream errors return 502 with structured error body
- [x] Frontend: Inspector tab appears for MCP APIs, absent for REST
- [x] Frontend: Inspector tab disabled when API has no deployment URL
- [x] Frontend: Tool list renders from capabilities response
- [x] Frontend: Schema-driven form renders for selected tool
- [x] Frontend: Tool invocation shows result panel with content + status
- [x] Frontend: isError=true surfaces an Error chip
- [x] Frontend: Prompts and Resources tabs render and select items
- [x] Frontend: Retry button on error state reloads capabilities
- [x] Frontend: Refresh button reloads capabilities
- [x] E2E: Inspector tab appears/absent based on API kind
- [x] E2E: Inspector tab disabled when no deployment
- [x] E2E: Clicking tab loads inspector panel
- [x] E2E: Tool list visible after load
- [x] E2E: Tool invocation triggers invoke endpoint and shows result
- [x] E2E: Prompts and Resources tabs navigable

---

## Validation Results

| Check | Result |
|-------|--------|
| `uv run ruff check .` | ✅ All checks passed |
| `uv run ruff format --check .` | ✅ All files formatted |
| `uv run pytest` | ✅ 1192 passed (11 new) |
| `npm run lint` | ✅ No ESLint errors |
| `npm run format:check` | ✅ All files use Prettier style |
| `npx tsc --noEmit` | ✅ No type errors |
| `npm run test` | ✅ 420 passed (15 new) |
| `npm run build` | ✅ Build succeeded |
