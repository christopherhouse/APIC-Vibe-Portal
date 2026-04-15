# APIC Vibe Portal — Implementation Plan Remediation Plan (Cloud Agent Handoff)

Date: 2026-04-14

## Goal

Apply the assessment findings by fixing sequencing, dependencies, and task coverage so execution can proceed in strict numeric order.

## Execution Constraints

1. Task flow must be contiguous and ordered: `001 -> 002 -> 003 -> ...`.
2. Any reordered task must be renumbered (file name, in-file title, dependencies, prompts, and README references).
3. Keep existing task content unless required by dependency/security/persistence remediations.
4. Add two new baseline tasks before feature-heavy work:
   - Security Baseline & Secure SDLC Controls
   - Persistence & Data Governance Baseline

## Target Sequenced Plan (New Numbering)

| New # | Source       | Task                                                        |
| ----- | ------------ | ----------------------------------------------------------- |
| 001   | existing 001 | Sprint Zero: Repository Scaffolding & GitHub Copilot Assets |
| 002   | existing 002 | Sprint Zero: Azure Infrastructure as Code (Bicep)           |
| 003   | existing 003 | Sprint Zero: CI/CD Pipeline with GitHub Actions             |
| 004   | **new**      | Security Baseline & Secure SDLC Controls                    |
| 005   | existing 004 | Frontend Next.js Setup                                      |
| 006   | existing 005 | BFF API Setup                                               |
| 007   | existing 006 | Shared Types Package                                        |
| 008   | existing 016 | Entra ID Authentication Integration                         |
| 009   | existing 007 | API Center Data Layer                                       |
| 010   | existing 008 | BFF Catalog Endpoints                                       |
| 011   | existing 009 | Frontend Catalog Page                                       |
| 012   | existing 010 | Frontend API Detail Page                                    |
| 013   | existing 011 | AI Search Index Setup                                       |
| 014   | existing 012 | Search API Implementation                                   |
| 015   | existing 013 | Frontend Search UI                                          |
| 016   | **new**      | Persistence & Data Governance Baseline                      |
| 017   | existing 014 | OpenAI Integration                                          |
| 018   | existing 015 | Frontend Chat UI                                            |
| 019   | existing 017 | Observability (App Insights)                                |
| 020   | existing 018 | Security Trimming                                           |
| 021   | existing 019 | MVP E2E Testing & Polish                                    |
| 022   | existing 020 | Foundry Agent Setup                                         |
| 023   | existing 021 | Governance Agent                                            |
| 024   | existing 022 | API Comparison Feature                                      |
| 025   | existing 023 | Governance Dashboard UI                                     |
| 026   | existing 024 | Multi-Agent Orchestration                                   |
| 027   | existing 025 | Phase 2 Integration Testing                                 |
| 028   | existing 026 | Analytics Data Collection                                   |
| 029   | existing 027 | Analytics Dashboard                                         |
| 030   | existing 028 | Metadata Completeness                                       |
| 031   | existing 029 | Performance & Accessibility                                 |
| 032   | existing 030 | Final Integration & Launch                                  |

## Required File Rename Map

### New task files to add

- `docs/project/plan/004-security-baseline-secure-sdlc-controls.md`
- `docs/project/plan/016-persistence-data-governance-baseline.md`

### Existing files to rename

- `004-frontend-nextjs-setup.md` -> `005-frontend-nextjs-setup.md`
- `005-bff-api-setup.md` -> `006-bff-api-setup.md`
- `006-shared-types-package.md` -> `007-shared-types-package.md`
- `007-api-center-data-layer.md` -> `009-api-center-data-layer.md`
- `008-bff-api-catalog-endpoints.md` -> `010-bff-api-catalog-endpoints.md`
- `009-frontend-api-catalog-page.md` -> `011-frontend-api-catalog-page.md`
- `010-frontend-api-detail-page.md` -> `012-frontend-api-detail-page.md`
- `011-ai-search-index-setup.md` -> `013-ai-search-index-setup.md`
- `012-search-api-implementation.md` -> `014-search-api-implementation.md`
- `013-frontend-search-ui.md` -> `015-frontend-search-ui.md`
- `014-openai-integration.md` -> `017-openai-integration.md`
- `015-frontend-chat-ui.md` -> `018-frontend-chat-ui.md`
- `016-entra-id-authentication.md` -> `008-entra-id-authentication.md`
- `017-observability-app-insights.md` -> `019-observability-app-insights.md`
- `018-security-trimming.md` -> `020-security-trimming.md`
- `019-e2e-testing-mvp-polish.md` -> `021-e2e-testing-mvp-polish.md`
- `020-foundry-agent-setup.md` -> `022-foundry-agent-setup.md`
- `021-governance-agent.md` -> `023-governance-agent.md`
- `022-api-comparison-feature.md` -> `024-api-comparison-feature.md`
- `023-governance-dashboard-ui.md` -> `025-governance-dashboard-ui.md`
- `024-multi-agent-orchestration.md` -> `026-multi-agent-orchestration.md`
- `025-phase2-integration-testing.md` -> `027-phase2-integration-testing.md`
- `026-analytics-data-collection.md` -> `028-analytics-data-collection.md`
- `027-analytics-dashboard.md` -> `029-analytics-dashboard.md`
- `028-metadata-completeness.md` -> `030-metadata-completeness.md`
- `029-performance-accessibility.md` -> `031-performance-accessibility.md`
- `030-final-integration-launch.md` -> `032-final-integration-launch.md`

## Dependency Fixes to Apply (Renumbered)

1. **017 OpenAI Integration**: must depend on **014 Search API**.
2. **022 Foundry Agent Setup**: add dependency on **014 Search API** (and optionally **020 Security Trimming** if enforced at this stage).
3. **024 API Comparison Feature**: add dependency on **023 Governance Agent**.
4. **025 Governance Dashboard UI**: add dependency on **008 Entra ID Auth** (and optionally **020 Security Trimming**).
5. **030 Metadata Completeness**: add dependencies on **012 API Detail UI** and **025 Governance Dashboard UI**.
6. **002 Azure IaC**: explicitly include Foundry Agent Service provisioning + RBAC prerequisites for step 022.

## New Task Scope Requirements

### 004 — Security Baseline & Secure SDLC Controls

Must define and enforce before feature implementation:

- Threat model baseline for frontend, BFF, and agent/data paths.
- CI security gates: SAST, dependency/container scanning, secret scanning, SBOM/provenance.
- Secrets management and rotation policy.
- Global API abuse protections (rate limiting and bot mitigation baseline).

### 016 — Persistence & Data Governance Baseline

Must define before trend/history-dependent work:

- Storage strategy by data class (chat, governance snapshots, analytics telemetry).
- Retention/deletion policy and PII handling.
- Partition/index/query strategy for trend workloads.
- Schema ownership/versioning and migration approach.

## Cloud Agent Execution Checklist

- [ ] Add the two new task docs using the existing task template structure.
- [ ] Rename task files to the new numbering.
- [ ] Update each task document title (`# NNN - ...`) and all intra-plan references.
- [ ] Update `docs/project/plan/README.md` task index, phase ranges, and dependency graph to 001–032.
- [ ] Apply dependency corrections listed above in each affected task doc.
- [ ] Update coding prompts so referenced step numbers/paths match renumbered files.
- [ ] Validate no stale old-step references remain (search for old filenames/IDs).

## Validation Commands (post-change)

Run from repo root:

```bash
git --no-pager diff --check
rg "docs/project/plan/0(0[1-9]|[12][0-9]|3[0-2])-" docs/project/plan/README.md docs/project/plan/*.md
rg "Implement plan step" docs/project/plan/*.md
```

Success criteria:

- No broken references to pre-remediation numbering.
- README and task docs are internally consistent with 001–032 flow.
- Dependency lists reflect remediation fixes.
