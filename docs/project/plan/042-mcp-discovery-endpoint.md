# 042 - MCP Discovery Endpoint for AI Agents

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Security, BFF, Persistence
- [Product Charter](../apic_product_charter.md) — Improve API discovery; AI-assisted workflows
- [008 — Entra ID Authentication](008-entra-id-authentication.md)
- [020 — Security Trimming](020-security-trimming.md)
- [036 — MCP Capability Indexing](036-mcp-capability-indexing.md)
- [037 — MCP Governance Rules](037-mcp-governance-rules.md)

## Overview

Today the portal is a **human** interface to MCP servers — a UI for browsing, inspecting, comparing. The other half of the registry value is exposing the same catalog to **agents** so they can discover MCP servers programmatically, with the same identity-aware filtering (RBAC + security trimming) that the human UI enforces.

This task adds an authenticated, machine-readable discovery API that emits an MCP-registry manifest tailored to the calling identity. Tools like Claude Desktop, VS Code Copilot, Cursor, and custom Foundry agents can fetch this manifest, parse it, and configure themselves to talk to the MCP servers the caller is allowed to use — without the caller hand-curating an `mcp.json` per machine.

This is the feature that turns the portal from "APIC with a nicer UI" into "the registry an enterprise points its agents at."

## Dependencies

- **008** — Entra ID Authentication (caller identity)
- **020** — Security Trimming (per-API access)
- **036** — MCP Capability Indexing (capability data the manifest summarises)
- **037** — MCP Governance Rules (risk badges in the manifest)
- **019** — App Insights (usage telemetry)

## Implementation Details

### 1. Manifest Format

A versioned, JSON-only manifest at `GET /api/mcp/registry/manifest`.

```typescript
interface McpRegistryManifest {
  schemaVersion: 1;
  generatedAt: string;
  registry: {
    name: string;          // configured portal display name
    portalUrl: string;     // base URL of the portal
  };
  caller: {
    oid: string;
    tenantId: string;
    roles: string[];
  };
  servers: McpRegistryServerEntry[];
}

interface McpRegistryServerEntry {
  apiId: string;
  apiName: string;
  versionName: string;
  description: string | null;
  serverUrl: string;
  transport: 'streamable-http' | 'sse';
  auth: McpAuthDescriptor;            // see §3
  capabilities: {
    toolCount: number;
    promptCount: number;
    resourceCount: number;
    toolNames: string[];              // names only — not full schemas
  };
  governance: {
    score: number | null;             // 0–100
    hasDestructiveTools: boolean;
    riskLevel: 'low' | 'medium' | 'high';
  };
  links: {
    detail: string;                   // portal API detail URL
    inspector: string;                // deep link to inspector tab
    capabilities: string;             // /api/mcp/{apiId}/capabilities
  };
}
```

The manifest is **already filtered** to APIs the caller can see (RBAC + security trimming). Filters apply at generation time, not at the consumer.

### 2. Endpoint Surface

```
src/bff/apic_vibe_portal_bff/routers/mcp_registry.py
src/bff/apic_vibe_portal_bff/services/mcp_registry_service.py
```

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/mcp/registry/manifest`                            | Full manifest, filtered to caller |
| `GET`  | `/api/mcp/registry/manifest?tags=&riskLevel=&hasTool=`  | Filtered manifest                  |
| `GET`  | `/api/mcp/registry/manifest/vscode`                     | VS Code `mcp.json` profile         |
| `GET`  | `/api/mcp/registry/manifest/claude`                     | Claude Desktop `claude_desktop_config.json` profile |
| `GET`  | `/api/mcp/registry/manifest/openapi`                    | OpenAPI 3 description of this surface |
| `GET`  | `/.well-known/mcp-registry`                             | Service discovery (returns capability + auth metadata) |

The two profile endpoints return the same data shaped to a specific consumer's config schema, saving operators from writing transformers.

### 3. Auth Descriptor

Each server entry includes a structured `auth` block describing how the consumer must authenticate to the upstream MCP server:

```typescript
type McpAuthDescriptor =
  | { type: 'none' }
  | { type: 'entra'; tenantId: string; clientId: string; scopes: string[] }
  | { type: 'oauth2'; authorizationUrl: string; tokenUrl: string; scopes: string[] }
  | { type: 'apikey'; header: string; instructionsUrl: string }
  | { type: 'token-broker'; brokerUrl: string };  // reserved for future Task

The descriptor is sourced from the API Center metadata for the deployment. APIs without a recognisable auth descriptor default to `{ type: 'none' }` and a governance warning is emitted.

### 4. Authentication & Authorisation

- All endpoints require Entra ID (same `acquireToken` flow as the rest of the portal). No anonymous access.
- A new role `Portal.Agent` is introduced — a least-privilege role specifically for headless agent identities (service principals, managed identities). It has read-only access to the registry endpoints and **no** access to admin pages or invocation surfaces.
- Existing `Portal.User` / `Portal.Maintainer` / `Portal.Admin` continue to work and see the same filtered manifest as their UI experience.
- Calls are rate-limited per (caller oid, endpoint) — default 60/min, configurable.

### 5. Caching

- Manifest generation is cached in Redis per-caller for 60 seconds (`mcp:registry:manifest:{oid}`). Filter parameters are included in the cache key.
- Cache invalidates when: the indexer (Task 036) writes a new snapshot, or governance rules are recomputed for an API in the manifest. Invalidation is broadcast via a Redis pub/sub channel `mcp.registry.invalidate`.

### 6. CLI / Helpers

- `scripts/print-mcp-manifest.py` — pretty-prints the manifest for a given Entra token. Useful for ops debugging.
- `scripts/install-mcp-from-portal.sh` — fetches the VS Code profile and merges it into the developer's local `mcp.json`. (Read-only, prompts before overwrite.)

### 7. Security Considerations

- **No bearer tokens in the manifest.** The manifest describes _how_ to authenticate, never carries a token to a downstream server.
- **No tool schemas in the manifest.** Schemas can leak business logic and are large; consumers fetch them via the existing `/api/mcp/{apiId}/capabilities` endpoint as needed.
- **No invocation surface.** This endpoint is read-only discovery; tool calls still go through the existing inspector endpoints with their own RBAC.
- **CORS**: Manifest endpoints reject browser-origin calls by default. They are designed for server-to-server / IDE consumption and should not be exposed to public web clients.

### 8. Telemetry

Emit App Insights events:

- `mcp.registry.manifest_fetched` — `oid`, `userAgent`, `serverCount`, `filtersApplied`.
- `mcp.registry.profile_fetched` — `oid`, `profile` (`vscode` | `claude`).

These let admins see which agents are actually using the registry.

## Testing & Acceptance Criteria

- [ ] Manifest endpoint requires authentication (401 without token).
- [ ] Manifest contains only APIs the caller can see (regression test against fixture with mixed-access APIs).
- [ ] Filter params (`tags`, `riskLevel`, `hasTool`) narrow results correctly.
- [ ] VS Code profile output validates against the VS Code `mcp.json` schema.
- [ ] Claude profile output is valid JSON loadable by Claude Desktop.
- [ ] Auth descriptor is populated for every entry; APIs with unknown auth default to `{type: 'none'}` and emit a governance warning.
- [ ] Manifest never contains tokens, full tool schemas, or invocation surfaces.
- [ ] `Portal.Agent` role can read manifest; cannot read admin endpoints.
- [ ] Rate limiter enforces the configured per-caller/per-endpoint limit.
- [ ] Redis cache returns the same payload within TTL; indexer writes invalidate the cache.
- [ ] `/.well-known/mcp-registry` returns service metadata (auth + endpoints) without requiring auth.
- [ ] OpenAPI description endpoint returns a valid OpenAPI 3 doc for the registry surface.
- [ ] `mcp.registry.manifest_fetched` event fires on every successful fetch with the documented dimensions.
- [ ] E2E: A test client authenticates as `Portal.Agent`, fetches the manifest, and sees only the expected fixture servers.

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date | Status         | Author | Notes        |
| ---- | -------------- | ------ | ------------ |
| —    | 🔲 Not Started | —      | Task created |

### Technical Decisions

_To be recorded by the implementing agent._

### Deviations from Plan

_To be recorded by the implementing agent._

### Validation Results

_To be recorded by the implementing agent._

## Coding Agent Prompt

```text
**Task**: Implement plan step 042 — MCP Discovery Endpoint for AI Agents.

Read the full task specification at `docs/project/plan/042-mcp-discovery-endpoint.md`.

Reference `docs/project/plan/008-entra-id-authentication.md` for the auth flow, `docs/project/plan/020-security-trimming.md` for per-API filtering, `docs/project/plan/036-mcp-capability-indexing.md` for the capability data, and `docs/project/plan/037-mcp-governance-rules.md` for the risk profile that feeds the manifest.

Build the manifest service and router with the schema in §1. Implement RBAC including a new `Portal.Agent` role. Add filter params (tags, riskLevel, hasTool), VS Code and Claude profile transformers, an OpenAPI surface, and a `/.well-known/mcp-registry` discovery endpoint. Cache per-caller in Redis with pub/sub-driven invalidation tied to indexer + governance writes. Emit telemetry. Reject browser CORS by default. Never include tokens or full tool schemas in the manifest.

Write unit tests covering RBAC, security-trimmed filtering, profile transformations, cache invalidation, and rate limiting. Add an E2E test that exercises the manifest as `Portal.Agent`.

**Living Document Update**: After completing implementation, update this plan document:
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
