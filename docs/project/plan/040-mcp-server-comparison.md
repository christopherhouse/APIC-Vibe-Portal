# 040 - MCP Server Comparison

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — AI-powered features for API understanding
- [Product Charter](../apic_product_charter.md) — Phase 2: Governance + Compare
- [024 — API Comparison Feature](024-api-comparison-feature.md) — base compare framework
- [036 — MCP Capability Indexing](036-mcp-capability-indexing.md) — capability snapshots
- [037 — MCP Governance Rules](037-mcp-governance-rules.md) — risk profile
- [038 — Capability Drift Detection](038-mcp-capability-drift-detection.md) — recency / churn signals
- [039 — Invocation Audit Log](039-mcp-invocation-audit-log.md) — usage signals

## Overview

The existing comparison feature (Task 024) compares APIs on metadata, versions, endpoints, governance, deployments, and specifications. None of those aspects are particularly useful for choosing between two MCP servers. The questions a developer actually asks are:

- "Which one has the tool I need?"
- "Whose tool schemas are stricter?"
- "Which one is more battle-tested?"
- "Which one has fewer destructive tools / better risk profile?"
- "Which one changes more often?"

This task adds an MCP-specific comparison aspect that surfaces these signals using only data already collected in Tasks 036–039 (snapshots, governance, drift, invocation rollups). It plugs into the existing `/compare` page so users get the right comparison automatically when all selected APIs are `kind=mcp`.

## Dependencies

- **024** — API Comparison Feature (extension point)
- **036** — MCP Capability Indexing
- **037** — MCP Governance Rules
- **038** — MCP Capability Drift Detection
- **039** — MCP Invocation Audit Log

## Implementation Details

### 1. New Compare Aspects

Extend the `CompareAspect` union in `src/shared/src/models/compare.ts`:

```typescript
type CompareAspect =
  | 'metadata' | 'versions' | 'endpoints'
  | 'governance' | 'deployments' | 'specifications'
  // new MCP-specific aspects
  | 'mcp.toolSurface'      // tool overlap matrix + counts
  | 'mcp.schemaQuality'    // per-server schema strictness scores
  | 'mcp.riskProfile'      // destructive/write tool counts, security flags
  | 'mcp.churn'            // recent drift summary (last 90d)
  | 'mcp.usage';           // invocation volume, error rate, popularity
```

When all selected APIs are `kind=mcp`, the default aspect set switches from the generic six to the five MCP aspects above (plus `metadata`).

### 2. Tool Overlap Matrix

The marquee feature: an N × M grid where rows are unique tool names across all selected servers and columns are servers, with ✓ in cells where the server provides that tool. Includes a "compatibility" column showing schema parity (identical / compatible-superset / divergent / incompatible) when ≥ 2 servers expose the same tool name.

```typescript
interface ToolOverlapMatrix {
  toolNames: string[];
  servers: { apiId: string; apiName: string }[];
  cells: ToolOverlapCell[][];   // [toolIndex][serverIndex]
}

interface ToolOverlapCell {
  present: boolean;
  schemaCompatibility?: 'identical' | 'superset' | 'divergent' | 'incompatible';
  toolFingerprint?: string;     // hash of normalised input schema
}
```

Schema-compatibility classification is a deterministic helper that compares two tools' input schemas and reports the result. Live in `src/shared/src/mcp/tool-compatibility.ts`.

### 3. Per-Server Aspect Computations

```
src/bff/apic_vibe_portal_bff/services/mcp_compare_service.py
```

For each selected MCP API the service produces:

- **toolSurface**: total tools, unique tools (not in any other selected server), shared tools, tool overlap matrix.
- **schemaQuality**: % tools with descriptions ≥ 20 chars, % tools with `required` array, % parameters with descriptions, % schemas with `additionalProperties: false`. Sourced from the same data Task 037 uses, but computed independently (don't reuse rule failures — that conflates "rule failed" with "metric").
- **riskProfile**: destructive tool count, write tool count, has-shell-passthrough flag, auth-documented flag. From Task 037's `getMcpRiskProfile`.
- **churn**: number of versions in the last 90 days; latest `changeKind`; count of breaking changes in that window. From Task 038.
- **usage**: 30-day invocation count, error rate, top 3 tools by volume, unique caller count. From Task 039 daily rollups. Returns `null` for servers with no recorded invocations.

### 4. AI Analysis Prompt Extensions

Update the comparison agent prompt to handle MCP servers: "When all compared APIs are MCP servers, focus the narrative on (a) tool coverage gaps, (b) schema strictness trade-offs, (c) risk posture, and (d) which server is the better default for typical developer use cases."

### 5. Frontend — MCP Compare View

`app/compare/components/`:

- `McpToolOverlapTable.tsx` — renders the overlap matrix with tooltips for cell details. Sticky first column (tool name).
- `McpSchemaQualityBars.tsx` — horizontal bar chart, one row per metric per server.
- `McpRiskProfileGrid.tsx` — small-multiples chip grid (one card per server).
- `McpChurnTimeline.tsx` — sparkline of versions + breaking change markers, per server.
- `McpUsageSummary.tsx` — three-column small-multiples (call count, error rate, top tools).

`CompareTable.tsx` is updated to recognise the MCP aspect set and route those rows to the new components.

### 6. Compatibility Filter

When the user is comparing servers, surface a small "filter" at the top: "Show only tools available in at least N servers." This makes the matrix readable when comparing 4 servers with 50+ tools each.

### 7. Backwards Compatibility

Mixed selections (e.g. one REST + two MCP) fall back to the generic comparison — the new MCP aspects are not rendered. The MCP aspects are gated on `selectedApis.every(a => a.kind === 'mcp')`.

## Testing & Acceptance Criteria

- [ ] Tool overlap matrix correctly identifies present/absent for fixture servers.
- [ ] `schemaCompatibility` classification matches the spec for each fixture pair (identical / superset / divergent / incompatible).
- [ ] All five MCP aspects render when all selected APIs are MCP.
- [ ] Mixed REST + MCP selection falls back to the generic six aspects.
- [ ] `mcp.usage` returns `null` gracefully when no invocations have been recorded.
- [ ] AI analysis prompt produces a narrative that mentions tool coverage and risk posture (smoke test against a known fixture).
- [ ] `CompareSelector` allows up to 4 MCP servers (existing limit honored).
- [ ] Tool overlap matrix tooltips show schema fingerprint and per-cell compatibility.
- [ ] "Show only tools in ≥ N servers" filter narrows the matrix.
- [ ] E2E: User compares two MCP servers, sees the matrix, and the matrix highlights a unique tool on one server.

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
**Task**: Implement plan step 040 — MCP Server Comparison.

Read the full task specification at `docs/project/plan/040-mcp-server-comparison.md`.

Reference `docs/project/plan/024-api-comparison-feature.md` for the comparison framework, `docs/project/plan/036-mcp-capability-indexing.md` for snapshot data, `docs/project/plan/037-mcp-governance-rules.md` for the risk profile tool, `docs/project/plan/038-mcp-capability-drift-detection.md` for churn signals, and `docs/project/plan/039-mcp-invocation-audit-log.md` for usage rollups.

Extend the compare aspect union with five MCP aspects (toolSurface, schemaQuality, riskProfile, churn, usage). Build a deterministic tool-compatibility helper. Implement an mcp_compare_service that aggregates each aspect from existing data sources without reaching live MCP servers. Add the AI prompt extension. Build new frontend components for the tool overlap matrix, schema quality bars, risk profile grid, churn timeline, and usage summary. Gate MCP aspects on every selected API being kind=mcp; fall back to generic compare otherwise.

Write unit tests for the compatibility classifier, every aspect computation, and the gating logic. Add an E2E test that compares two MCP fixtures and validates the matrix.

**Living Document Update**: After completing implementation, update this plan document:
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
