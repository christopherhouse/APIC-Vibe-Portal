# Contributing Guide

Thank you for contributing to the APIC Vibe Portal AI! This guide explains our development process, coding conventions, and pull request requirements.

## Getting Started

1. Read the [Local Development Guide](local-development.md) to set up your environment
2. Check the [Implementation Plan](../project/plan/README.md) for the current task status
3. Review the [Architecture Deep Dive](architecture-deep-dive.md) to understand the system

## Branching Strategy

We use **GitHub Flow**:

- `main` — production-ready code; protected branch
- `copilot/<task-number>-<description>` — AI-assisted feature branches
- `feature/<description>` — human-authored feature branches
- `fix/<description>` — bug fix branches
- `docs/<description>` — documentation-only changes

Always branch from `main`:

```bash
git checkout main
git pull
git checkout -b feature/my-new-feature
```

## Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:

```
feat(catalog): add lifecycle filter to catalog page
fix(chat): handle empty streamed response gracefully
docs(api): update BFF endpoint documentation
test(e2e): add admin journey E2E test
```

## Pull Request Requirements

Every pull request must:

1. **Pass all CI checks** — linting, type-checking, unit tests, E2E tests, build
2. **Include tests** — new features must have corresponding tests
3. **Follow coding conventions** — see below
4. **Update documentation** — if the change affects user-facing behaviour
5. **Use the PR template** — fill in all sections of `.github/PULL_REQUEST_TEMPLATE.md`
6. **Have a meaningful title** — using Conventional Commits format

## Coding Conventions

### TypeScript (Frontend + Shared)

- **Strict mode** — `tsconfig.json` has `"strict": true`; do not disable
- **No `any`** — use `unknown` or proper types instead
- **Named exports** — prefer named exports over default exports
- **Path aliases** — use `@/` for imports from `src/`: `import { Foo } from '@/components/Foo'`
- **React hooks** — use functional components and hooks only (no class components)
- **Async/await** — use `async/await` over `.then()` chains
- **File size** — keep files under 300 lines; extract components if needed

#### ESLint + Prettier

Run before committing:

```bash
npm run lint          # Check ESLint rules
npm run format:check  # Check Prettier formatting
npm run format        # Auto-fix formatting
```

The CI pipeline enforces both checks.

### Python (BFF)

- **Type hints** on all public functions and methods
- **Pydantic models** for all request/response schemas
- **`async def`** for all route handlers
- **Dependency injection** via `Depends()` for shared services
- **No bare `except`** — always catch specific exceptions
- **Snake case** for all identifiers

#### Ruff

Run before committing:

```bash
cd src/bff
uv run ruff check .           # Check lint rules
uv run ruff format --check .  # Check formatting
uv run ruff check --fix .     # Auto-fix lint issues
uv run ruff format .          # Auto-fix formatting
```

### General

- **Comments explain why, not what** — the code should be self-documenting
- **No magic numbers** — use named constants
- **Fail fast** — validate inputs early; don't let bad data propagate
- **Error messages are for humans** — error responses should be actionable

## Testing Requirements

| Change Type        | Required Tests                              |
| ------------------ | ------------------------------------------- |
| New UI component   | Unit test (RTL) + E2E test                  |
| New API endpoint   | BFF unit test                               |
| New user journey   | E2E journey test in `e2e/journeys/`         |
| Bug fix            | Test that reproduces the bug before the fix |
| Refactoring        | Existing tests must still pass              |
| Documentation only | No tests required                           |

## Code Review Process

1. Open a PR and request review from a teammate
2. Address all review comments (or leave a reply explaining why you disagree)
3. The reviewer approves once satisfied
4. Merge with **Squash and merge** to keep `main` history clean

## Living Documents

After completing a task from the implementation plan:

1. Update the task document (`docs/project/plan/NNN-task-name.md`):
   - Change status banner to ✅ Complete
   - Add Status History row
   - Record Technical Decisions and Deviations from Plan
   - Fill in Validation Results

2. Update `docs/project/plan/README.md`:
   - Change task status icon to ✅

See the [Implementation Plan README](../project/plan/README.md) for the full process.

## Security Requirements

- **Never commit secrets** — use environment variables or Azure Key Vault references
- **Validate all inputs** — use Pydantic models in BFF and Zod in frontend
- **No PII in logs** — mask user IDs and emails in log output
- **Dependency scanning** — run `npm audit` and Snyk before adding new packages
- **CORS** — do not add CORS middleware to the BFF; it is handled by Azure Container Apps

## Getting Help

- **GitHub Discussions** — for design questions and proposals
- **GitHub Issues** — for bug reports and feature requests
- **PR comments** — for code-level questions
- **Team Slack** — for real-time collaboration

## Related Documentation

- **[Local Development](local-development.md)**
- **[Testing Guide](testing-guide.md)**
- **[Architecture Deep Dive](architecture-deep-dive.md)**
