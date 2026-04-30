# 036 - MCP Capability Indexing

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Search Layer (AI Search), Persistence (Cosmos DB)
- [Product Charter](../apic_product_charter.md) — Improve API discovery
- [013 — AI Search Index Setup & Indexing Pipeline](013-ai-search-index-setup.md)
- [014 — Search API Implementation](014-search-api-implementation.md)
- [033 — MCP Inspector Integration](033-mcp-inspector-integration.md) — capability shape (`McpTool`, `McpPrompt`, `McpResource`)

## Overview

Today the catalog and search index API-level metadata (name, description, lifecycle, etc.). For MCP-kind APIs, the **most useful unit of discovery is a tool, not a server** — developers search for "convert markdown to pdf," not for a server that happens to contain that capability.

This task captures the tools, prompts, and resources declared in each MCP API's APIC definition payload, projects them as child documents into AI Search, and persists a structured snapshot in Cosmos DB so downstream features (drift detection, governance, comparison) can read a stable shape.

The capture source is **the API Center definition document** for each `kind=mcp` API version — _not_ a live `tools/list` call against the upstream server. The indexer runs as a scheduled Container Apps Job and must work without inbound network access to MCP endpoints.

## Dependencies

- **009** — API Center data layer (definition export)
- **013** — AI Search index setup (index schema)
- **016** — Persistence baseline (Cosmos DB containers, repository pattern)
- **033** — MCP Inspector Integration (capability Pydantic models in `models/mcp.py`)

## Implementation Details

### 1. Capability Snapshot Schema

Add a new Cosmos DB container `mcp-capability-snapshots` (partition key `/apiId`).

```typescript
interface McpCapabilitySnapshot {
  id: string;                  // `${apiId}__${versionName}`
  apiId: string;
  apiName: string;
  versionName: string;
  capturedAt: string;          // ISO timestamp
  source: 'apic-definition';   // reserved for future 'live-probe'
  definitionHash: string;      // sha256 of normalized definition payload
  tools: McpTool[];            // shape from models/mcp.py
  prompts: McpPrompt[];
  resources: McpResource[];
  toolCount: number;
  promptCount: number;
  resourceCount: number;
  schemaVersion: 1;
}
```

Hash is computed over a normalized JSON form (sorted keys, stripped whitespace) so unchanged payloads do not trigger search reindex churn.

### 2. Definition Parser

```
src/shared/src/mcp/
├── definition-parser.ts       # Parse APIC MCP definition → McpCapabilitySnapshot
└── definition-parser.test.ts
```

A pure function `parseMcpDefinition(rawDefinition: unknown): ParsedCapabilities` that:

- Accepts the JSON payload returned by `export_api_specification` for `kind=mcp` APIs.
- Tolerates two layouts: (a) MCP-spec-style `{ tools: [...], prompts: [...], resources: [...] }` and (b) a wrapping `capabilities` object — log and pick whichever is present.
- Validates each tool/prompt/resource against the existing Pydantic / TS shapes; drops malformed entries with a warning rather than failing the whole snapshot.
- Returns counts plus a list of validation issues for governance to consume.

A matching Python implementation lives in `src/bff/apic_vibe_portal_bff/services/mcp_definition_parser.py` so both the indexer and the BFF can use it.

### 3. Indexer Worker Changes

Extend the existing `src/indexer/` Container Apps Job:

- For each API where `kind == 'mcp'`, fetch the latest version's primary definition via `list_api_definitions` + `export_api_specification`.
- Parse with the shared parser; compute `definitionHash`.
- Upsert the snapshot into Cosmos. Skip the AI Search reindex step when the new hash matches the existing snapshot.
- Emit App Insights telemetry: `mcp_indexer.captured`, `mcp_indexer.unchanged`, `mcp_indexer.parse_failed` with `apiId` / `versionName` / counts.

### 4. AI Search Index Changes

Extend `src/indexer/indexer/index_schema.py` to add a second index (or sibling fields) for **MCP capability** documents — one document per tool / prompt / resource:

| Field             | Type    | Notes                                     |
| ----------------- | ------- | ----------------------------------------- |
| `id`              | string  | `${apiId}__${versionName}__tool__${name}` |
| `apiId`           | string  | filterable, faceted                       |
| `apiName`         | string  |                                           |
| `versionName`     | string  | filterable                                |
| `capabilityType`  | string  | `tool` / `prompt` / `resource`            |
| `capabilityName`  | string  | searchable                                |
| `description`     | string  | searchable                                |
| `parameterNames`  | string[]| from input schema                         |
| `embedding`       | vector  | name + description + params               |
| `lastIndexedAt`   | dateTime|                                           |

Use a **separate index** (`mcp-capabilities`) to keep facets, scoring, and TTL independent from the existing api-level index.

### 5. BFF — Search Surface

```
src/bff/apic_vibe_portal_bff/services/mcp_capability_search_service.py
src/bff/apic_vibe_portal_bff/routers/mcp_search.py
```

New endpoint:

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/mcp/capabilities/search?q=&type=&top=` | Hybrid search across tool/prompt/resource docs |

- Same RBAC + security trimming as `/api/search`. Filter results to `apiId`s the caller can see.
- Returns each hit with `apiId`, `apiName`, `capabilityType`, `capabilityName`, `description`, and a back-link to the API detail page.

A read-only `getSnapshot(apiId, versionName)` accessor on the same service exposes the full Cosmos snapshot for downstream tasks (drift, comparison).

### 6. Frontend — Capability-Level Search Results

- Add a "Tools" tab to the global search page (`app/search/page.tsx`) that calls the new endpoint.
- Each hit links to the API detail page with `?tab=inspector&tool=<name>` so the existing Inspector tab pre-selects the matching tool.

### 7. Catalog Card — Tool Count Chip

On `app/catalog/components/ApiCard.tsx`, for MCP APIs, render a small chip "N tools" sourced from the snapshot's `toolCount`. Read from the snapshot, not a live probe.

## Testing & Acceptance Criteria

- [ ] Shared parser handles both definition layouts and rejects malformed tool/prompt/resource entries with structured warnings.
- [ ] Indexer captures a snapshot for every `kind=mcp` API in a test APIC fixture.
- [ ] Indexer is idempotent — a second run with no source changes produces zero AI Search writes (verified via search client mock).
- [ ] Cosmos snapshot includes `definitionHash`, `toolCount`, `promptCount`, `resourceCount`.
- [ ] AI Search `mcp-capabilities` index has one document per tool/prompt/resource with correct `apiId` linkage.
- [ ] `GET /api/mcp/capabilities/search?q=...` returns hits filtered by RBAC + security trimming.
- [ ] Search page Tools tab renders results and deep-links into the Inspector tab with the tool pre-selected.
- [ ] ApiCard renders a tool-count chip on MCP APIs.
- [ ] Unit tests cover parser edge cases, indexer idempotency, search service filters.
- [ ] E2E: Search "weather" finds a tool defined in a fixture MCP server.

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
**Task**: Implement plan step 036 — MCP Capability Indexing.

Read the full task specification at `docs/project/plan/036-mcp-capability-indexing.md`.

Reference `docs/project/plan/013-ai-search-index-setup.md` for the indexing pipeline, `docs/project/plan/016-persistence-data-governance-baseline.md` for the Cosmos repository pattern, and `docs/project/plan/033-mcp-inspector-integration.md` for the existing MCP capability models.

Build a shared definition parser (TS + Python), extend the indexer Container Apps Job to capture MCP capability snapshots into a new Cosmos container, project each capability as a child document in a new `mcp-capabilities` AI Search index, and expose a hybrid-search BFF endpoint with RBAC + security trimming. Add a Tools tab to the search page and a tool-count chip to ApiCard.

The indexer must NOT call live MCP servers. Source data exclusively from APIC definition exports. Indexing must be idempotent on unchanged definitions.

Write unit tests (parser, indexer idempotency, search service) and one E2E test that finds a tool by name. Verify all tests pass.

**Living Document Update**: After completing implementation, update this plan document:
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
