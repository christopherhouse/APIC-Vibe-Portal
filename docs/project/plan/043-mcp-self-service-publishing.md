# 043 - MCP Server Self-Service Publishing

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — API Center, BFF, RBAC
- [Product Charter](../apic_product_charter.md) — Improve API discovery; metadata completeness
- [009 — API Center Data Layer](009-api-center-data-layer.md)
- [023 — Governance Agent](023-governance-agent.md)
- [036 — MCP Capability Indexing](036-mcp-capability-indexing.md)
- [037 — MCP Governance Rules](037-mcp-governance-rules.md)
- [034 — API Center Backup](034-api-center-backup.md) — entity export schema (informs registration payload)

## Overview

Today, registering a new MCP server in API Center is a Bicep / az-cli exercise — too friction-heavy for ad-hoc internal contributors. The result is a registry that grows write-only, where API owners ship servers but never get them into the catalog because the on-ramp is too steep.

This task adds a **self-service publishing flow**: a guided UI through which a developer submits a candidate MCP server, runs an automated validation pipeline (governance + schema + auth checks), and on success creates the corresponding API Center entry with metadata pre-filled from the candidate manifest. A submission stays in a pending state until a `Portal.Maintainer` or `Portal.Admin` approves it.

The validation pipeline reuses the rule set built in Task 037 — so the bar to enter the catalog is the same bar that governs what's already in it.

## Dependencies

- **009** — API Center Data Layer (write path)
- **023** — Governance Agent (rule engine)
- **036** — MCP Capability Indexing (definition parser, snapshot model)
- **037** — MCP Governance Rules (validation rule set)
- **020** — Security Trimming (RBAC)

## Implementation Details

### 1. Submission Schema

Add a Cosmos container `mcp-submissions` (partition key `/submitterOid`).

```typescript
interface McpSubmission {
  id: string;                     // uuid
  submitterOid: string;
  submitterEmail: string;
  status: SubmissionStatus;
  proposedApiId: string;          // slug, derived from name
  proposedName: string;
  description: string;
  contacts: Contact[];
  serverUrl: string;
  transport: 'streamable-http' | 'sse';
  authDescriptor: McpAuthDescriptor;
  definitionPayload: unknown;     // raw JSON the submitter uploaded
  validationReport: ValidationReport | null;
  reviewerOid: string | null;
  reviewNotes: string | null;
  createdAt: string;
  updatedAt: string;
  schemaVersion: 1;
}

type SubmissionStatus =
  | 'draft'             // submitter is still editing
  | 'validating'        // pipeline running
  | 'validation_failed' // critical rules failed
  | 'awaiting_review'   // passed validation, queued for human review
  | 'approved'          // registered into APIC
  | 'rejected'
  | 'withdrawn';
```

```typescript
interface ValidationReport {
  ranAt: string;
  passed: boolean;
  ruleResults: RuleResult[];     // reuses 023's RuleResult shape
  parserWarnings: string[];      // from the definition parser
  authPreflightResult: 'ok' | 'unreachable' | 'unauthenticated' | 'skipped';
}
```

### 2. Validation Pipeline

A single pure-ish service `McpSubmissionValidator` that runs the following checks against a submission:

1. **Definition parses** via the Task 036 shared parser.
2. **Capability counts** within configurable bounds (e.g. ≤ 200 tools).
3. **Critical governance rules** from Task 037 pass: `mcp.tools.unique_names`, `mcp.tools.no_shell_passthrough`, `mcp.tools.destructive_verb_review`, plus all metadata.* rules.
4. **Auth preflight** — best-effort. If the submitter provided an Entra-secured server URL and the BFF's managed identity has the relevant scopes, run an `initialize` call. If not, skip with `'skipped'` (this is the only place the BFF talks to the live MCP endpoint, and it's behind explicit configuration).
5. **Slug uniqueness** in API Center.

A submission is `validation_failed` if any critical rule fails. Warnings/info-severity rule failures are recorded but do not block.

### 3. Submitter UI

```
app/submit-mcp/                                    # new top-level page
├── page.tsx                                       # multi-step form
├── components/SubmissionStep1Metadata.tsx
├── components/SubmissionStep2Definition.tsx       # paste-or-upload
├── components/SubmissionStep3Auth.tsx
├── components/SubmissionStep4Review.tsx
├── components/SubmissionValidationPanel.tsx
└── components/MySubmissionsTable.tsx
```

- Wizard with metadata → definition upload → auth descriptor → review.
- Auto-derives a slug from name; lets the user edit.
- Step 4 runs the validator and renders the report inline. If validation fails, the user can edit and re-validate without losing state.
- On success, the submission moves to `awaiting_review`.
- A "My submissions" tab lists the user's submissions and their status.

### 4. Reviewer UI

```
app/admin/mcp-submissions/
├── page.tsx                                       # queue
└── [submissionId]/page.tsx                        # detail + approve/reject
```

- Queue table filtered by status, with sort by submitted-at and validation result.
- Detail page renders the full validation report (rule-by-rule), the proposed APIC entry preview, and approve/reject buttons.
- Approving triggers the **registration step** (§5).
- Rejection requires a reason that is emailed back to the submitter.

### 5. Registration Step (Approval → APIC Write)

The BFF writes the new API to API Center via the data-plane client:

- Create API resource with metadata from the submission.
- Create initial version `v1`.
- Upload the definition payload as a Definition document with the appropriate content type.
- Create deployment resource pointing to `serverUrl` with the configured environment.
- Apply tags and contact metadata.

If any APIC write fails, the submission is moved to a new state `registration_failed` and the partial APIC writes are rolled back where possible. A reviewer can retry.

After successful registration, the indexer (Task 036) picks up the new API on its next run and the capability snapshot is captured automatically.

### 6. BFF Endpoints

```
src/bff/apic_vibe_portal_bff/routers/mcp_submissions.py
src/bff/apic_vibe_portal_bff/services/mcp_submission_service.py
src/bff/apic_vibe_portal_bff/services/mcp_submission_validator.py
src/bff/apic_vibe_portal_bff/services/mcp_apic_registrar.py
```

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `POST`   | `/api/mcp/submissions`                        | any authenticated | Create draft |
| `GET`    | `/api/mcp/submissions/mine`                   | any authenticated | List own submissions |
| `GET`    | `/api/mcp/submissions/{id}`                   | submitter or reviewer | Fetch |
| `PUT`    | `/api/mcp/submissions/{id}`                   | submitter (only while editable) | Update draft fields |
| `POST`   | `/api/mcp/submissions/{id}/validate`          | submitter | Run validator |
| `POST`   | `/api/mcp/submissions/{id}/withdraw`          | submitter | Withdraw |
| `GET`    | `/api/mcp/submissions/queue`                  | Maintainer / Admin | Reviewer queue |
| `POST`   | `/api/mcp/submissions/{id}/approve`           | Maintainer / Admin | Approve & register |
| `POST`   | `/api/mcp/submissions/{id}/reject`            | Maintainer / Admin | Reject with reason |

### 7. Notifications

- Submitter: email on status transitions (`validation_failed`, `awaiting_review` confirmation, `approved`, `rejected`).
- Reviewers: in-portal badge on `/admin/mcp-submissions` showing pending count; optional Teams/email digest (configurable, off by default).

### 8. Observability

- App Insights events: `mcp.submission.created`, `mcp.submission.validated`, `mcp.submission.approved`, `mcp.submission.rejected`, `mcp.submission.registration_failed`.
- Submission audit log: status transitions tracked in a sub-collection so a reviewer can see who approved what and when.

### 9. Documentation

- New user-guide page `docs/user-guide/publishing-mcp-server.md` walking through the flow.
- New developer doc `docs/development/mcp-submission-validator.md` describing the validator's rule set, rule severity gates, and how to extend them.

## Testing & Acceptance Criteria

- [ ] Authenticated user can create, edit, and withdraw a submission.
- [ ] Wizard steps validate inputs and prevent invalid transitions.
- [ ] Validator runs all checks in §2 and produces a structured report.
- [ ] Critical-rule failures block transition to `awaiting_review`.
- [ ] Warning/info failures are recorded but do not block.
- [ ] Auth preflight degrades gracefully when the BFF cannot reach the upstream server (`'unreachable'`/`'skipped'` rather than a hard failure).
- [ ] Reviewer queue lists submissions in correct state and respects RBAC.
- [ ] Approve registers the API in APIC: API resource, version, definition, deployment, tags, contacts.
- [ ] Failed registration moves submission to `registration_failed` and surfaces the underlying error in the reviewer UI.
- [ ] Reject with reason transitions to `rejected` and notifies submitter (verified by email-fixture test).
- [ ] Indexer picks up the newly registered API and creates a capability snapshot on its next scheduled run.
- [ ] All `mcp.submission.*` App Insights events fire with the correct dimensions.
- [ ] Slug collisions in APIC are detected before registration is attempted.
- [ ] User can re-edit and re-validate a `validation_failed` submission without losing prior data.

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
**Task**: Implement plan step 043 — MCP Server Self-Service Publishing.

Read the full task specification at `docs/project/plan/043-mcp-self-service-publishing.md`.

Reference `docs/project/plan/009-api-center-data-layer.md` for the APIC write surface, `docs/project/plan/023-governance-agent.md` and `docs/project/plan/037-mcp-governance-rules.md` for the validator's rule set, `docs/project/plan/036-mcp-capability-indexing.md` for the definition parser and downstream indexing, and `docs/project/plan/020-security-trimming.md` for RBAC.

Build a four-step submission wizard, a Cosmos-backed submission store with the state machine in §1, a validator service that exercises Task 037's critical rules plus parser + slug uniqueness + optional live auth preflight, a reviewer queue + detail page, and an APIC registrar that creates API + version + definition + deployment on approval (with rollback on failure). Wire submitter and reviewer notifications. Emit App Insights `mcp.submission.*` events for every state transition.

The validator is the only place this feature is permitted to talk to a live MCP endpoint, and only behind explicit configuration. All other operations work from stored data.

Write unit tests for the validator (each rule, both pass and fail), the state machine, RBAC, and registrar rollback. Add an integration test for create → validate → approve → register, asserting the resulting APIC entry. Add an E2E test for the submitter wizard.

**Living Document Update**: After completing implementation, update this plan document:
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
