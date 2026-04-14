# 007 - Phase 1 MVP: Shared Types & Utilities Package

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Frontend and BFF share data contracts
- [Product Charter](../apic_product_charter.md) — API discovery and AI-assisted workflows require consistent models
- [Product Spec](../apic_portal_spec.md) — Data model requirements

## Overview
Create the shared TypeScript package containing type definitions, interfaces, and utility functions used by both the frontend and BFF. This ensures type safety and consistency across the full stack.

## Dependencies
- **001** — Repository scaffolding (monorepo workspace structure)
- **006** — Frontend project (consumer of shared types)
- **006** — BFF project (consumer of shared types)

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
- Both frontend and BFF reference this as a workspace dependency

## Testing & Acceptance Criteria
- [ ] Package compiles without errors
- [ ] Package is importable from both frontend and BFF workspaces
- [ ] All type guards have corresponding tests
- [ ] All utility functions have tests
- [ ] Barrel export (`index.ts`) exports all public types and utilities
- [ ] No circular dependencies between modules
- [ ] `npm run build` in shared package produces valid output

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
**Task**: Implement plan step 007 — Shared Types & Utilities Package.

Read the full task specification at `docs/project/plan/007-shared-types-package.md`.

Reference the architecture at `docs/project/apic_architecture.md` for the data flow between Frontend and BFF, and `docs/project/apic_product_charter.md` for the domain concepts (API discovery, governance, AI assistance).

Create the shared TypeScript package in `src/shared/` with domain models (API definitions, versions, deployments, search results, chat messages), DTOs for frontend-BFF communication, enum types for API lifecycle and governance states, error types, type guards, and utility functions. Ensure dual CJS/ESM build output and that both `src/frontend` and `src/bff` can import from the shared package.

Write tests for type guards and utility functions. Verify the package builds and is importable from both consumer workspaces.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/007-shared-types-package.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
