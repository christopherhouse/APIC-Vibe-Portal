# 038 - MCP Capability Drift Detection (Inter-Version)

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Persistence (Cosmos DB)
- [Product Charter](../apic_product_charter.md) — Improve API discovery; metadata completeness
- [009 — API Center Data Layer](009-api-center-data-layer.md)
- [036 — MCP Capability Indexing](036-mcp-capability-indexing.md) — capability snapshot source
- [037 — MCP Governance Rules](037-mcp-governance-rules.md)

## Overview

When an API owner publishes a new version of an MCP server in API Center, consumers need to know what changed: which tools were added, removed, or had their input schemas altered, and which prompts/resources moved. Today this requires manually reading two specs side-by-side.

This task computes a **structured diff between two capability snapshots of the same MCP API** (typically consecutive versions) and surfaces it in the catalog UI as a "What's changed" view. It also triggers governance signals (e.g. "breaking change without major version bump") that the rule engine can act on.

**Critical scope constraint**: The diff is computed exclusively between snapshots stored in Cosmos by Task 036 — i.e. between definition payloads registered in API Center. No live MCP endpoint is contacted. We do not assume the indexer or BFF can reach upstream MCP servers.

## Dependencies

- **036** — MCP Capability Indexing (snapshot source)
- **037** — MCP Governance Rules (consumes drift events)
- **019** — Application Insights (drift telemetry)

## Implementation Details

### 1. Diff Algorithm

Add a shared TypeScript module and a Python mirror:

```
src/shared/src/mcp/capability-diff.ts
src/bff/apic_vibe_portal_bff/services/mcp_capability_diff_service.py
```

Function signature:

```typescript
function diffCapabilities(
  before: McpCapabilitySnapshot,
  after: McpCapabilitySnapshot,
): McpCapabilityDiff;

interface McpCapabilityDiff {
  apiId: string;
  fromVersion: string;
  toVersion: string;
  tools: {
    added: McpTool[];
    removed: McpTool[];
    changed: McpToolChange[];     // per-field diff
    unchanged: number;
  };
  prompts: { added; removed; changed; unchanged };
  resources: { added; removed; changed; unchanged };
  breakingChanges: BreakingChange[];
  changeKind: 'major' | 'minor' | 'patch' | 'none';
}

interface McpToolChange {
  name: string;
  descriptionChanged: boolean;
  inputSchemaChanges: SchemaChange[];   // added/removed/typeChanged/requiredChanged
  isBreaking: boolean;
}
```

**Breaking change classification** (drives `changeKind`):

| Change                                                 | Severity     |
| ------------------------------------------------------ | ------------ |
| Tool removed                                           | major        |
| Required parameter added to existing tool              | major        |
| Parameter type changed                                 | major        |
| Resource URI removed                                   | major        |
| Optional parameter added to existing tool              | minor        |
| Tool added                                             | minor        |
| Description-only change                                | patch        |
| Prompt argument required → optional                    | minor        |

The classification is a pure function — no LLM, no I/O — so it is deterministic and trivially testable.

### 2. Persistence

Add a `mcp-capability-diffs` Cosmos container (partition key `/apiId`) keyed by `${apiId}__${fromVersion}__${toVersion}`. Diffs are computed on demand and cached so the BFF does not recompute on every page load.

### 3. Diff Trigger

Two trigger paths:

1. **Indexer-triggered**: When the indexer (Task 036) writes a new snapshot whose `definitionHash` differs from the previous snapshot for the same `apiId`, it enqueues a diff computation. The diff is persisted and a telemetry event `mcp.drift.detected` is emitted with `apiId`, `changeKind`, and counts.
2. **On-demand**: BFF endpoint allows callers to request an arbitrary `(fromVersion, toVersion)` pair — used by the UI when a user picks two versions to compare.

### 4. BFF Endpoints

```
src/bff/apic_vibe_portal_bff/routers/mcp_drift.py
```

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/mcp/{apiId}/drift/latest`                    | Diff between the latest version and the one before it |
| `GET`  | `/api/mcp/{apiId}/drift?from=&to=`                 | Diff between two arbitrary versions of the same API   |
| `GET`  | `/api/mcp/{apiId}/drift/history?limit=`            | List of historical diff records (changeKind + counts) |

All endpoints enforce the same RBAC + security trimming as the catalog. 422 if either version has no snapshot; 404 if the API does not exist.

### 5. Frontend — "What's Changed" Tab

On the API detail page for `kind=mcp` APIs, add a new tab **Changes** alongside the existing Inspector tab.

```
app/catalog/[apiId]/components/McpChangesTab.tsx
app/catalog/[apiId]/components/McpDriftSummaryCard.tsx
app/catalog/[apiId]/components/McpToolDiffRow.tsx
```

UI elements:

- Version selector (two dropdowns; default to latest two versions).
- A summary chip showing `changeKind` (Major / Minor / Patch / None) with color.
- Three collapsible sections (Tools, Prompts, Resources) listing added / removed / changed entries.
- For changed tools, render a parameter-level diff: `+ required: city (string)`, `- type: number → string`.
- A "Breaking changes" banner if any are present, with a link to the relevant tool sections.

### 6. Governance Hook

Task 037's rule engine gains a derived rule that consumes the latest diff:

- `mcp.versioning.breaking_change_requires_major_bump` (severity: critical) — fails when the diff between two adjacent versions is `major` but the API's `version` string didn't increment its major component (best-effort regex on `^v?(\d+)\.`).

This rule is added in 037's mcp_rules.py but its trigger lives here because the diff store is the data source.

### 7. Telemetry

Emit App Insights events:

- `mcp.drift.detected` — `apiId`, `fromVersion`, `toVersion`, `changeKind`, `toolsAdded`, `toolsRemoved`, `toolsChanged`.
- `mcp.drift.breaking_change` — for each entry in `breakingChanges`.

These feed the analytics dashboard so platform owners can spot churn hotspots.

## Testing & Acceptance Criteria

- [ ] `diffCapabilities` is a pure function with no I/O dependencies.
- [ ] Unit tests cover: tool added/removed/renamed; required-param added/removed; type changed; description-only change; prompts; resources; identical snapshots → `none`.
- [ ] Breaking-change classification matches the table in §1 for every fixture case.
- [ ] Diff is persisted to Cosmos and retrieved by `id`.
- [ ] Indexer triggers diff computation only when `definitionHash` changes.
- [ ] All three BFF endpoints enforce RBAC + security trimming.
- [ ] `GET /api/mcp/{apiId}/drift?from=&to=` returns 422 when a snapshot is missing.
- [ ] Frontend Changes tab renders for MCP APIs with ≥ 2 versions, hidden otherwise.
- [ ] Parameter-level diff is shown for each changed tool.
- [ ] Breaking-change banner appears only when `breakingChanges` is non-empty.
- [ ] Governance rule `breaking_change_requires_major_bump` fires for the matching fixture.
- [ ] E2E: User navigates to an MCP API with two versions, opens the Changes tab, and sees the expected added/removed/changed counts.

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
**Task**: Implement plan step 038 — MCP Capability Drift Detection (Inter-Version).

Read the full task specification at `docs/project/plan/038-mcp-capability-drift-detection.md`.

Reference `docs/project/plan/036-mcp-capability-indexing.md` for the snapshot data source, `docs/project/plan/037-mcp-governance-rules.md` for the consuming governance rule, and `docs/project/plan/019-observability-app-insights.md` for telemetry conventions.

Implement a pure-function diff (TS in `src/shared`, Python mirror in the BFF service layer) over two capability snapshots, with explicit breaking-change classification. Persist computed diffs in a new `mcp-capability-diffs` Cosmos container. Trigger diff computation from the indexer when a new snapshot's `definitionHash` changes. Add three BFF endpoints (latest, arbitrary from/to, history) with RBAC + security trimming. Build the Changes tab in the API detail page with version pickers, change-kind chip, tool/prompt/resource diff sections, parameter-level diffs for changed tools, and a breaking-change banner. Wire `mcp.drift.detected` and `mcp.drift.breaking_change` App Insights events.

The diff must NEVER call live MCP endpoints — operate exclusively on stored snapshots.

Write unit tests for every diff and breaking-change case in §1 of the plan, plus an E2E test for the Changes tab.

**Living Document Update**: After completing implementation, update this plan document:
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
