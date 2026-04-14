# 005 - Phase 1 MVP: BFF API Project Setup

## References
- [Architecture Document](../apic_architecture.md) — Backend (BFF); BFF required for orchestration
- [Product Charter](../apic_product_charter.md) — AI-assisted workflows require server-side orchestration
- [Product Spec](../apic_portal_spec.md) — Backend feature requirements

## Overview
Scaffold the Backend-for-Frontend (BFF) API service using Node.js, Express, and TypeScript. The BFF acts as the orchestration layer between the Next.js frontend and Azure services (API Center, AI Search, OpenAI, Foundry Agents).

## Dependencies
- **001** — Repository scaffolding (monorepo workspace structure)

## Implementation Details

### 1. Project Initialization
- Initialize a Node.js + TypeScript project in `src/bff/`
- Use Express.js as the HTTP framework
- Integrate with the root npm workspace

### 2. Project Structure
```
src/bff/
├── src/
│   ├── index.ts                # Application entry point
│   ├── app.ts                  # Express app configuration
│   ├── config/
│   │   └── settings.ts         # Environment-based configuration
│   ├── routes/
│   │   ├── index.ts            # Route registration
│   │   ├── health.routes.ts    # Health check endpoints
│   │   └── api-catalog.routes.ts  # Placeholder routes
│   ├── middleware/
│   │   ├── error-handler.ts    # Global error handling
│   │   ├── request-logger.ts   # Request logging
│   │   ├── cors.ts             # CORS configuration
│   │   └── auth.ts             # Auth middleware placeholder
│   ├── services/               # Business logic layer
│   ├── clients/                # Azure SDK client wrappers
│   ├── types/
│   │   └── index.ts            # Shared type definitions
│   └── utils/
│       └── logger.ts           # Structured logging utility
├── __tests__/
│   ├── setup.ts                # Test configuration
│   ├── routes/                 # Route tests
│   └── middleware/             # Middleware tests
├── tsconfig.json               # Extends root tsconfig.base.json
├── jest.config.ts
├── package.json
└── nodemon.json                # Dev server config
```

### 3. Express App Configuration (`app.ts`)
- JSON body parsing with size limits
- CORS configured for frontend origin
- Request logging middleware (structured JSON)
- Global error handling middleware
- Health check endpoints (`/health`, `/health/ready`)

### 4. Configuration Management (`config/settings.ts`)
- Environment-based configuration using `dotenv`
- Typed settings object with required fields:
  - `PORT` (default 3001)
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
- **Auth Placeholder**: Passes through for now; will integrate Entra ID in task 015

### 6. Health Check Endpoints
- `GET /health` — Simple liveness check (returns 200)
- `GET /health/ready` — Readiness check that will validate Azure service connectivity (stubs for now)

### 7. Logging
- Use a structured logger (e.g., `pino` or `winston`)
- JSON format for production, pretty-print for development
- Correlation ID support via request header

### 8. Testing Setup
- Configure Jest with TypeScript support
- Add supertest for HTTP endpoint testing
- Write tests for:
  - Health check endpoints
  - Error handler middleware
  - Request logger middleware
  - Configuration validation

### 9. Development Experience
- `nodemon` for auto-restart during development
- NPM scripts: `dev`, `build`, `start`, `test`, `lint`
- `src/bff/dev.env` example file (gitignored actual `.env`)

## Testing & Acceptance Criteria
- [ ] `npm run dev` starts the BFF on port 3001 without errors
- [ ] `npm run build` compiles TypeScript without errors
- [ ] `npm run lint` passes
- [ ] `GET /health` returns `200 OK` with `{ "status": "healthy" }`
- [ ] `GET /health/ready` returns `200 OK`
- [ ] Invalid JSON body returns `400` with structured error
- [ ] Unhandled errors return `500` with structured error (no stack in production)
- [ ] All tests pass (health, middleware, config)
- [ ] CORS properly allows frontend origin and rejects others

## Coding Agent Prompt

> **Task**: Implement plan step 005 — BFF API Project Setup.
>
> Read the full task specification at `docs/project/plan/005-bff-api-setup.md`.
>
> Reference the architecture at `docs/project/apic_architecture.md` (Backend BFF, orchestration layer) and the repo structure from `docs/project/plan/001-sprint-zero-repo-scaffolding.md`.
>
> Scaffold a Node.js + Express + TypeScript BFF API in `src/bff/`. Create the Express app with middleware (CORS, error handling, request logging, auth placeholder), health check endpoints, environment-based configuration with validation, structured logging, and a comprehensive test suite using Jest + supertest.
>
> Ensure the project integrates with the root npm workspace. Verify the dev server starts, the build succeeds, linting passes, and all tests pass.
