# Contributing

## Branch Strategy

| Branch                                      | Purpose                                            |
| ------------------------------------------- | -------------------------------------------------- |
| `main`                                      | Production-ready code; triggers auto-deploy to dev |
| `feature/<task-number>-<short-description>` | Feature branches for implementation tasks          |
| `fix/<short-description>`                   | Bug fix branches                                   |
| `chore/<short-description>`                 | Non-functional changes (deps, config, docs)        |

Create branches from `main`. Open PRs back to `main`.

## Workflow

1. Check the [[Implementation Plan]] for available tasks
2. Create a branch: `git checkout -b feature/024-api-comparison`
3. Make changes following the coding conventions below
4. Run all quality checks (see below) — **do not skip**
5. Create a PR using the PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
6. Address review feedback
7. Merge after CI passes and approval is received

## Coding Conventions

### TypeScript (Frontend + Shared)

- **TypeScript 6.0 strict mode** — no `any`, no `ts-ignore` without a comment
- **Functional React components** with hooks — no class components
- **Named exports** preferred over default exports
- **Path aliases**: use `@/components`, `@/lib`, etc. (configured in `tsconfig.json`)
- **async/await** over raw Promises
- **ESLint + Prettier** enforced — run `npm run lint` and `npm run format:check`
- Files under 300 lines where possible

### Python (BFF)

- **Python 3.14** — use modern features (PEP 695 type syntax, etc.)
- **Type hints** on all public functions and methods
- **async/await** for all I/O operations
- **Pydantic models** for request/response validation
- **Ruff** for linting and formatting — run `uv run ruff check .`
- **FastAPI patterns**: use routers, dependency injection, Pydantic models
- Snake_case for all identifiers
- Files under 300 lines where possible

### General

- Comments explain **why**, not **what**
- Named constants over magic numbers
- Tests for all business logic (target >80% coverage)
- Never commit secrets or credentials

## Quality Gates (Mandatory Before Committing)

Run **every applicable check** and iterate until all pass.

### Frontend + Shared

```bash
npm run lint            # ESLint + Prettier check
npm run format:check    # Prettier format check
npx tsc --noEmit        # TypeScript type check
npm run test            # Jest unit tests
npm run build           # Production build
# For UI changes:
npm run test:e2e --workspace=@apic-vibe-portal/frontend
```

### BFF

```bash
cd src/bff
uv run ruff check .                  # Lint
uv run ruff format --check .         # Format check
uv run pytest                        # Unit tests
uv run python -m compileall .        # Compile check
```

### Docker (when Dockerfiles change)

```bash
docker build -t frontend-check src/frontend
docker build -t bff-check src/bff
```

## Custom Copilot Agents

The repository includes GitHub Copilot coding agents for specialized tasks:

| Agent                  | Specialization                      |
| ---------------------- | ----------------------------------- |
| `api-portal-architect` | Architecture and design decisions   |
| `azure-infra-agent`    | Bicep templates and Azure resources |
| `frontend-agent`       | Next.js and React development       |
| `bff-agent`            | FastAPI and Azure SDK integration   |
| `tech-writer-agent`    | Documentation writing               |

Use these agents via GitHub Copilot when working in their respective domains.

## PR Template

Every PR should reference the implementation task it addresses and fill in all sections of `.github/PULL_REQUEST_TEMPLATE.md`.

## Updating Task Documents

When working on an implementation task:

1. Update the task document at `docs/project/plan/NNN-task-name.md`:
   - Change the status banner (`🔄 In Progress` or `✅ Complete`)
   - Add rows to the Status History table
   - Record Technical Decisions
   - Note any Deviations from Plan
   - Fill in Validation Results

2. Update `docs/project/plan/README.md`:
   - Update the status icon in the task index table

**This is required, not optional.**

## Related

- [[Implementation Plan]] — Current task status and dependencies
- [[Architecture]] — System design to understand before making changes
- [[Getting Started]] — Local setup
