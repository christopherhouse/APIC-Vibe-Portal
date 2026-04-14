# 008 - Phase 1 MVP: BFF API Catalog Endpoints

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — BFF required for orchestration between frontend and Azure services
- [Product Charter](../apic_product_charter.md) — Improve API discovery
- [Product Spec](../apic_portal_spec.md) — API catalog browsing requirements

## Overview
Implement the REST API endpoints in the BFF that expose API catalog data to the frontend. These endpoints serve as the contract between the Next.js frontend and the Azure API Center data layer.

## Dependencies
- **005** — BFF API project setup (Express app, routing)
- **006** — Shared types package (DTOs)
- **007** — API Center data layer (service and client)

## Implementation Details

### 1. Route Definitions
```
src/bff/src/routes/
├── api-catalog.routes.ts       # API catalog endpoints
├── api-catalog.routes.test.ts
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
- Use a validation library (e.g., `zod` or `joi`) for:
  - Query parameters: `page`, `pageSize`, `sort`, `filter`, `lifecycle`
  - Path parameters: `apiId`, `versionId`
- Return `400` with structured errors for invalid inputs

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
- [ ] `GET /api/catalog` returns paginated list of APIs
- [ ] `GET /api/catalog?lifecycle=production` filters correctly
- [ ] `GET /api/catalog?sort=name&direction=asc` sorts correctly
- [ ] `GET /api/catalog/:apiId` returns full API details or `404`
- [ ] `GET /api/catalog/:apiId/versions` returns version list
- [ ] `GET /api/catalog/:apiId/versions/:versionId/definition` returns spec document
- [ ] Invalid query parameters return `400` with validation errors
- [ ] All endpoints return consistent response envelopes
- [ ] All routes have supertest integration tests
- [ ] API response times are logged

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

> **Task**: Implement plan step 008 — BFF API Catalog Endpoints.
>
> Read the full task specification at `docs/project/plan/008-bff-api-catalog-endpoints.md`.
>
> Reference `docs/project/plan/007-api-center-data-layer.md` for the service layer these endpoints call, and `docs/project/plan/006-shared-types-package.md` for the DTOs.
>
> In `src/bff/src/routes/`, create Express route handlers for the API catalog endpoints (list, detail, versions, definition, deployments, environments). Add request validation using zod, consistent response envelopes, pagination support, and filtering/sorting.
>
> Write supertest integration tests for all endpoints with mocked service layer. Verify the build succeeds and all tests pass.
>
> **Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/008-bff-api-catalog-endpoints.md`):
> 1. Change the status banner at the top to `> **✅ Status: Complete**`
> 2. Add a row to the Status History table with the completion date and a summary
> 3. Record any technical decisions made under "Technical Decisions"
> 4. Note any deviations from the plan under "Deviations from Plan"
> 5. Record test/validation results under "Validation Results"
