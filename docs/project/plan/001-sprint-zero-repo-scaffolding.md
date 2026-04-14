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
│   ├── bff/               # Backend-for-Frontend API (Python 3.14 / FastAPI / UV)
│   └── shared/            # Shared types, utilities (TypeScript — frontend only)
├── infra/                 # Bicep IaC templates
├── .github/
│   ├── workflows/         # CI/CD pipelines
│   ├── copilot-instructions.md
│   ├── agents/            # Custom Copilot agents
│   ├── copilot/
│   │   └── mcp.json       # MCP server configuration (Microsoft Learn, Context7, Next.js DevTools)
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   └── project/           # Existing project docs
├── scripts/               # Developer helper scripts
├── .editorconfig
├── .gitignore
├── .nvmrc                 # Pin Node.js version (>=24)
├── package.json           # Root workspace package.json
└── README.md
```

### 2. Root Workspace Configuration
- Initialize a root `package.json` with npm workspaces pointing to `src/frontend` and `src/shared` (the BFF is a Python project managed by UV, not part of the npm workspace).
- Add a `.nvmrc` file pinning Node.js >=24 (for the frontend and shared packages).
- Add a `.python-version` file pinning Python 3.14 (for the BFF, managed via UV).
- Add an `.editorconfig` for consistent formatting (2-space indent for JS/TS, 4-space indent for Python, UTF-8, LF line endings).
- Add a comprehensive `.gitignore` for Node.js, Next.js, Python, and Azure artifacts.

### 3. GitHub Copilot Assets

#### Copilot Instructions (`.github/copilot-instructions.md`)
Create instructions that describe:
- The project is an AI-powered API portal built on Azure services
- Tech stack: Next.js 16 (App Router), TypeScript 6.0 (frontend), Python 3.14 + FastAPI BFF (managed with UV), Azure API Center, Azure AI Search, Azure OpenAI, Foundry Agent Service
- Coding conventions: TypeScript 6.0 strict mode, ESLint + Prettier, functional React components with hooks
- Architecture: Frontend ↔ BFF ↔ Azure services (API Center, AI Search, Foundry Agents)
- Security: Entra ID authentication, RBAC, security trimming
- Testing: Jest + React Testing Library for frontend, pytest for BFF, Playwright for E2E
- Deployment target: Azure Container Apps via ACR

#### Custom Copilot Agents (`.github/agents/`)
Create agent definitions for:
- **api-portal-architect**: Understands the architecture doc, helps with design decisions, component interactions
- **azure-infra-agent**: Specializes in Bicep templates, Azure resource configuration, deployment
- **frontend-agent**: Next.js, React, TypeScript UI development, accessibility
- **bff-agent**: Python 3.14 / FastAPI BFF API design, Azure SDK for Python integration, middleware patterns, UV dependency management
- **tech-writer-agent**: Writes engaging, well-organized documentation with emojis for flair, generates SVG images and diagrams, uses Mermaid for architecture/flow diagrams, and ensures all docs are visually appealing and developer-friendly

#### MCP Servers
Document the available MCP (Model Context Protocol) servers in copilot instructions and agent definitions so that Copilot and agents can leverage external context:
- **Microsoft Learn** — Azure SDK docs, Azure service references, best practices
- **Context7** — Up-to-date library documentation and API references
- **Next.js DevTools** — Next.js-specific development tooling and guidance

### 4. Developer Tooling
- Add ESLint and Prettier configuration at the root level (shared across frontend/shared TypeScript workspaces).
- Add TypeScript 6.0 base configuration (`tsconfig.base.json`) that frontend and shared workspaces extend.
- Add Ruff configuration for BFF Python linting and formatting.
- Add a root `Makefile` or npm scripts for common operations: `lint`, `test`, `build`, `dev`.
- Use UV for all Python dependency management in the BFF (no pip).

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
- [ ] Repository clones cleanly and `npm install` succeeds at the root (frontend + shared)
- [ ] Workspace structure resolves correctly (`npm ls` shows frontend and shared)
- [ ] BFF Python project initializes correctly with `uv sync` in `src/bff/`
- [ ] `.github/copilot-instructions.md` exists and is well-formed
- [ ] Custom agent definitions exist under `.github/agents/`
- [ ] MCP servers (Microsoft Learn, Context7, Next.js DevTools) are documented in copilot instructions and/or agent definitions
- [ ] ESLint, Prettier, and TypeScript configurations exist and are valid (frontend/shared)
- [ ] Ruff configuration exists and is valid (BFF Python)
- [ ] `.gitignore` properly excludes `node_modules`, `__pycache__`, `.venv`, build artifacts, `.env` files
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

```text
**Task**: Implement plan step 001 — Sprint Zero: Repository Scaffolding & GitHub Copilot Assets.

Read the full task specification at `docs/project/plan/001-sprint-zero-repo-scaffolding.md`.

You are bootstrapping a new monorepo for the APIC Vibe Portal AI project. Reference the architecture at `docs/project/apic_architecture.md` and the charter at `docs/project/apic_product_charter.md` for context on the tech stack and project goals.

Create the monorepo directory structure, root workspace configuration (npm workspaces for frontend and shared, UV-managed Python project for BFF, .nvmrc pinning Node.js >=24, .python-version pinning Python 3.14, .editorconfig, .gitignore), GitHub Copilot instructions and custom agent definitions (including tech-writer-agent), shared ESLint/Prettier/TypeScript 6.0 configs for frontend/shared, Ruff config for BFF Python, a PR template, and update the root README. Document the available MCP servers (Microsoft Learn, Context7, Next.js DevTools) in copilot instructions and/or agent definitions.

Do NOT scaffold the Next.js or BFF projects themselves — that is handled in later tasks. Just create the directory structure, placeholder package.json files for frontend and shared workspaces, a placeholder pyproject.toml for the BFF (managed with UV, targeting Python 3.14), and all the developer tooling described in the plan.

Verify that `npm install` succeeds at the root (frontend + shared workspaces) and `uv sync` succeeds in `src/bff/`. Verify the workspace structure is correct.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/001-sprint-zero-repo-scaffolding.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
