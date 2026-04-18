# Mock BFF Server

A lightweight mock server for Playwright e2e testing. It mimics the BFF API endpoints
so the frontend can be tested end-to-end without a running BFF or Azure services.

## Supported Endpoints

| Method | Path                                                 | Description                             |
| ------ | ---------------------------------------------------- | --------------------------------------- |
| GET    | `/api/catalog`                                       | List APIs (pagination, filtering)       |
| GET    | `/api/catalog/:apiId`                                | API detail                              |
| GET    | `/api/catalog/:apiId/versions`                       | API versions                            |
| GET    | `/api/catalog/:apiId/versions/:versionId/definition` | API spec                                |
| GET    | `/api/catalog/:apiId/deployments`                    | API deployments                         |
| GET    | `/api/environments`                                  | Environments list                       |
| POST   | `/api/search`                                        | Full-text search with facets/pagination |
| GET    | `/api/search/suggest`                                | Autocomplete prefix suggestions         |
| GET    | `/health`                                            | Health check                            |

## Usage

### In Playwright tests (recommended)

Tests primarily use Playwright's `page.route()` for request mocking. The mock server
data generators can also be imported directly:

```typescript
import { generateMockApis, generateMockSpec } from './mock-server';
```

### Standalone

```bash
MOCK_PORT=8000 npx tsx e2e/mock-server/index.ts
```

## Updating

As the BFF API evolves, update:

1. `MockApiDefinition` interface — to match new fields
2. `generateMockApis()` — to include new mock data
3. Route handlers — to add new endpoints
4. `generateMockSpec()` — to update the mock OpenAPI spec

## Standard Practice

**Screenshots should be captured for any UI changes.** When developing frontend features:

1. Start the dev server and mock API server
2. Use Playwright to navigate to affected pages
3. Capture screenshots to document UI state
4. Include screenshots in PR descriptions when relevant
