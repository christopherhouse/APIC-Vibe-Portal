# 039 - MCP Invocation Audit Log

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Persistence (Cosmos DB), Observability
- [PII Handling](../../architecture/pii-handling.md)
- [Data Retention Policy](../../architecture/data-retention-policy.md)
- [033 — MCP Inspector Integration](033-mcp-inspector-integration.md)
- [020 — Security Trimming](020-security-trimming.md)
- [028 — Analytics Data Collection](028-analytics-data-collection.md)

## Overview

Today the MCP Inspector invokes a tool and forgets — the result is shown to the caller and discarded. There is no audit trail, no usage signal for ranking tools in search, and no way for a security review to answer "who called what tool, when, with what arguments."

This task persists every Inspector tool invocation as a structured audit record, exposes per-server and per-tool admin views, and emits aggregated usage metrics that downstream features (search ranking in Task 036, comparison in Task 040) can consume.

The log is **append-only**, **PII-scrubbed**, and **retention-bounded** in line with the project's existing data governance baseline.

## Dependencies

- **033** — MCP Inspector Integration (the invocation surface)
- **016** — Persistence baseline (Cosmos DB containers, soft-delete patterns)
- **020** — Security Trimming (caller identity)
- **028** — Analytics Data Collection (rollup pipeline)
- **019** — App Insights telemetry

## Implementation Details

### 1. Audit Record Schema

Add a Cosmos container `mcp-invocations` (partition key `/apiId`).

```typescript
interface McpInvocationRecord {
  id: string;                // uuid
  apiId: string;
  apiName: string;
  versionName: string | null;
  toolName: string;
  invokedAt: string;         // ISO timestamp
  invokedBy: {
    userOid: string;         // Entra object ID
    tenantId: string;
    roles: string[];
  };
  arguments: {
    keys: string[];          // top-level argument names only
    hash: string;            // sha256 of canonicalised JSON
    sizeBytes: number;
    redactedSnippet: string | null;  // first 200 chars, PII-scrubbed
  };
  result: {
    isError: boolean;
    durationMs: number;
    contentItemCount: number;
    contentSizeBytes: number;
    errorCode: string | null;
  };
  source: 'inspector' | 'playground' | 'agent';
  schemaVersion: 1;
  ttl: number;               // Cosmos TTL — default 90 days
}
```

**What we deliberately do _not_ store**: full argument values, full result text, server URLs (already in catalog), bearer tokens. The `hash` enables de-duplication and "this same call has been made before" lookups without retaining payloads.

### 2. PII Scrubbing

`redactedSnippet` runs the existing PII redactor (`docs/architecture/pii-handling.md`) over a JSON-stringified argument set, truncated to 200 chars. Document this in `pii-handling.md` as a new emission point.

### 3. Persistence Hook

Modify `routers/mcp_inspector.py:invoke_mcp_tool` to write the audit record after the upstream call returns (success or failure). Writes are best-effort — a Cosmos failure logs a warning but does not fail the user-facing response (same posture as Redis cache failures).

The write happens via a new `McpInvocationRepository` in `services/` mirroring the existing repository pattern.

### 4. Admin & Owner Views

```
app/admin/mcp-invocations/                         # admin global view
app/catalog/[apiId]/components/McpInvocationsTab.tsx  # per-API owner view
```

**Admin global view** (`Portal.Admin` only):

- Filterable table: `apiId`, `userOid`, `toolName`, time range, error-only.
- Columns: timestamp, server, tool, user, duration, status (OK / Error), arguments hash.
- CSV export.

**Per-API tab** (visible to `Portal.Maintainer` and `Portal.Admin` for that API):

- Last 30 days of invocations on this server.
- Top tools by call count + error rate.
- Sparkline of daily volume.
- "Most active users" (anonymised counts unless caller is admin).

### 5. BFF Endpoints

```
src/bff/apic_vibe_portal_bff/routers/mcp_invocations.py
```

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `GET`  | `/api/mcp/invocations`              | `Portal.Admin`                    | Global list with filters |
| `GET`  | `/api/mcp/{apiId}/invocations`      | `Portal.Maintainer`, `Portal.Admin` | Per-API list (security trimmed) |
| `GET`  | `/api/mcp/{apiId}/invocations/stats`| `Portal.Maintainer`, `Portal.Admin` | Aggregates: counts, error rate, top tools, daily series |

All endpoints support `from`, `to`, `toolName`, `userOid`, `errorOnly` query parameters. Results are paginated (`continuationToken`).

### 6. Analytics Rollup

Extend the analytics worker (Task 028) to compute daily aggregates per `apiId`/`toolName`:

- `mcp_tool_invocations_daily` Cosmos container with `(apiId, toolName, date)` keys.
- Counts: total, errors, p50/p95 duration, unique users.
- Used by Task 040 (comparison) and Task 036 (search ranking signal).

### 7. Telemetry

Emit two App Insights custom events:

- `mcp.tool.invoked` — minimal: `apiId`, `toolName`, `durationMs`, `isError`. Fires on every call.
- `mcp.tool.error` — fires only on error with `errorCode` and `apiId`.

### 8. Privacy & Compliance

- The audit log is in-scope for the GDPR erasure flow defined in the data retention policy: erasing a user must delete or anonymise records matching their `userOid`.
- TTL of 90 days is the default; an admin setting in `runtime-config` allows extension to 365 days for highly-regulated tenants.
- Document the new log in `docs/architecture/pii-handling.md` and `docs/architecture/data-retention-policy.md`.

## Testing & Acceptance Criteria

- [ ] Inspector `tools/call` writes an `McpInvocationRecord` on success and on error.
- [ ] Cosmos write failures do not propagate to the caller (best-effort).
- [ ] Argument hash is deterministic across equivalent payloads (key-order independent).
- [ ] `redactedSnippet` does not exceed 200 chars and PII patterns (email, phone, GUID-like tokens) are masked.
- [ ] Records have a TTL field set to the configured retention.
- [ ] Admin endpoint returns paginated results with all documented filters working.
- [ ] Per-API endpoint returns 403 for users without Maintainer/Admin on that API (security trimmed).
- [ ] Stats endpoint returns counts, error rate, top tools, daily series for the configured window.
- [ ] Admin invocations page renders, filters, and exports CSV.
- [ ] Per-API tab renders top tools, error rate, sparkline.
- [ ] Daily rollup container is populated by the analytics worker.
- [ ] App Insights events `mcp.tool.invoked` and `mcp.tool.error` fire with correct dimensions.
- [ ] GDPR erasure of a user wipes/anonymises their `userOid` from `mcp-invocations`.

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
**Task**: Implement plan step 039 — MCP Invocation Audit Log.

Read the full task specification at `docs/project/plan/039-mcp-invocation-audit-log.md`.

Reference `docs/project/plan/033-mcp-inspector-integration.md` for the invocation entry point, `docs/project/plan/016-persistence-data-governance-baseline.md` for the repository pattern and TTL handling, `docs/project/plan/020-security-trimming.md` for caller identity, and `docs/architecture/pii-handling.md` for the redaction utility.

Add a Cosmos container `mcp-invocations` with the schema in §1. Hook the inspector's `invoke_mcp_tool` to write a redacted, hashed audit record on every call (best-effort — don't fail user requests on write errors). Build admin and per-API listing/stats endpoints with RBAC + security trimming. Add the admin invocations page and the per-API invocations tab. Extend the analytics worker to roll up daily aggregates. Emit `mcp.tool.invoked` and `mcp.tool.error` App Insights events. Wire the new container into the GDPR erasure flow.

Do NOT persist full argument or result content — only key names, hash, size, redacted snippet, and result metadata.

Write unit tests covering hashing determinism, redaction, RBAC, write-failure tolerance, and the rollup math. Add an E2E test that invokes a tool and verifies the audit row.

**Living Document Update**: After completing implementation, update this plan document:
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
