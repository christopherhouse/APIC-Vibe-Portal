# APIC Vibe Portal AI - GitHub Copilot Instructions

## Project Overview

This is an **AI-powered API portal** built on Azure services, designed to help developers discover, understand, and use APIs faster through multi-agent AI assistance.

## Architecture

- **Frontend**: Next.js 16 (App Router) + TypeScript 6.0 SPA
- **Backend-for-Frontend (BFF)**: Python 3.14 + FastAPI, managed with UV
- **AI Services**: Azure OpenAI, Foundry Agent Service (multi-agent orchestration)
- **Search**: Azure AI Search (hybrid search with semantic ranking)
- **API Catalog**: Azure API Center
- **Persistence**: Azure Cosmos DB (serverless) — chat sessions, governance snapshots, analytics
- **Observability**: Azure Application Insights
- **Deployment**: Azure Container Apps via Azure Container Registry
- **Security**: Entra ID authentication, RBAC, security trimming

## Tech Stack Details

### Frontend (Next.js)

- **Version**: Next.js 16 with App Router
- **Language**: TypeScript 6.0 in strict mode
- **UI Framework**: React 19 with functional components and hooks
- **Component Library**: Material UI (MUI) — pre-built React components, theming, and design system
- **Styling**: Material UI (MUI) theme + Emotion (MUI's default styling engine)
- **Testing**: Jest + React Testing Library, Playwright for E2E
- **Linting**: ESLint 9.x (flat config) + Prettier
- **Node Version**: >= 24 (see `.nvmrc`)

### Backend-for-Frontend (BFF)

- **Language**: Python 3.14 (see `.python-version`)
- **Framework**: FastAPI
- **Package Manager**: UV (not pip)
- **Azure SDK**: Azure SDK for Python
- **Testing**: pytest
- **Linting/Formatting**: Ruff
- **Middleware**: Authentication, logging, request validation (CORS handled by Azure Container Apps)

### Shared

- **Purpose**: Shared TypeScript types, utilities (frontend-only)
- **Language**: TypeScript 6.0
- **Workspace**: npm workspace alongside frontend

## Coding Conventions

### TypeScript (Frontend + Shared)

- Use **TypeScript 6.0** strict mode
- Prefer **functional React components** with hooks
- Use **async/await** over promises
- Follow **ESLint + Prettier** rules (see `eslint.config.js`, `.prettierrc.json`)
- Export named exports over default exports where possible
- Use **Path aliases** for imports (e.g., `@/components`, `@/lib`)

### Python (BFF)

- Use **Python 3.14** features
- Follow **PEP 8** conventions (enforced by Ruff)
- Use **async/await** for async operations
- Type hints on all public functions and methods
- Use **UV** for dependency management, not pip
- Follow FastAPI best practices (routers, dependency injection, Pydantic models)

### General

- Keep files under 300 lines where possible
- Write self-documenting code; comments for "why," not "what"
- Use consistent naming: camelCase (TS/JS), snake_case (Python)
- Avoid magic numbers; use named constants
- Write unit tests for business logic

## Security Practices

- **Authentication**: Entra ID (Azure AD) for user authentication
- **Authorization**: RBAC with security trimming (filter results by user permissions)
- **Secrets**: Store in Azure Key Vault, never commit to source control
- **Input Validation**: Validate all user inputs (Pydantic models in BFF, Zod in frontend)
- **CORS**: Handled by Azure Container Apps (do NOT add CORS middleware to BFF)
- **Dependencies**: Regularly scan for vulnerabilities (Snyk integration)

## Testing Strategy

- **Frontend**: Jest + React Testing Library for unit/component tests, Playwright for E2E
- **BFF**: pytest for unit and integration tests
- **Coverage**: Aim for >80% coverage on business logic
- **E2E**: Playwright tests live in `src/frontend/e2e/` and run against the Next.js dev server. Every frontend task that adds or modifies user-facing pages or flows **must** include corresponding Playwright e2e tests. Run with `npm run test:e2e --workspace=@apic-vibe-portal/frontend`. CI runs e2e tests on every PR via the `e2e-frontend` job in `.github/workflows/ci.yml`.

## Available MCP Servers

GitHub Copilot and custom agents have access to the following Model Context Protocol (MCP) servers for enhanced context and tooling:

- **Microsoft Learn** — Azure SDK documentation, Azure service references, best practices
- **Context7** — Up-to-date library documentation and API references for popular frameworks
- **Next.js DevTools** — Next.js-specific development tooling, debugging, and guidance
- **Snyk** — Security scanning for vulnerabilities in dependencies and code

Leverage these MCP servers when you need current documentation, security insights, or framework-specific guidance.

## Deployment

- **Target**: Azure Container Apps (one for frontend, one for BFF)
- **Registry**: Azure Container Registry
- **IaC**: Bicep templates (see `infra/` directory)
  - **Note**: Azure Container Apps are deployed via bash script AFTER infrastructure is provisioned and containers are pushed to ACR (not via Bicep)
- **CI/CD**: GitHub Actions (see `.github/workflows/`)
- **Observability**: All Azure resources must have diagnostic settings configured to send logs to Log Analytics workspace

## Local Development Setup

1. **Clone** the repository
2. **Install Node.js** >= 24 (see `.nvmrc`)
3. **Install Python** 3.14 (see `.python-version`)
4. **Install dependencies**:
   - Root: `npm install` (installs frontend + shared)
   - BFF: `cd src/bff && uv sync`
5. **Run dev servers**:
   - Frontend: `npm run dev --workspace=@apic-vibe-portal/frontend`
   - BFF: `cd src/bff && uv run fastapi dev` (or similar, TBD in Task 006)

## Agent Development Workflow

**This is the MANDATORY workflow for all coding agents. Do NOT commit or push code without completing all applicable quality checks.**

When you receive a task that involves code changes, follow these steps **in order**:

### 1. Understand the Task
- Read the task requirements thoroughly
- Identify which parts of the codebase are affected (frontend, shared, BFF, infra)
- Review relevant existing code, tests, and documentation

### 2. Plan the Execution
- Outline the minimal set of changes needed
- Identify which tests need to be added or updated
- Report your plan before writing any code

### 3. Implement Changes Iteratively
- Make small, incremental changes
- Add or update tests alongside the code changes — do not defer testing
- Report progress after each meaningful unit of work

### 4. Run ALL Quality Checks (MANDATORY before committing)

Run every applicable quality check below and **iterate until all pass**. Do not skip checks or commit with known failures.

#### Frontend + Shared (TypeScript)
```bash
# Lint (ESLint + Prettier)
npm run lint
npm run format:check

# Type check
npx tsc --noEmit

# Unit tests
npm run test

# Build
npm run build

# E2E tests (when UI changes are involved)
npm run test:e2e --workspace=@apic-vibe-portal/frontend
```

#### BFF (Python)
```bash
# Lint + format check (Ruff)
cd src/bff && uv run ruff check .
cd src/bff && uv run ruff format --check .

# Unit tests
cd src/bff && uv run pytest

# Compile check
cd src/bff && uv run python -m compileall .
```

#### Docker (when Dockerfiles or dependencies change)
```bash
docker build -t frontend-check src/frontend
docker build -t bff-check src/bff
```

### 5. Commit Only After All Checks Pass
- Only commit and push once **all applicable quality checks pass**
- If a check fails, fix the issue and re-run the checks
- Never commit with the intent to "fix it later"

### Quality Check Quick Reference

| Area | Lint | Format | Types | Tests | Build |
|------|------|--------|-------|-------|-------|
| Frontend + Shared | `npm run lint` | `npm run format:check` | `npx tsc --noEmit` | `npm run test` | `npm run build` |
| BFF | `uv run ruff check .` | `uv run ruff format --check .` | N/A | `uv run pytest` | `uv run python -m compileall .` |
| Docker | N/A | N/A | N/A | N/A | `docker build` |

## Project References

- **Product Charter**: [docs/project/apic_product_charter.md](../docs/project/apic_product_charter.md)
- **Architecture**: [docs/project/apic_architecture.md](../docs/project/apic_architecture.md)
- **Product Spec**: [docs/project/apic_portal_spec.md](../docs/project/apic_portal_spec.md)
- **Implementation Plan**: [docs/project/plan/README.md](../docs/project/plan/README.md)

## Living Documentation Requirements

The implementation plan and all task documents are **living documents** that MUST be kept up-to-date as work progresses.

### When Working on Implementation Tasks

After completing any implementation task from the plan (tasks 001-032):

1. **Update the individual task document** (`docs/project/plan/NNN-task-name.md`, e.g. `docs/project/plan/001-sprint-zero-repo-scaffolding.md`):
   - Change the status banner at the top to reflect current state (🔄 In Progress or ✅ Complete)
   - Add rows to the Status History table with dates and notes
   - Record Technical Decisions made during implementation
   - Note any Deviations from Plan with rationale
   - Fill in Validation Results with test outcomes and metrics
   - Check off completed items in Testing & Acceptance Criteria

2. **Update the plan README** (`docs/project/plan/README.md`):
   - Update the status icon in the task index table (🔲 → 🔄 → ✅)
   - Keep the status synchronized with the individual task document

### Status Icons

- 🔲 Not Started
- 🔄 In Progress
- ✅ Complete
- ⚠️ Blocked (with notes in task document)

**This is NOT optional** — keeping these documents current ensures the entire team understands project status and decisions made along the way.

## Notes for Copilot

- When suggesting Azure SDK usage, prefer the latest Azure SDK for Python or JavaScript/TypeScript
- For Next.js 16, always use App Router conventions (app directory, Server Components by default, Client Components with "use client")
- For FastAPI, use modern Python 3.14 features (e.g., PEP 695 type syntax)
- Respect the monorepo structure: frontend and shared are npm workspaces; BFF is a separate UV-managed Python project
- When working on infrastructure, use Bicep (not ARM JSON or Terraform)
- **IMPORTANT**: Do NOT add CORS middleware to the BFF — Azure Container Apps handles CORS configuration
- **IMPORTANT**: All Azure resources must have diagnostic settings sending logs/metrics to Log Analytics
- **IMPORTANT**: Deploy Container Apps via bash script after infrastructure provisioning, NOT via Bicep templates
