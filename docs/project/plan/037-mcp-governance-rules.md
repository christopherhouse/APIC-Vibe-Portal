# 037 - MCP Governance & Best-Practices Rules

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Multi-agent design, Governance Agent
- [Product Charter](../apic_product_charter.md) — Provide governance visibility
- [023 — Governance & Compliance Agent](023-governance-agent.md) — rule engine + scoring
- [025 — Governance Dashboard UI](025-governance-dashboard-ui.md)
- [036 — MCP Capability Indexing](036-mcp-capability-indexing.md) — capability snapshot data source

## Overview

The existing governance rule engine (Task 023) checks API-level metadata (description, contacts, license, lifecycle, etc.). For MCP servers it leaves the most consequential surface — the **tools** themselves — completely unchecked. A server that exposes a `delete_everything` tool with no description and no input schema scores the same as one with carefully-typed, well-documented tools.

This task adds a category of MCP-specific rules that operate on the capability snapshots produced by Task 036 and integrates them into the existing scoring, dashboard, and remediation flows. Rules cover **metadata quality, schema strictness, security posture, and naming hygiene** — all derived from data already in APIC, with no live network access required.

## Dependencies

- **023** — Governance Agent (rule engine, severity model, scoring, agent tools)
- **025** — Governance Dashboard UI (presentation surface)
- **036** — MCP Capability Indexing (capability snapshot data source)

## Implementation Details

### 1. Rule Authoring

Add `src/bff/apic_vibe_portal_bff/agents/governance_agent/rules/mcp_rules.py` defining at least the following rules. Each rule operates on a `(api: dict, snapshot: McpCapabilitySnapshot | None)` pair so it can short-circuit gracefully on non-MCP APIs.

**Metadata quality**

| Rule ID                              | Severity | Description                                                |
| ------------------------------------ | -------- | ---------------------------------------------------------- |
| `mcp.tools.have_descriptions`        | warning  | Every tool has a non-empty `description` ≥ 20 chars        |
| `mcp.tools.unique_names`             | critical | No duplicate tool names within the server                  |
| `mcp.prompts.have_descriptions`      | info     | Every prompt has a description                             |
| `mcp.resources.have_mime_type`       | info     | Every resource declares a `mimeType`                       |

**Schema strictness**

| Rule ID                              | Severity | Description                                                |
| ------------------------------------ | -------- | ---------------------------------------------------------- |
| `mcp.tools.input_schema_present`     | warning  | Every tool declares an `inputSchema` (object schema)       |
| `mcp.tools.required_fields_declared` | warning  | Tools with input schemas declare a `required` array        |
| `mcp.tools.no_freeform_object`       | info     | Tools do not accept untyped `additionalProperties: true`   |
| `mcp.tools.parameter_descriptions`   | info     | ≥ 80 % of input parameters have descriptions               |

**Security & risk posture**

| Rule ID                              | Severity | Description                                                |
| ------------------------------------ | -------- | ---------------------------------------------------------- |
| `mcp.tools.destructive_verb_review`  | critical | Tools whose name matches `^(delete|drop|destroy|wipe|purge|truncate)_` MUST set a `destructive` annotation in the description (e.g. `[destructive]`) |
| `mcp.tools.no_shell_passthrough`     | critical | No tool named `exec`, `shell`, `run_command`, or accepting a single string parameter named `command` / `cmd` without a documented allowlist |
| `mcp.tools.auth_documented`          | warning  | API description references the auth scheme (Entra / OAuth / API key) the MCP server expects |
| `mcp.tools.write_tools_capped`       | info     | Surface count of write-style tools (`create_*`, `update_*`, `delete_*`) so reviewers can spot scope creep |

**Naming hygiene**

| Rule ID                              | Severity | Description                                                |
| ------------------------------------ | -------- | ---------------------------------------------------------- |
| `mcp.tools.snake_case`               | info     | Tool names match `^[a-z][a-z0-9_]*$`                       |
| `mcp.tools.no_ambiguous_names`       | info     | Tool name is not a single generic verb (`get`, `update`, `process`) |

Each rule must include `remediation` text written for an API owner — concrete, copy-paste-actionable.

### 2. Rule Engine Integration

- Extend `compliance_checker.py` to thread the `snapshot` through to MCP rules.
- Snapshots are fetched via the read accessor introduced in Task 036; missing snapshots short-circuit MCP rules to `not_applicable` (do _not_ count as failures).
- MCP rules must **not** affect the scoring of non-MCP APIs (route via the existing `applicable_to` predicate).
- Add a per-category breakdown to `ComplianceResult` so the dashboard can render MCP rule outcomes in their own group.

### 3. Governance Agent Tools

Add two new tools on the existing Governance Agent:

- `getMcpRiskProfile(apiId)` — returns the destructive/write tool counts, schema-strictness score, and security flags for a single MCP server.
- `listMcpServersFailingRule(ruleId)` — returns MCP APIs failing a specific rule, used by admin queries.

Update the system prompt (`agents/prompts/governance_system.md`) so the agent can reason about MCP-specific concerns (destructive tools, schema strictness, auth documentation).

### 4. Governance Dashboard UI

`app/governance/` and `app/catalog/[apiId]/`:

- On the API detail compliance tab for MCP APIs, render a **"MCP Capability Rules"** panel grouping the new rules with per-tool breakdowns (which specific tool failed which rule).
- On the dashboard, add a filter chip "MCP Servers" that limits the view to `kind=mcp`.
- Add a "Risk profile" mini-card to MCP API detail compliance: destructive tools count, write tools count, schema strictness %, auth documented yes/no.

### 5. Telemetry & Backfill

- Emit `governance.mcp_rule_evaluated` with `ruleId`, `apiId`, `passed`, `severity` for analytics.
- The Governance worker's existing scheduled run picks up MCP rules automatically once snapshots exist; provide a one-shot CLI script `scripts/recompute-mcp-governance.py` for backfill.

## Testing & Acceptance Criteria

- [ ] All rules above implemented with rule IDs matching spec, each with remediation text.
- [ ] Each rule has unit tests covering pass, fail, and `not_applicable` paths (≥ 3 tests per rule).
- [ ] Non-MCP APIs see no change in score after MCP rules are introduced (regression test against fixture).
- [ ] APIs with no capability snapshot evaluate MCP rules as `not_applicable`.
- [ ] `getMcpRiskProfile` returns destructive/write counts, schema strictness, auth-documented flag.
- [ ] `listMcpServersFailingRule` filters to MCP APIs only.
- [ ] Governance dashboard renders MCP filter chip and risk-profile card.
- [ ] Per-tool breakdown shows _which_ tool failed each rule (not just the server).
- [ ] Backfill script processes a fixture APIC of ≥ 10 MCP APIs end-to-end.

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
**Task**: Implement plan step 037 — MCP Governance & Best-Practices Rules.

Read the full task specification at `docs/project/plan/037-mcp-governance-rules.md`.

Reference `docs/project/plan/023-governance-agent.md` for the rule engine, severity model, and scoring; `docs/project/plan/025-governance-dashboard-ui.md` for the dashboard surface; and `docs/project/plan/036-mcp-capability-indexing.md` for the capability snapshot data source.

Add an MCP rule module under `agents/governance_agent/rules/mcp_rules.py` with rules covering metadata quality, schema strictness, security/risk posture (destructive verbs, shell passthrough, auth documentation), and naming hygiene. Integrate with the existing compliance checker so non-MCP APIs are unaffected and MCP APIs without a snapshot evaluate to not_applicable. Add `getMcpRiskProfile` and `listMcpServersFailingRule` agent tools. Extend the governance dashboard with an MCP filter chip, a per-tool failure breakdown, and a risk-profile mini-card on MCP detail pages.

Write unit tests covering each rule (pass, fail, not_applicable) and a regression test verifying non-MCP API scores are unchanged. Verify all tests pass.

**Living Document Update**: After completing implementation, update this plan document:
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
