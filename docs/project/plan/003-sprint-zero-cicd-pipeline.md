# 003 - Sprint Zero: CI/CD Pipeline with GitHub Actions

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Deployment: Azure Container Apps, ACR
- [Product Charter](../apic_product_charter.md) — Rapid iteration and phased delivery
- [Product Spec](../apic_portal_spec.md) — Continuous deployment requirements

## Overview
Set up GitHub Actions workflows for continuous integration and continuous deployment. This enables every subsequent task to be rapidly built, tested, and deployed to Azure.

## Dependencies
- **001** — Repository scaffolding (workspace structure, tooling)
- **002** — Bicep templates (infrastructure deployment)

## Implementation Details

### 1. Workflow Files
```
/.github/workflows/
├── ci.yml                  # Lint, test, build on PRs
├── deploy-infra.yml        # Deploy Bicep templates
├── deploy-app.yml          # Build & deploy container images
└── pr-checks.yml           # PR quality gates
```

### 2. CI Workflow (`ci.yml`)
Triggers: `push` to `main`, `pull_request` to `main`

Jobs:
1. **lint** — Run ESLint across all workspaces
2. **test-frontend** — Run frontend unit tests (Jest + RTL)
3. **test-bff** — Run BFF unit tests
4. **build-frontend** — Build Next.js app
5. **build-bff** — Build BFF service
6. **typecheck** — Run TypeScript compiler in `--noEmit` mode across workspaces

Use npm workspace commands and matrix strategy where appropriate.

### 3. Infrastructure Deployment (`deploy-infra.yml`)
Triggers: `push` to `main` (changes in `/infra/**`), `workflow_dispatch`

Jobs:
1. **validate** — `az bicep build` and `az deployment group validate`
2. **deploy-dev** — Deploy to dev environment
3. **deploy-staging** — Deploy to staging (requires approval)
4. **deploy-prod** — Deploy to prod (requires approval)

Use GitHub environments for approval gates. Authenticate with Azure using OIDC (federated credentials, no secrets).

### 4. Application Deployment (`deploy-app.yml`)
Triggers: `push` to `main` (changes in `/src/**`), `workflow_dispatch`

Jobs:
1. **build-and-push-frontend** — Build Docker image for frontend, push to ACR
2. **build-and-push-bff** — Build Docker image for BFF, push to ACR
3. **deploy-dev** — Update Container Apps with new images
4. **deploy-staging** — Deploy to staging (requires approval)
5. **deploy-prod** — Deploy to prod (requires approval)

### 5. PR Quality Gates (`pr-checks.yml`)
Triggers: `pull_request`

Jobs:
1. **labeler** — Auto-label PRs based on changed paths
2. **size-check** — Warn on large PRs
3. **plan-reference** — Check PR description references a plan step

### 6. Dockerfiles
Create Dockerfiles for the frontend and BFF:
```
/src/frontend/Dockerfile
/src/bff/Dockerfile
```
- Multi-stage builds (build stage + production stage)
- Use `node:24-alpine` as base
- Non-root user for production stage
- Health check endpoints

### 7. GitHub Actions Configuration
- Define reusable composite actions where patterns repeat
- Use GitHub environments: `dev`, `staging`, `prod`
- Store Azure credentials as OIDC federated identity (document setup steps)
- Use `azure/login@v2` with OIDC

## Testing & Acceptance Criteria
- [ ] CI workflow runs successfully on a PR with lint, test, and build jobs
- [ ] CI workflow properly fails when lint errors or test failures exist
- [ ] Infrastructure deployment workflow validates Bicep templates
- [ ] Application deployment workflow builds Docker images
- [ ] Dockerfiles build successfully with `docker build`
- [ ] Workflows use OIDC authentication (no stored secrets for Azure login)
- [ ] GitHub environments are documented in README
- [ ] All workflow files pass `actionlint` validation

## Implementation Notes
<!-- 
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History
| Date | Status | Author | Notes |
|------|--------|--------|-------|
| — | 🔲 Not Started | — | Task created |

### Technical Decisions
_No technical decisions recorded yet._

### Deviations from Plan
_No deviations from the original plan._

### Validation Results
_No validation results yet._


## Coding Agent Prompt

```text
**Task**: Implement plan step 003 — CI/CD Pipeline with GitHub Actions.

Read the full task specification at `docs/project/plan/003-sprint-zero-cicd-pipeline.md`.

Reference the architecture at `docs/project/apic_architecture.md` for deployment targets (Container Apps, ACR) and `docs/project/plan/002-sprint-zero-azure-infra-bicep.md` for the infrastructure outputs the pipeline will use.

Create GitHub Actions workflow files under `.github/workflows/` for CI (lint, test, build), infrastructure deployment (Bicep), application deployment (Docker build + Container Apps), and PR quality gates. Create multi-stage Dockerfiles for the frontend and BFF services.

Ensure workflows use OIDC-based Azure authentication and GitHub environments for approval gates. Validate workflow YAML is syntactically correct. Do NOT configure actual Azure credentials or trigger deployments.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/003-sprint-zero-cicd-pipeline.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
