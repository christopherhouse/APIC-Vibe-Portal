# 001 - Sprint Zero: Repository Scaffolding & GitHub Copilot Assets

> **✅ Status: Complete**
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
│   │   └── mcp.json       # MCP server configuration (Microsoft Learn, Context7, Next.js DevTools, Snyk)
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
- **Snyk** — Security scanning for vulnerabilities in dependencies and code

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
- [ ] MCP servers (Microsoft Learn, Context7, Next.js DevTools, Snyk) are documented in copilot instructions and/or agent definitions
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
| 2026-04-14 | ✅ Complete | Claude Code Agent | Successfully scaffolded monorepo structure, tooling, and GitHub Copilot assets |

### Technical Decisions

1. **UV Dependency Management**: Updated `pyproject.toml` to use `[dependency-groups]` instead of the deprecated `[tool.uv]` section for dev dependencies, following UV 0.11+ conventions.

2. **TypeScript 6.0**: Configured strict TypeScript 6.0 with modern compiler options (ESNext module resolution, bundler mode) for frontend and shared workspaces.

3. **ESLint Flat Config**: Used ESLint 9.x flat config format (`eslint.config.js`) instead of legacy `.eslintrc` for improved configuration and plugin management.

4. **MCP Server Configuration**: Documented four MCP servers (Microsoft Learn, Context7, Next.js DevTools, Snyk) in both `.github/copilot/mcp.json` and copilot instructions for discoverability.

5. **Minimal BFF Package**: Created a minimal `apic_vibe_portal_bff` Python package with `__init__.py` to satisfy Hatchling build requirements. Full BFF implementation is deferred to Task 006.

### Deviations from Plan

**None**. All requirements from the plan were implemented as specified. The only additions were:
- Created minimal `apic_vibe_portal_bff/__init__.py` package to satisfy UV/Hatchling build requirements (not explicitly mentioned in plan but necessary for `uv sync` to succeed)

### Validation Results

✅ **All acceptance criteria passed:**

1. ✅ Repository clones cleanly and `npm install` succeeds at the root (frontend + shared)
   - Installed 239 packages successfully with 0 vulnerabilities

2. ✅ Workspace structure resolves correctly (`npm ls` shows frontend and shared)
   - Both `@apic-vibe-portal/frontend` and `@apic-vibe-portal/shared` workspaces are correctly linked

3. ✅ BFF Python project initializes correctly with `uv sync` in `src/bff/`
   - UV successfully installed Python 3.14.4
   - Created virtual environment at `.venv`
   - Installed 2 packages: `apic-vibe-portal-bff` and `ruff`

4. ✅ `.github/copilot-instructions.md` exists and is well-formed
   - Comprehensive instructions covering tech stack, conventions, architecture, security, testing, and MCP servers

5. ✅ Custom agent definitions exist under `.github/agents/`
   - Created 5 agent definitions: `api-portal-architect`, `azure-infra-agent`, `frontend-agent`, `bff-agent`, `tech-writer-agent`

6. ✅ MCP servers documented
   - Documented in `.github/copilot/mcp.json`
   - Referenced in `.github/copilot-instructions.md`
   - Referenced in individual agent definition files

7. ✅ ESLint, Prettier, and TypeScript configurations exist and are valid
   - `eslint.config.js` (ESLint 9.x flat config)
   - `.prettierrc.json`
   - `tsconfig.base.json` (TypeScript 6.0)

8. ✅ Ruff configuration exists and is valid (BFF Python)
   - Configured in `src/bff/pyproject.toml` with appropriate linting rules

9. ✅ `.gitignore` properly excludes artifacts
   - Excludes `node_modules`, `__pycache__`, `.venv`, build artifacts, `.env` files, and more

10. ✅ `README.md` contains accurate project overview and links
    - Includes architecture diagram (Mermaid), getting started instructions, tech stack, and documentation links


## Coding Agent Prompt

```text
**Task**: Implement plan step 001 — Sprint Zero: Repository Scaffolding & GitHub Copilot Assets.

Read the full task specification at `docs/project/plan/001-sprint-zero-repo-scaffolding.md`.

You are bootstrapping a new monorepo for the APIC Vibe Portal AI project. Reference the architecture at `docs/project/apic_architecture.md` and the charter at `docs/project/apic_product_charter.md` for context on the tech stack and project goals.

Create the monorepo directory structure, root workspace configuration (npm workspaces for frontend and shared, UV-managed Python project for BFF, .nvmrc pinning Node.js >=24, .python-version pinning Python 3.14, .editorconfig, .gitignore), GitHub Copilot instructions and custom agent definitions (including tech-writer-agent), shared ESLint/Prettier/TypeScript 6.0 configs for frontend/shared, Ruff config for BFF Python, a PR template, and update the root README. Document the available MCP servers (Microsoft Learn, Context7, Next.js DevTools, Snyk) in copilot instructions and/or agent definitions.

Do NOT scaffold the Next.js or BFF projects themselves — that is handled in later tasks. Just create the directory structure, placeholder package.json files for frontend and shared workspaces, a placeholder pyproject.toml for the BFF (managed with UV, targeting Python 3.14), and all the developer tooling described in the plan.

Verify that `npm install` succeeds at the root (frontend + shared workspaces) and `uv sync` succeeds in `src/bff/`. Verify the workspace structure is correct.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/001-sprint-zero-repo-scaffolding.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
