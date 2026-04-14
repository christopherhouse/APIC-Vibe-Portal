# 007 - Phase 1 MVP: Azure API Center Data Layer Integration

## References
- [Architecture Document](../apic_architecture.md) — Azure API Center as the core API catalog data source
- [Product Charter](../apic_product_charter.md) — Improve API discovery; API metadata completeness
- [Product Spec](../apic_portal_spec.md) — API catalog and metadata requirements

## Overview
Integrate the BFF with Azure API Center to read API definitions, versions, deployments, and environments. This creates the data layer that powers the API catalog, providing the foundation for all API browsing and discovery features.

## Dependencies
- **002** — Azure infrastructure (API Center resource deployed)
- **005** — BFF API project setup
- **006** — Shared types package (API models and DTOs)

## Implementation Details

### 1. Azure API Center Client
Create a typed client wrapper around the Azure API Center SDK:
```
src/bff/src/clients/
├── api-center-client.ts        # Main client class
├── api-center-client.test.ts
└── __mocks__/
    └── api-center-responses.ts # Mock responses for testing
```

- Use `@azure/arm-apicenter` SDK or REST API directly
- Authenticate using `@azure/identity` (DefaultAzureCredential for managed identity)
- Wrap all operations with error handling and logging
- Implement retry logic with exponential backoff

### 2. Service Layer
```
src/bff/src/services/
├── api-catalog.service.ts      # Business logic for catalog operations
└── api-catalog.service.test.ts
```

Implement the following operations:
- `listApis(options: ListApisOptions): Promise<PaginatedResult<ApiDefinition>>` — List APIs with pagination, filtering, sorting
- `getApi(apiId: string): Promise<ApiDefinition>` — Get a single API with all metadata
- `listApiVersions(apiId: string): Promise<ApiVersion[]>` — List versions for an API
- `getApiDefinition(apiId: string, versionId: string): Promise<ApiSpecification>` — Get OpenAPI/AsyncAPI spec
- `listEnvironments(): Promise<ApiEnvironment[]>` — List deployment environments
- `listDeployments(apiId: string): Promise<ApiDeployment[]>` — List deployments for an API

### 3. Data Mapping
- Map API Center SDK responses to shared model types (from package 006)
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
- [ ] API Center client connects successfully with managed identity (integration test)
- [ ] `listApis` returns paginated API definitions mapped to shared models
- [ ] `getApi` returns complete API details with versions and deployments
- [ ] `getApiDefinition` returns the OpenAPI/AsyncAPI specification document
- [ ] Error handling covers: not found, unauthorized, service unavailable
- [ ] Caching reduces redundant API Center calls (verifiable via mock tests)
- [ ] All service methods have unit tests with mocked API Center responses
- [ ] Data mapping correctly handles missing/nullable fields

## Coding Agent Prompt

> **Task**: Implement plan step 007 — Azure API Center Data Layer Integration.
>
> Read the full task specification at `docs/project/plan/007-api-center-data-layer.md`.
>
> Reference the architecture at `docs/project/apic_architecture.md` for how the BFF connects to Azure API Center, and `docs/project/plan/006-shared-types-package.md` for the shared models to map to.
>
> In `src/bff/`, create an Azure API Center client using the Azure SDK with DefaultAzureCredential, a service layer with operations for listing/getting APIs, versions, deployments, and specifications, a data mapping layer to convert SDK responses to shared types, and an in-memory caching layer.
>
> Write comprehensive unit tests with mocked API Center responses. Verify the build succeeds and all tests pass.
