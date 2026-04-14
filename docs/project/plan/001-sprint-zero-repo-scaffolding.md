# 001 - Sprint Zero: Repository Scaffolding & GitHub Copilot Assets

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Product Charter](../apic_product_charter.md) — Project scope, goals, and phased timeline
- [Architecture Document](../apic_architecture.md) — Component overview: Next.js SPA, BFF, Agent Layer, Search Layer, Observability
- [Product Spec](../apic_portal_spec.md) — Feature requirements

## Overview
Bootstrap the repository with a monorepo structure, developer tooling, and GitHub Copilot assets. This is the foundation every subsequent task builds upon.

## Implementation Details

### 1. Monorepo Structure
Create the following top-level directory layout:
```
/
├── src/
│   ├── frontend/          # Next.js SPA
│   ├── bff/               # Backend-for-Frontend API
│   └── shared/            # Shared types, utilities
├── infra/                 # Bicep IaC templates
├── .github/
│   ├── workflows/         # CI/CD pipelines
│   ├── copilot-instructions.md
│   ├── agents/            # Custom Copilot agents
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   └── project/           # Existing project docs
├── scripts/               # Developer helper scripts
├── .editorconfig
├── .gitignore
├── .nvmrc                 # Pin Node.js version (20 LTS)
├── package.json           # Root workspace package.json
└── README.md
```

### 2. Root Workspace Configuration
- Initialize a root `package.json` with npm workspaces pointing to `src/frontend`, `src/bff`, and `src/shared`.
- Add a `.nvmrc` file pinning Node.js 20 LTS.
- Add an `.editorconfig` for consistent formatting (2-space indent, UTF-8, LF line endings).
- Add a comprehensive `.gitignore` for Node.js, Next.js, and Azure artifacts.

### 3. GitHub Copilot Assets

#### Copilot Instructions (`.github/copilot-instructions.md`)
Create instructions that describe:
- The project is an AI-powered API portal built on Azure services
- Tech stack: Next.js 14+ (App Router), TypeScript, Node.js BFF, Azure API Center, Azure AI Search, Azure OpenAI, Foundry Agent Service
- Coding conventions: TypeScript strict mode, ESLint + Prettier, functional React components with hooks
- Architecture: Frontend ↔ BFF ↔ Azure services (API Center, AI Search, Foundry Agents)
- Security: Entra ID authentication, RBAC, security trimming
- Testing: Jest + React Testing Library for frontend, Jest/Vitest for BFF, Playwright for E2E
- Deployment target: Azure Container Apps via ACR

#### Custom Copilot Agents (`.github/agents/`)
Create agent definitions for:
- **api-portal-architect**: Understands the architecture doc, helps with design decisions, component interactions
- **azure-infra-agent**: Specializes in Bicep templates, Azure resource configuration, deployment
- **frontend-agent**: Next.js, React, TypeScript UI development, accessibility
- **bff-agent**: BFF API design, Azure SDK integration, middleware patterns

### 4. Developer Tooling
- Add ESLint and Prettier configuration at the root level (shared across workspaces).
- Add TypeScript base configuration (`tsconfig.base.json`) that workspaces extend.
- Add a root `Makefile` or npm scripts for common operations: `lint`, `test`, `build`, `dev`.

### 5. PR Template
Create `.github/PULL_REQUEST_TEMPLATE.md` with sections for:
- Summary of changes
- Related task/plan step reference
- Testing performed
- Checklist (tests pass, lint clean, docs updated)

### 6. README
Update the root `README.md` with:
- Project name and description
- Architecture overview (reference architecture doc)
- Getting started / prerequisites
- Development workflow
- Link to plan docs

## Testing & Acceptance Criteria
- [ ] Repository clones cleanly and `npm install` succeeds at the root
- [ ] Workspace structure resolves correctly (`npm ls` shows frontend, bff, shared)
- [ ] `.github/copilot-instructions.md` exists and is well-formed
- [ ] Custom agent definitions exist under `.github/agents/`
- [ ] ESLint, Prettier, and TypeScript configurations exist and are valid
- [ ] `.gitignore` properly excludes `node_modules`, build artifacts, `.env` files
- [ ] `README.md` contains accurate project overview and links

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

> **Task**: Implement plan step 001 — Sprint Zero: Repository Scaffolding & GitHub Copilot Assets.
>
> Read the full task specification at `docs/project/plan/001-sprint-zero-repo-scaffolding.md`.
>
> You are bootstrapping a new monorepo for the APIC Vibe Portal AI project. Reference the architecture at `docs/project/apic_architecture.md` and the charter at `docs/project/apic_product_charter.md` for context on the tech stack and project goals.
>
> Create the monorepo directory structure, root workspace configuration (npm workspaces, .nvmrc, .editorconfig, .gitignore), GitHub Copilot instructions and custom agent definitions, shared ESLint/Prettier/TypeScript configs, a PR template, and update the root README.
>
> Do NOT scaffold the Next.js or BFF projects themselves — that is handled in later tasks. Just create the directory structure, placeholder package.json files for each workspace, and all the developer tooling described in the plan.
>
> Verify that `npm install` succeeds at the root and the workspace structure is correct.
>
> **Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/001-sprint-zero-repo-scaffolding.md`):
> 1. Change the status banner at the top to `> **✅ Status: Complete**`
> 2. Add a row to the Status History table with the completion date and a summary
> 3. Record any technical decisions made under "Technical Decisions"
> 4. Note any deviations from the plan under "Deviations from Plan"
> 5. Record test/validation results under "Validation Results"
