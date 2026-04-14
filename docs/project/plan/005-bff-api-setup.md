# 005 - Phase 1 MVP: BFF API Project Setup

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Backend (BFF); BFF required for orchestration
- [Product Charter](../apic_product_charter.md) — AI-assisted workflows require server-side orchestration
- [Product Spec](../apic_portal_spec.md) — Backend feature requirements

## Overview
Scaffold the Backend-for-Frontend (BFF) API service using Python 3.14 and FastAPI, with UV managing the Python version and all dependencies. The BFF acts as the orchestration layer between the Next.js frontend and Azure services (API Center, AI Search, OpenAI, Foundry Agents).

## Dependencies
- **001** — Repository scaffolding (monorepo workspace structure)

## Implementation Details

### 1. Project Initialization
- Initialize a Python 3.14 project in `src/bff/` using UV (`uv init`)
- Use FastAPI as the HTTP framework
- Use UV to manage the Python version (3.14) and all dependencies — no pip

### 2. Project Structure
```
src/bff/
├── src/
│   └── bff/
│       ├── __init__.py
│       ├── main.py                 # Application entry point (Uvicorn startup)
│       ├── app.py                  # FastAPI app configuration
│       ├── config/
│       │   └── settings.py         # Environment-based configuration (Pydantic Settings)
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── health.py           # Health check endpoints
│       │   └── api_catalog.py      # Placeholder routes
│       ├── middleware/
│       │   ├── __init__.py
│       │   ├── error_handler.py    # Global error handling
│       │   ├── request_logger.py   # Request logging
│       │   ├── cors.py             # CORS configuration
│       │   └── auth.py             # Auth middleware placeholder
│       ├── services/               # Business logic layer
│       ├── clients/                # Azure SDK client wrappers
│       ├── models/
│       │   └── __init__.py         # Pydantic model definitions
│       └── utils/
│           └── logger.py           # Structured logging utility
├── tests/
│   ├── conftest.py                 # Test configuration and fixtures
│   ├── test_health.py              # Health endpoint tests
│   └── test_middleware.py          # Middleware tests
├── pyproject.toml                  # Project metadata, dependencies (UV-managed)
├── uv.lock                         # UV lockfile
└── .python-version                 # Pins Python 3.14
```

### 3. FastAPI App Configuration (`app.py`)
- JSON request parsing with size limits
- CORS configured for frontend origin (via FastAPI `CORSMiddleware`)
- Request logging middleware (structured JSON)
- Global exception handler middleware
- Health check endpoints (`/health`, `/health/ready`)

### 4. Configuration Management (`config/settings.py`)
- Environment-based configuration using Pydantic Settings (`pydantic-settings`)
- Typed settings model with required fields:
  - `PORT` (default 8000)
  - `FRONTEND_URL` (CORS origin)
  - `API_CENTER_ENDPOINT`
  - `AI_SEARCH_ENDPOINT`
  - `OPENAI_ENDPOINT`
  - `KEY_VAULT_URL`
  - `APPINSIGHTS_CONNECTION_STRING`
- Validation on startup (fail fast if required vars missing)

### 5. Middleware
- **Error Handler**: Catches unhandled errors, returns consistent JSON error responses, logs details
- **Request Logger**: Logs method, path, status, duration in structured JSON
- **CORS**: Configurable origins from settings
- **Auth Placeholder**: Passes through for now; will integrate Entra ID in task 016

### 6. Health Check Endpoints
- `GET /health` — Simple liveness check (returns 200)
- `GET /health/ready` — Readiness check that will validate Azure service connectivity (stubs for now)

### 7. Logging
- Use `structlog` for structured logging
- JSON format for production, pretty-print for development
- Correlation ID support via request header

### 8. Testing Setup
- Configure pytest with `httpx` / `HTTPX AsyncClient` for async endpoint testing
- Write tests for:
  - Health check endpoints
  - Error handler middleware
  - Request logger middleware
  - Configuration validation

### 9. Development Experience
- Uvicorn with `--reload` for auto-restart during development
- UV scripts in `pyproject.toml`: `dev`, `test`, `lint`, `format`
- `src/bff/.env.example` file (gitignored actual `.env`)
- All dependencies managed via `uv add` (no pip)

## Testing & Acceptance Criteria
- [ ] `uv run uvicorn bff.main:app --reload` starts the BFF on port 8000 without errors
- [ ] Python 3.14 is enforced via `.python-version` and UV
- [ ] `uv run pytest` passes all tests
- [ ] `uv run ruff check .` passes linting
- [ ] `GET /health` returns `200 OK` with `{ "status": "healthy" }`
- [ ] `GET /health/ready` returns `200 OK`
- [ ] Invalid JSON body returns `422` with structured error (FastAPI validation)
- [ ] Unhandled errors return `500` with structured error (no stack in production)
- [ ] All tests pass (health, middleware, config)
- [ ] CORS properly allows frontend origin and rejects others

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
**Task**: Implement plan step 005 — BFF API Project Setup.

Read the full task specification at `docs/project/plan/005-bff-api-setup.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Backend BFF, orchestration layer) and the repo structure from `docs/project/plan/001-sprint-zero-repo-scaffolding.md`.

Scaffold a Python 3.14 + FastAPI BFF API in `src/bff/` using UV for Python version and dependency management (no pip). Create the FastAPI app with middleware (CORS, error handling, request logging, auth placeholder), health check endpoints, environment-based configuration with Pydantic Settings validation, structured logging with structlog, and a comprehensive test suite using pytest + httpx.

Ensure the project uses UV for all dependency management (`uv add`, `uv sync`, `uv run`). Verify the dev server starts, linting passes (Ruff), and all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/005-bff-api-setup.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
