# 007 - Phase 1 MVP: Shared Types & Utilities Package

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Frontend and BFF share data contracts
- [Product Charter](../apic_product_charter.md) — API discovery and AI-assisted workflows require consistent models
- [Product Spec](../apic_portal_spec.md) — Data model requirements

## Overview

Create the shared TypeScript package containing type definitions, interfaces, and utility functions used by the frontend. The BFF is a Python 3.14 / FastAPI application and will define its own Pydantic models mirroring these contracts. This package ensures type safety on the frontend side, and the type definitions serve as the canonical reference for the frontend-BFF API contract.

## Dependencies

- **001** — Repository scaffolding (monorepo workspace structure)
- **005** — Frontend project (consumer of shared types)
- **006** — BFF project (defines corresponding Pydantic models for the same contracts)

## Implementation Details

### 1. Package Setup

```
src/shared/
├── src/
│   ├── index.ts                # Public API barrel export
│   ├── models/
│   │   ├── api-definition.ts   # API definition model
│   │   ├── api-version.ts      # API version model
│   │   ├── api-deployment.ts   # API deployment info
│   │   ├── api-environment.ts  # Environment model
│   │   ├── search-result.ts    # Search result model
│   │   ├── chat-message.ts     # Chat/AI message model
│   │   ├── user.ts             # User profile model
│   │   └── pagination.ts       # Pagination models
│   ├── enums/
│   │   ├── api-lifecycle.ts    # API lifecycle states
│   │   ├── api-kind.ts         # REST, GraphQL, gRPC, etc.
│   │   └── governance-status.ts # Governance compliance states
│   ├── dto/
│   │   ├── api-catalog-response.ts   # Catalog listing response
│   │   ├── api-detail-response.ts    # API detail response
│   │   ├── search-request.ts         # Search request DTO
│   │   ├── search-response.ts        # Search response DTO
│   │   ├── chat-request.ts           # Chat request DTO
│   │   └── chat-response.ts          # Chat response DTO
│   ├── errors/
│   │   ├── app-error.ts        # Base application error
│   │   └── error-codes.ts      # Standardized error codes
│   └── utils/
│       ├── type-guards.ts      # Runtime type checking utilities
│       └── formatters.ts       # Common formatting functions
├── __tests__/
│   ├── models/
│   ├── utils/
│   └── type-guards.test.ts
├── tsconfig.json
├── jest.config.ts
└── package.json
```

### 2. Core Models

#### API Definition

```typescript
interface ApiDefinition {
  id: string;
  name: string;
  title: string;
  description: string;
  kind: ApiKind;
  lifecycleStage: ApiLifecycle;
  termsOfService?: string;
  license?: string;
  externalDocs?: ExternalDoc[];
  contacts?: Contact[];
  customProperties?: Record<string, unknown>;
  versions: ApiVersion[];
  deployments: ApiDeployment[];
  createdAt: string;
  updatedAt: string;
}
```

#### Search Result

```typescript
interface SearchResult<T> {
  items: T[];
  totalCount: number;
  facets?: SearchFacets;
  queryDuration: number;
}
```

#### Chat Message

```typescript
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  timestamp: string;
}
```

### 3. DTOs (Data Transfer Objects)

- Request DTOs: Typed payloads sent from frontend to BFF
- Response DTOs: Typed payloads returned from BFF to frontend
- All DTOs should be serialization-friendly (no class instances, pure interfaces)

### 4. Error Types

- `AppError` base class with `code`, `message`, `statusCode`
- Standard error codes enum for consistent error handling

### 5. Utilities

- Type guards for runtime validation of API responses
- Formatters for dates, byte sizes, URL normalization

### 6. Package Configuration

- Compile to CommonJS and ESM (dual package)
- Export via `package.json` `exports` field
- The frontend references this as a workspace dependency
- The BFF (Python) will define corresponding Pydantic models — these TypeScript types serve as the source of truth for the API contract

## Testing & Acceptance Criteria

- [x] Package compiles without errors
- [x] Package is importable from the frontend workspace
- [x] Type definitions serve as reference for BFF Pydantic models
- [x] All type guards have corresponding tests
- [x] All utility functions have tests
- [x] Barrel export (`index.ts`) exports all public types and utilities
- [x] No circular dependencies between modules
- [x] `npm run build` in shared package produces valid output

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author  | Notes                                                                                                                                |
| ---------- | -------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| —          | 🔲 Not Started | —       | Task created                                                                                                                         |
| 2026-04-15 | ✅ Complete    | copilot | Full implementation: enums, models, DTOs, errors, utilities, type guards, formatters. 69 tests passing. Dual CJS/ESM build verified. |

### Technical Decisions

- **Dual CJS/ESM output**: Separate `tsconfig.esm.json` and `tsconfig.cjs.json` with `rewriteRelativeImportExtensions` for TS 6.0 compatibility. CJS output uses a nested `package.json` with `{"type":"commonjs"}` to resolve correctly under the parent `"type":"module"` package.
- **ts-jest test config**: Used a dedicated `tsconfig.test.json` with `moduleResolution: "node10"` + `ignoreDeprecations: "6.0"` since ts-jest 29.x does not yet support the `bundler` resolution mode natively. Added `ignoreDiagnostics: [5107]` in jest config for resilience.
- **String enums over union types**: Used TypeScript `enum` for `ApiLifecycle`, `ApiKind`, `GovernanceStatus`, and `ErrorCode` so they produce runtime values usable in type guards and serialization, not just compile-time types.
- **Generic SearchResult and PaginatedResponse**: Both support generic type parameters for reuse across different entity types.
- **`toApiCatalogItem` transformer**: Included in DTOs as a pure function to convert full `ApiDefinition` to summary `ApiCatalogItem`.

### Deviations from Plan

- Added `EnvironmentKind` enum in `api-environment.ts` (not in original spec) to type the environment kind field.
- Added `ChatSession` interface alongside `ChatMessage` to model conversation threads.
- Added `Citation` and `ChatRole` types to support AI citation linking.
- Test file `__tests__/models/app-error-and-dto.test.ts` covers both AppError and toApiCatalogItem rather than a separate `type-guards.test.ts` at the top level (test coverage is equivalent).

### Validation Results

- **Build**: `npm run build` produces valid CJS (`dist/cjs/`) and ESM (`dist/esm/`) output with type declarations (`dist/types/`)
- **Tests**: 69 tests across 3 test suites, all passing
- **Lint**: `eslint .` passes with no errors or warnings
- **CJS import**: Verified via `require('@apic-vibe-portal/shared')` — all exports accessible
- **ESM import**: Verified via `import { ... } from '@apic-vibe-portal/shared'` — all exports accessible
- **Frontend build**: `next build` succeeds with shared package as workspace dependency

## Coding Agent Prompt

```text
**Task**: Implement plan step 007 — Shared Types & Utilities Package.

Read the full task specification at `docs/project/plan/007-shared-types-package.md`.

Reference the architecture at `docs/project/apic_architecture.md` for the data flow between Frontend and BFF, and `docs/project/apic_product_charter.md` for the domain concepts (API discovery, governance, AI assistance).

Create the shared TypeScript package in `src/shared/` with domain models (API definitions, versions, deployments, search results, chat messages), DTOs for frontend-BFF communication, enum types for API lifecycle and governance states, error types, type guards, and utility functions. Ensure dual CJS/ESM build output and that `src/frontend` can import from the shared package. These types also serve as the canonical reference for the BFF's corresponding Pydantic models (Python).

Write tests for type guards and utility functions. Verify the package builds and is importable from both consumer workspaces.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/007-shared-types-package.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
