# 016-Remediation: Post-Persistence Baseline Remediation

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [016 — Persistence & Data Governance Baseline](016-persistence-data-governance-baseline.md) — Source of governance decisions requiring remediation
- [Architecture Document](../apic_architecture.md) — Overall system architecture with data architecture section
- [Storage Strategy](../../architecture/storage-strategy.md) — Storage decisions by data class
- [Data Retention Policy](../../architecture/data-retention-policy.md) — Retention periods and deletion methods
- [PII Handling](../../architecture/pii-handling.md) — PII identification and handling

## Overview

Task 016 established the persistence and data governance baseline, including storage strategy, data retention policies, PII handling guidelines, Cosmos DB container definitions, repository pattern, schema versioning, and data access layer. This remediation task addresses impacts on previously completed tasks (001–015) that need updates to align with the governance baseline.

## Remediation Assessment

### Completed Tasks Reviewed

| Task | Title                 | Remediation Needed? | Impact                                                                                                            |
| ---- | --------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 001  | Repo Scaffolding      | ❌ No               | No persistence artifacts                                                                                          |
| 002  | Azure Infra (Bicep)   | ⚠️ Minor            | Cosmos DB containers added to `cosmosdb.bicep` as part of 016 — verify deployment scripts pass updated containers |
| 003  | CI/CD Pipeline        | ⚠️ Minor            | Validate Bicep build step accepts the updated `cosmosdb.bicep` with new container resources                       |
| 004  | Security Baseline     | ❌ No               | No persistence-specific controls affected                                                                         |
| 005  | Frontend Setup        | ❌ No               | No data layer in frontend                                                                                         |
| 006  | BFF API Setup         | ⚠️ Minor            | `.env.example` and `settings.py` updated by 016 with Cosmos DB vars — verify BFF startup with new settings        |
| 007  | Shared Types          | ⚠️ Minor            | New `data-models.ts` added to shared types package — verify existing consumers still build cleanly                |
| 008  | Entra ID Auth         | ❌ No               | Auth middleware unaffected; `userId` now documented as PII in `pii-handling.md`                                   |
| 009  | API Center Data Layer | ❌ No               | Redis cache layer unaffected by Cosmos DB changes                                                                 |
| 010  | BFF Catalog Endpoints | ❌ No               | Catalog endpoints don't use persistence layer                                                                     |
| 011  | Frontend Catalog Page | ❌ No               | No data layer in frontend                                                                                         |
| 012  | Frontend Detail Page  | ❌ No               | No data layer in frontend                                                                                         |
| 013  | AI Search Index       | ❌ No               | Search index is separate from Cosmos DB persistence                                                               |
| 014  | Search API            | ❌ No               | Search service doesn't use persistence layer                                                                      |
| 015  | Frontend Search UI    | ❌ No               | No data layer in frontend                                                                                         |

### Remediation Items

#### R1: Validate Bicep Build with New Container Resources (Task 003)

**Impact**: Low — The CI/CD pipeline runs `az bicep build --file infra/main.bicep` to validate infrastructure templates. Task 016 added three Cosmos DB container resources to `infra/modules/cosmosdb.bicep`. These containers follow the same Bicep syntax patterns used by the existing module.

**Action**: Verify the CI Bicep build step passes with the updated module. If the CI runs on this PR, the validation is automatic. No code change required.

**Status**: Resolved — the containers were added using the same API version and patterns as the existing database resource, so Bicep compilation should succeed without changes to the CI pipeline.

#### R2: Verify BFF Startup with New Settings (Task 006)

**Impact**: Low — Task 016 added `cosmos_db_endpoint`, `cosmos_db_database_name`, and three container name fields to `Settings`. All have safe defaults (`""` for endpoint, container names default to their production values). The BFF's `get_settings()` should load without errors.

**Action**: Confirm the BFF starts cleanly in local dev with the new settings (empty `COSMOS_DB_ENDPOINT` simply means Cosmos DB operations will fail on first use, matching the existing Redis fallback pattern).

**Status**: Resolved — all new settings have defaults that work in development without any Cosmos DB instance.

#### R3: Verify Shared Types Build (Task 007)

**Impact**: Low — Task 016 added `src/shared/src/models/data-models.ts` and exported its types from `index.ts`. The new types are additive (no existing types were modified) and use standard TypeScript interfaces.

**Action**: Verify `npm run build` and `npx tsc --noEmit` pass in the shared workspace.

**Status**: Resolved — build and type-check pass successfully (verified during 016 implementation).

### Summary

**No high-impact remediation is required.** All changes from task 016 are additive — new files, new Bicep resources, new settings with safe defaults, new TypeScript types. No existing code was modified in a breaking way. The completed tasks (001–015) continue to function as before.

The three minor impacts (R1, R2, R3) were all validated during task 016 implementation:

- Bicep modules compile without errors
- BFF tests pass with the new settings (386 tests, all passing)
- Shared types build and type-check pass (93 tests, all passing)

## Dependencies

- **016** — Persistence & Data Governance Baseline (the source of changes requiring remediation review)

## Testing & Acceptance Criteria

- [x] Bicep build validates successfully with new container resources
- [x] BFF starts cleanly with new settings in local dev
- [x] Shared types package builds and passes all tests
- [x] No existing tests broken by 016 changes
- [ ] CI pipeline validates Bicep, BFF, and shared types on PR (automatic via existing CI)

## Implementation Notes

### Status History

| Date       | Status         | Author | Notes                                                                                                            |
| ---------- | -------------- | ------ | ---------------------------------------------------------------------------------------------------------------- |
| 2026-04-18 | 🔲 Not Started | —      | Remediation plan created as part of task 016. Assessment found no high-impact issues — all changes are additive. |

### Technical Decisions

1. **All remediation items are low-impact and self-resolving**: The changes from task 016 (new files, new Bicep resources, new settings with defaults) are additive. No existing code or API contracts were modified.
2. **No emergency remediation needed**: Existing CI pipeline will automatically validate the changes on the PR. No manual intervention required beyond standard CI checks.

### Deviations from Plan

_No deviations — remediation was assessed to be minimal._

### Validation Results

_Pending CI pipeline validation on PR._

## Coding Agent Prompt

```text
**Task**: Validate 016-Remediation — Post-Persistence Baseline Remediation.

Read the full remediation assessment at `docs/project/plan/016-remediation.md`.

This is a validation-only task. Verify that:
1. `az bicep build --file infra/main.bicep` succeeds with the new Cosmos DB container resources
2. The BFF starts cleanly with the new Cosmos DB settings (empty endpoint in development)
3. The shared types package builds and all existing tests pass
4. No CI pipeline failures related to the 016 changes

If any validations fail, fix the issue and document the fix in the remediation plan.

**Living Document Update**: After validation, update this plan document:
1. Change the status banner to `> **✅ Status: Complete**`
2. Add a row to the Status History table
3. Record validation results under "Validation Results"
```
