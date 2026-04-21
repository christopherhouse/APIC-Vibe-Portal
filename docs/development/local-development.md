# Local Development Guide

This guide explains how to set up and run the APIC Vibe Portal AI on your local machine for development.

## Prerequisites

| Tool      | Version    | Notes                                                               |
| --------- | ---------- | ------------------------------------------------------------------- | --- |
| Node.js   | >= 24      | See `.nvmrc`; use `nvm use`                                         |
| Python    | 3.14       | See `.python-version`; use `pyenv install`                          |
| UV        | Latest     | Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh` |
| npm       | >= 10      | Bundled with Node.js                                                |
| Git       | Any recent | For version control                                                 |
| Azure CLI | Latest     | Only needed for Azure-connected features                            |

Optional but recommended:

- **Docker** — for building and testing production containers locally
- **nvm** — for managing Node.js versions

## Initial Setup

### 1. Clone the repository

```bash
git clone https://github.com/christopherhouse/APIC-Vibe-Portal.git
cd APIC-Vibe-Portal
```

### 2. Use the correct Node.js version

```bash
nvm use   # reads .nvmrc automatically
```

### 3. Install frontend and shared dependencies

```bash
npm install
```

This installs dependencies for both `@apic-vibe-portal/frontend` and `@apic-vibe-portal/shared` workspaces.

### 4. Install BFF dependencies

```bash
cd src/bff
uv sync
cd ../..
```

### 5. Configure environment variables

```bash
cp .env.example .env.local
```

Edit `.env.local` and fill in at minimum:

```ini
# Required for authentication
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-app-registration-client-id>

# Frontend BFF URL (default for local dev)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Azure services (optional for frontend-only development)
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_KEY=<your-key>
COSMOS_DB_ENDPOINT=https://<your-cosmos>.documents.azure.com:443/
```

> **Tip**: If you only need to work on UI/frontend changes, the E2E tests use mock BFF responses, so you may not need real Azure credentials.

## Running the Application

### Frontend only (with mock BFF)

For frontend-only development with mocked API responses (no Azure needed):

```bash
npm run dev --workspace=@apic-vibe-portal/frontend
```

The app starts at `http://localhost:3000`. The E2E test mock server (`src/frontend/e2e/mock-server/`) can serve as a local BFF stand-in.

### Full stack (Frontend + BFF)

In one terminal, start the BFF:

```bash
cd src/bff
uv run fastapi dev
```

In another terminal, start the frontend:

```bash
npm run dev --workspace=@apic-vibe-portal/frontend
```

The BFF runs at `http://localhost:8000` and the frontend at `http://localhost:3000`.

## Development Workflow

### Making Frontend Changes

1. Edit files in `src/frontend/`
2. Next.js hot reload picks up changes automatically
3. Run unit tests: `npm run test --workspace=@apic-vibe-portal/frontend`
4. Run E2E tests: `npm run test:e2e --workspace=@apic-vibe-portal/frontend`

### Making BFF Changes

1. Edit files in `src/bff/`
2. FastAPI dev server hot reloads automatically
3. Run tests: `cd src/bff && uv run pytest`
4. Run linter: `cd src/bff && uv run ruff check . && uv run ruff format --check .`

### Making Shared Types Changes

1. Edit files in `src/shared/`
2. TypeScript types are available to both frontend and BFF (frontend imports from `@apic-vibe-portal/shared`)
3. Run type check: `npx tsc --noEmit`

## Running Quality Checks

Run all checks before pushing:

```bash
# Frontend + Shared
npm run lint         # ESLint
npm run format:check # Prettier
npx tsc --noEmit    # TypeScript
npm run test        # Jest
npm run build       # Next.js build

# BFF
cd src/bff
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Using the Mock BFF for E2E Tests

The Playwright E2E tests intercept all BFF API calls using `page.route()`. No running BFF is needed to run E2E tests.

```bash
# Run all E2E tests (starts Next.js dev server automatically)
npm run test:e2e --workspace=@apic-vibe-portal/frontend

# Run a specific test file
npx playwright test e2e/catalog.spec.ts --project=chromium

# Run with UI mode for debugging
npm run test:e2e:ui --workspace=@apic-vibe-portal/frontend
```

## Environment-Specific Configuration

The application reads runtime configuration from environment variables. For Next.js, variables prefixed with `NEXT_PUBLIC_` are available in the browser. All others are server-only.

| Variable prefix | Available in                                      |
| --------------- | ------------------------------------------------- |
| `NEXT_PUBLIC_*` | Frontend browser + server                         |
| Other vars      | Frontend server (Next.js API routes) and BFF only |

See `.env.example` for the complete list of variables.

## Debugging

### Frontend

Use the **Next.js DevTools** MCP server (configured in `.github/copilot/mcp.json`) for AI-assisted debugging. Alternatively:

1. Open Chrome DevTools (F12)
2. Use the **React DevTools** browser extension for component inspection
3. Check the **Network** tab for API call failures

### BFF

Enable debug logging in FastAPI:

```bash
cd src/bff
LOG_LEVEL=DEBUG uv run fastapi dev
```

Use VS Code with the Python extension and set a breakpoint in the router handler.

## Related Documentation

- **[Architecture Deep Dive](architecture-deep-dive.md)**
- **[Testing Guide](testing-guide.md)**
- **[Contributing](contributing.md)**
