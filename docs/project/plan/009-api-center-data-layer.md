# 009 - Phase 1 MVP: Azure API Center Data Layer Integration

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Azure API Center as the core API catalog data source
- [Product Charter](../apic_product_charter.md) — Improve API discovery; API metadata completeness
- [Product Spec](../apic_portal_spec.md) — API catalog and metadata requirements

## Overview

Integrate the BFF with Azure API Center to read API definitions, versions, deployments, and environments. This creates the data layer that powers the API catalog, providing the foundation for all API browsing and discovery features.

## Dependencies

- **002** — Azure infrastructure (API Center resource deployed)
- **006** — BFF API project setup
- **007** — Shared types package (API models and DTOs)

## Implementation Details

### 1. Azure API Center Client

Create a typed client wrapper around the Azure API Center SDK:

```
src/bff/src/bff/clients/
├── api_center_client.py        # Main client class
├── test_api_center_client.py
└── mocks/
    └── api_center_responses.py # Mock responses for testing
```

- Use `azure-mgmt-apicenter` SDK or REST API directly via `httpx`
- Authenticate using `azure-identity` (DefaultAzureCredential for managed identity)
- Wrap all operations with error handling and logging
- Implement retry logic with exponential backoff

### 2. Service Layer

```
src/bff/src/bff/services/
├── api_catalog_service.py      # Business logic for catalog operations
└── test_api_catalog_service.py
```

Implement the following operations:

- `listApis(options: ListApisOptions): Promise<PaginatedResult<ApiDefinition>>` — List APIs with pagination, filtering, sorting
- `getApi(apiId: string): Promise<ApiDefinition>` — Get a single API with all metadata
- `listApiVersions(apiId: string): Promise<ApiVersion[]>` — List versions for an API
- `getApiDefinition(apiId: string, versionId: string): Promise<ApiSpecification>` — Get OpenAPI/AsyncAPI spec
- `listEnvironments(): Promise<ApiEnvironment[]>` — List deployment environments
- `listDeployments(apiId: string): Promise<ApiDeployment[]>` — List deployments for an API

### 3. Data Mapping

- Map API Center SDK responses to Pydantic models (mirroring the shared TypeScript types from package 006)
- Handle nullable fields and optional properties gracefully
- Normalize API metadata for consistent frontend consumption

### 4. Caching Layer

- Implement in-memory caching with configurable TTL
- Cache API list results (short TTL: 2-5 minutes)
- Cache individual API details (medium TTL: 5-10 minutes)
- Cache environment/deployment info (long TTL: 15-30 minutes)
- Provide cache invalidation mechanism

### 5. Configuration

Add to BFF settings:

- `API_CENTER_RESOURCE_GROUP` — Resource group containing API Center
- `API_CENTER_SERVICE_NAME` — API Center service name
- `API_CENTER_SUBSCRIPTION_ID` — Azure subscription ID
- `CACHE_TTL_SECONDS` — Default cache TTL

## Testing & Acceptance Criteria

- [x] API Center client connects successfully with managed identity (integration test)
- [x] `listApis` returns paginated API definitions mapped to shared models
- [x] `getApi` returns complete API details with versions and deployments
- [x] `getApiDefinition` returns the OpenAPI/AsyncAPI specification document
- [x] Error handling covers: not found, unauthorized, service unavailable
- [x] Caching reduces redundant API Center calls (verifiable via mock tests)
- [x] All service methods have unit tests with mocked API Center responses
- [x] Data mapping correctly handles missing/nullable fields

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author  | Notes        |
| ---------- | -------------- | ------- | ------------ |
| —          | 🔲 Not Started | —       | Task created |
| 2026-04-16 | ✅ Complete    | copilot | Full implementation: ApiCenterClient, ApiCatalogService, data mapper, in-memory cache, Pydantic models. 189 tests passing (94 new). |

### Technical Decisions

- **`azure-mgmt-apicenter` SDK over direct REST calls**: Used the official management SDK (`azure-mgmt-apicenter>=1.0.0`) rather than raw `httpx` calls for type safety and managed retry/auth handling.
- **DefaultAzureCredential**: Credential is injected via constructor (default `DefaultAzureCredential`), making the client unit-testable with a mock credential without requiring real Azure access.
- **In-process pagination**: The API Center SDK returns all pages via a lazy pager; pagination is applied in-process in `ApiCatalogService.list_apis`. This is simpler and sufficient for typical API Center catalog sizes. A future task can add server-side `$skip`/`$top` if needed.
- **Separate mapper module** (`api_center_mapper.py`): All SDK-to-Pydantic conversion is in pure functions with no side effects, making them trivially testable without instantiating the full service.
- **Python 3.14 generic syntax** (`class CacheEntry[V]`): Used PEP 695 syntax for generics as enforced by Ruff `UP046` for the target Python version.
- **StrEnum for domain enums**: Used `StrEnum` (available since Python 3.11) so enum values serialize directly to their string representation in JSON responses without custom serializers.
- **Differentiated cache TTLs**: API lists (2 min), API details/versions (5 min), specifications (10 min), environments/deployments (15 min) — balancing freshness vs. call reduction.

### Deviations from Plan

- The plan referenced a `src/bff/src/bff/` layout (nested `src` directory); the actual BFF layout uses `src/bff/apic_vibe_portal_bff/` (flat source directory per the existing project structure).
- Mock responses live in `tests/api_center_mocks.py` rather than `clients/mocks/api_center_responses.py` to keep them alongside the test suite and avoid polluting the production package.
- Settings added `api_center_subscription_id`, `api_center_resource_group`, `api_center_service_name`, and `cache_ttl_seconds` as new fields alongside the pre-existing `api_center_endpoint` field (retained for potential direct REST usage).

### Validation Results

- **Tests**: 189 tests (94 new tests across `test_cache.py`, `test_api_center_mapper.py`, `test_api_center_client.py`, `test_api_catalog_service.py`), all passing
- **Lint**: `uv run ruff check .` passes with no errors or warnings
- **Existing tests**: All 95 pre-existing tests continue to pass (no regressions)
- **New dependencies added**: `azure-identity>=1.21.0`, `azure-mgmt-apicenter>=1.0.0`

## Coding Agent Prompt

```text
**Task**: Implement plan step 009 — Azure API Center Data Layer Integration.

Read the full task specification at `docs/project/plan/009-api-center-data-layer.md`.

Reference the architecture at `docs/project/apic_architecture.md` for how the BFF connects to Azure API Center, and `docs/project/plan/007-shared-types-package.md` for the shared models to map to.

In `src/bff/`, create an Azure API Center client using the Azure SDK for Python with DefaultAzureCredential, a service layer with operations for listing/getting APIs, versions, deployments, and specifications, a data mapping layer to convert SDK responses to Pydantic models (mirroring the shared TypeScript types), and an in-memory caching layer.

Write comprehensive unit tests with mocked API Center responses using pytest. Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/009-api-center-data-layer.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
