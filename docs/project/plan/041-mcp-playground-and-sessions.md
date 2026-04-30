# 041 - MCP Playground & Saved Sessions

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Persistence, BFF orchestration
- [Product Charter](../apic_product_charter.md) — Enable AI-assisted workflows
- [033 — MCP Inspector Integration](033-mcp-inspector-integration.md) — single-call inspector
- [039 — MCP Invocation Audit Log](039-mcp-invocation-audit-log.md) — invocation persistence
- [020 — Security Trimming](020-security-trimming.md)

## Overview

The current MCP Inspector is a one-shot tool: pick a tool, fill the form, see the result. Real-world MCP exploration is **multi-step** — call `list_files`, feed an output into `read_file`, then chain into `summarise`. The Inspector cannot represent this, and there is no way to save a verified sequence as documentation, a regression scenario, or a shareable example.

This task introduces a **Playground** mode on the API detail page that supports ordered tool sequences with cell-style outputs, and a **Saved Sessions** facility that lets users persist, name, share (within RBAC), and replay a sequence. Saved sessions also serve as durable, executable documentation: an API owner can publish "How to use this server" as a session that any consumer can replay.

## Dependencies

- **033** — MCP Inspector Integration
- **016** — Persistence baseline
- **020** — Security Trimming
- **039** — MCP Invocation Audit Log (writes still happen via the same hook)

## Implementation Details

### 1. Session Schema

Add a Cosmos container `mcp-sessions` (partition key `/apiId`).

```typescript
interface McpSession {
  id: string;                  // uuid
  apiId: string;
  apiName: string;
  versionName: string | null;
  ownerOid: string;            // creator
  name: string;
  description: string | null;
  visibility: 'private' | 'shared-org' | 'published';
  steps: McpSessionStep[];
  variables: Record<string, McpVariableSpec>;  // user-declared inputs
  createdAt: string;
  updatedAt: string;
  schemaVersion: 1;
}

interface McpSessionStep {
  stepId: string;              // ulid
  toolName: string;
  argumentsTemplate: string;   // JSON-with-$refs (see §3)
  notes: string | null;
  expectError: boolean;
}

interface McpVariableSpec {
  name: string;
  type: 'string' | 'number' | 'boolean';
  description: string | null;
  defaultValue: string | null;
}
```

Visibility tiers:

- **private** — visible only to `ownerOid`.
- **shared-org** — visible to any caller with read access to the API (security-trimmed).
- **published** — visible to any catalog reader; flagged in UI as official documentation. Only the API's `Portal.Maintainer` or `Portal.Admin` can publish.

### 2. Playground UI

```
app/catalog/[apiId]/components/McpPlaygroundTab.tsx
app/catalog/[apiId]/components/McpStepCell.tsx
app/catalog/[apiId]/components/McpSessionToolbar.tsx
app/catalog/[apiId]/components/McpVariableEditor.tsx
```

Layout: a notebook-style column of cells. Each cell:

- Tool selector (auto-completed against the capability list).
- Argument editor — same schema-driven form as the Inspector, plus the ability to insert `$ref` placeholders.
- "Run cell" button.
- Output area: result content + status chip + duration (reuses the Inspector's `InvokeResultPanel`).
- "Insert variable" / "Insert step output reference" controls.

A toolbar above the cells offers: Run all, Stop, Reset outputs, Save session, Open saved session, Share, Publish.

### 3. Step Output References

`argumentsTemplate` is a JSON object that may contain string-literal `$ref` placeholders:

- `"$step.<stepId>.content[0].text"` — pulls a value from a previous step's result.
- `"$var.<name>"` — pulls a user-declared variable.

A small reference resolver in `src/shared/src/mcp/session-runtime.ts` walks the template at runtime, evaluates each `$ref` against the live execution context, type-coerces according to the tool's input schema, and produces the final arguments object. Missing refs surface as a typed runtime error (`UNRESOLVED_REF`) before any upstream call.

### 4. BFF Endpoints

```
src/bff/apic_vibe_portal_bff/routers/mcp_sessions.py
```

| Method | Path | Description |
|--------|------|-------------|
| `POST`   | `/api/mcp/{apiId}/sessions`              | Create a session                     |
| `GET`    | `/api/mcp/{apiId}/sessions`              | List visible sessions for this API   |
| `GET`    | `/api/mcp/{apiId}/sessions/{sessionId}`  | Fetch a session                      |
| `PUT`    | `/api/mcp/{apiId}/sessions/{sessionId}`  | Update (owner or maintainer only)    |
| `DELETE` | `/api/mcp/{apiId}/sessions/{sessionId}`  | Soft delete (owner or admin only)    |
| `POST`   | `/api/mcp/{apiId}/sessions/{sessionId}/publish` | Maintainer/Admin only         |
| `POST`   | `/api/mcp/{apiId}/sessions/{sessionId}/run`     | Server-side run (see §5)        |

All endpoints enforce RBAC + security trimming on `apiId` and visibility-tier checks per session.

### 5. Session Runs — Two Modes

**Client-side** (default): The Playground UI runs each step by calling the existing `POST /api/mcp/{apiId}/invoke` endpoint per cell. Each call still writes an audit record (Task 039) with `source: 'playground'`.

**Server-side** (`/run`): Runs the entire session top-to-bottom on the BFF and returns an array of step results. Used for:

- Replay-from-link sharing (no client logic required).
- Regression checks invoked from the admin UI.
- Future scheduled "session-as-test" jobs.

Server-side runs are subject to a 60s wall-clock cap and a per-session step cap of 25.

### 6. Sharing & Permalinks

Each saved session has a permalink: `/catalog/{apiId}?tab=playground&session={sessionId}`. Loading the page with this URL opens the Playground tab pre-populated with the session.

Variables prompted from the user before "Run all" begins; defaults pre-fill the input.

### 7. Published Sessions on the API Detail Page

A new collapsible section on the Overview tab of MCP API detail pages: "Quickstart sessions" — lists `published` sessions for the API with a one-click "Open in playground" link. This makes published sessions act as executable documentation.

### 8. Variable Redaction

Variables marked `secret: true` are masked in the UI display, redacted from the audit log's `redactedSnippet`, and excluded from the published session export.

## Testing & Acceptance Criteria

- [ ] Playground tab renders for MCP APIs only.
- [ ] User can add, reorder, and delete cells.
- [ ] Schema-driven form per cell mirrors Inspector behaviour.
- [ ] `$step.<id>.…` references resolve at run-time and produce correct typed arguments.
- [ ] `$var.<name>` references prompt the user before "Run all".
- [ ] `UNRESOLVED_REF` surfaces a typed error without invoking the upstream tool.
- [ ] Each Playground cell run writes an audit record with `source: 'playground'`.
- [ ] Save session → list session → reload session round-trips faithfully.
- [ ] Visibility-tier RBAC: private sessions invisible to non-owner; shared-org honors security trimming; published gated on Maintainer/Admin.
- [ ] Permalink to a session opens Playground pre-populated.
- [ ] Server-side `/run` returns all step results within wall-clock + step-count caps.
- [ ] Secret variables are masked in UI and audit `redactedSnippet`.
- [ ] Published sessions appear on the Overview tab Quickstart section.
- [ ] E2E: Create a 3-step session that chains list → read → summarise; save; reopen; run all; verify the chained outputs.

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
**Task**: Implement plan step 041 — MCP Playground & Saved Sessions.

Read the full task specification at `docs/project/plan/041-mcp-playground-and-sessions.md`.

Reference `docs/project/plan/033-mcp-inspector-integration.md` for the existing tool-call surface and form patterns; `docs/project/plan/039-mcp-invocation-audit-log.md` for the audit hook (Playground runs must still write audit records with source='playground'); `docs/project/plan/020-security-trimming.md` for visibility-tier RBAC; and `docs/project/plan/016-persistence-data-governance-baseline.md` for the Cosmos repository pattern.

Build a notebook-style Playground tab on the MCP API detail page with cell-based ordered tool runs, schema-driven argument editing, and a `$step` / `$var` reference resolver implemented in src/shared. Persist sessions in a new `mcp-sessions` Cosmos container with three visibility tiers (private / shared-org / published) and RBAC-gated transitions. Add CRUD + publish + server-side run endpoints. Add a permalink-loadable share link and a Quickstart sessions panel on the Overview tab for published sessions.

Run modes: client-side (default, hits existing invoke endpoint per cell) and server-side `/run` (capped at 25 steps and 60s). Both must write audit records.

Write unit tests for the reference resolver, RBAC transitions, and run mode caps; an integration test for a 3-step chain; and an E2E test for save → reload → run-all.

**Living Document Update**: After completing implementation, update this plan document:
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
