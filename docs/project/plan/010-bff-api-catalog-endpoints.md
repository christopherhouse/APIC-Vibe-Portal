# 010 - Phase 1 MVP: BFF API Catalog Endpoints

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — BFF required for orchestration between frontend and Azure services
- [Product Charter](../apic_product_charter.md) — Improve API discovery
- [Product Spec](../apic_portal_spec.md) — API catalog browsing requirements

## Overview

Implement the REST API endpoints in the BFF that expose API catalog data to the frontend. These endpoints serve as the contract between the Next.js frontend and the Azure API Center data layer.

## Dependencies

- **006** — BFF API project setup (FastAPI app, routing)
- **007** — Shared types package (DTOs)
- **009** — API Center data layer (service and client)

## Implementation Details

### 1. Route Definitions

```
src/bff/src/bff/routers/
├── api_catalog.py              # API catalog endpoints
├── test_api_catalog.py
```

Endpoints:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/catalog` | List APIs with pagination & filtering |
| `GET` | `/api/catalog/:apiId` | Get API details |
| `GET` | `/api/catalog/:apiId/versions` | List API versions |
| `GET` | `/api/catalog/:apiId/versions/:versionId/definition` | Get API spec |
| `GET` | `/api/catalog/:apiId/deployments` | List API deployments |
| `GET` | `/api/environments` | List environments |

### 2. Request Validation

- Use Pydantic models and FastAPI's built-in validation for:
  - Query parameters: `page`, `page_size`, `sort`, `filter`, `lifecycle`
  - Path parameters: `api_id`, `version_id`
- Return `422` with structured errors for invalid inputs (FastAPI default behavior)

### 3. Response Format

All responses follow a consistent envelope:

```typescript
interface ApiResponse<T> {
  data: T;
  meta?: {
    page: number;
    pageSize: number;
    totalCount: number;
    totalPages: number;
  };
}
```

Error responses:

```typescript
interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
```

### 4. Controller Layer

Create controller functions that:

- Parse and validate request parameters
- Call the appropriate service method
- Map results to response DTOs
- Handle errors and return appropriate status codes

### 5. Pagination

- Default page size: 20
- Max page size: 100
- Include `totalCount` and `totalPages` in meta
- Support cursor-based pagination for large datasets (optional)

### 6. Filtering & Sorting

- Filter by: `lifecycle` (design, development, production, deprecated, retired), `kind` (REST, GraphQL, gRPC)
- Sort by: `name`, `updatedAt`, `createdAt`
- Sort direction: `asc`, `desc`

## Testing & Acceptance Criteria

- [x] `GET /api/catalog` returns paginated list of APIs
- [x] `GET /api/catalog?lifecycle=production` filters correctly
- [x] `GET /api/catalog?sort=name&direction=asc` sorts correctly
- [x] `GET /api/catalog/:apiId` returns full API details or `404`
- [x] `GET /api/catalog/:apiId/versions` returns version list
- [x] `GET /api/catalog/:apiId/versions/:versionId/definition` returns spec document
- [x] Invalid query parameters return `422` with validation errors
- [x] All endpoints return consistent response envelopes
- [x] All routes have pytest integration tests (using `httpx.AsyncClient`)
- [x] API response times are logged

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author  | Notes                                                                                                                                                                                                                                                                                            |
| ---------- | -------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| —          | 🔲 Not Started | —       | Task created                                                                                                                                                                                                                                                                                     |
| 2026-04-16 | ✅ Complete    | copilot | Full implementation: 6 endpoints (list, detail, versions, definition, deployments, environments), Pydantic request validation, consistent response envelopes (ApiResponse/ApiErrorResponse), pagination, filtering (lifecycle/kind), sorting, RBAC. 36 new integration tests, 252 total passing. |

### Technical Decisions

- **Router without prefix**: The router defines full paths (e.g., `/api/catalog`, `/api/environments`) rather than using FastAPI's `prefix` parameter. This keeps route registration in `app.py` simple and makes the URL structure explicit in the router module.
- **Dependency injection for service**: `ApiCatalogService` is injected via `Depends(_get_service)`, allowing tests to override via `app.dependency_overrides` without touching real Azure credentials.
- **Sync handlers for sync service**: All route handlers are declared as regular `def` (not `async def`) because the underlying `ApiCatalogService` and Azure SDK are synchronous. FastAPI automatically runs `def` handlers in a thread-pool, preventing the event loop from being blocked under load.
- **Sort-then-paginate in service layer**: Sorting is applied inside `ApiCatalogService.list_apis()` _before_ pagination so that ordering is consistent across pages. The router translates the API-facing `SortField` enum to a model attribute name and forwards it to the service.
- **OData filter construction**: Lifecycle and kind filters are translated to OData `$filter` expressions and passed through to the service layer, which forwards them to the API Center SDK.
- **Distinct response pagination model**: The router defines `PaginationMetaOut` (camelCase JSON aliases) separate from the internal `PaginationMeta` in `models.api_center` (snake_case only) to keep the HTTP contract and service internals decoupled.
- **Structured error responses via custom exception**: `CatalogApiError` + a registered exception handler produce a top-level `{error: {code, message, details}}` JSON body, matching the documented `ApiErrorResponse` contract without the `{detail: …}` wrapper that `HTTPException` would add.
- **PEP 695 generic syntax**: Used `class ApiResponse[T]` for generic type parameters per PEP 695 (Python 3.14).
- **`noqa: B008` for FastAPI parameters**: All `Query()` and `Depends()` defaults in endpoint signatures are suppressed for Ruff B008, which is standard practice for FastAPI.

### Deviations from Plan

- The plan specified test file `test_api_catalog.py` alongside the router; tests were placed in `tests/test_api_catalog_routes.py` to match the project's convention of keeping tests in the `tests/` directory.
- The plan specified `src/bff/src/bff/routers/` path; the actual layout is `src/bff/apic_vibe_portal_bff/routers/` per the existing project structure (consistent with task 009).
- The plan mentioned returning `400` for invalid query parameters; FastAPI returns `422` (Unprocessable Entity) by default for validation errors, which is the framework's convention and was kept as-is.
- The `/api/environments` route is at the top level (not nested under `/api/catalog`) to reflect that environments are a separate domain concept.

### Validation Results

- **Tests**: 252 total (36 new in `test_api_catalog_routes.py`), all passing — no regressions from 216 baseline
- **Lint**: `uv run ruff check .` passes with no errors or warnings
- **Endpoints verified**: `GET /api/catalog`, `GET /api/catalog/{api_id}`, `GET /api/catalog/{api_id}/versions`, `GET /api/catalog/{api_id}/versions/{version_id}/definition`, `GET /api/catalog/{api_id}/deployments`, `GET /api/environments`
- **Pagination**: Default (page=1, pageSize=20), custom values, max enforcement (pageSize ≤ 100), page ≥ 1
- **Filtering**: lifecycle, kind, combined lifecycle+kind — verified OData filter string generation
- **Sorting**: name asc/desc verified with mock data
- **Error handling**: 404 (not found), 422 (validation), 401 (unauthenticated), 503 (service error) — all verified
- **Response envelopes**: Consistent `{data, meta}` structure across all 6 endpoints

## Coding Agent Prompt

```text
**Task**: Implement plan step 010 — BFF API Catalog Endpoints.

Read the full task specification at `docs/project/plan/010-bff-api-catalog-endpoints.md`.

Reference `docs/project/plan/009-api-center-data-layer.md` for the service layer these endpoints call, and `docs/project/plan/007-shared-types-package.md` for the DTOs.

In `src/bff/src/bff/routers/`, create FastAPI route handlers for the API catalog endpoints (list, detail, versions, definition, deployments, environments). Add request validation using Pydantic models, consistent response envelopes, pagination support, and filtering/sorting.

Write pytest integration tests for all endpoints with mocked service layer. Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/010-bff-api-catalog-endpoints.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
