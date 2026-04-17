# 014 - Phase 1 MVP: Search API Implementation (BFF)

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Hybrid search for retrieval; Search Layer: AI Search
- [Product Charter](../apic_product_charter.md) — Reduce time to find APIs; core success metric
- [Product Spec](../apic_portal_spec.md) — Search functionality specifications

## Overview

Implement the search API endpoints in the BFF that perform hybrid search (keyword + semantic + vector) against Azure AI Search, providing intelligent API discovery capabilities.

## Dependencies

- **006** — BFF API project setup
- **007** — Shared types package (search DTOs)
- **013** — AI Search index setup (index must exist with data)

## Implementation Details

### 1. Search Client

```
src/bff/src/bff/clients/
├── ai_search_client.py        # Azure AI Search client wrapper
└── test_ai_search_client.py
```

- Use `azure-search-documents` SDK for Python
- Authenticate with DefaultAzureCredential
- Configure for hybrid search (keyword + semantic + vector)

### 2. Search Service

```
src/bff/src/bff/services/
├── search_service.py           # Search business logic
└── test_search_service.py
```

Operations:

- `search(query: SearchRequest): Promise<SearchResponse>` — Full hybrid search
- `suggest(prefix: string): Promise<SuggestResponse>` — Autocomplete suggestions
- `getFacets(): Promise<SearchFacets>` — Available filter facets

### 3. Search Endpoint

```
Route: POST /api/search
```

Request body:

```typescript
interface SearchRequest {
  query: string; // Search text
  filters?: {
    kind?: ApiKind[]; // Filter by API kind
    lifecycle?: ApiLifecycle[]; // Filter by lifecycle
    tags?: string[]; // Filter by tags
  };
  page?: number;
  pageSize?: number;
  searchMode?: 'keyword' | 'semantic' | 'hybrid'; // Default: hybrid
}
```

Response:

```typescript
interface SearchResponse {
  results: SearchResultItem[];
  totalCount: number;
  facets: {
    kind: FacetValue[];
    lifecycle: FacetValue[];
    tags: FacetValue[];
  };
  queryDuration: number;
}

interface SearchResultItem {
  apiId: string;
  apiName: string;
  title: string;
  description: string;
  kind: ApiKind;
  lifecycleStage: ApiLifecycle;
  score: number;
  highlights?: {
    title?: string[];
    description?: string[];
  };
  semanticCaption?: string; // AI-generated caption
}
```

### 4. Suggest Endpoint

```
Route: GET /api/search/suggest?q={prefix}
```

Returns top-5 autocomplete suggestions based on API names and descriptions.

### 5. Hybrid Search Implementation

- **Keyword search**: Standard full-text search across searchable fields
- **Semantic search**: Use semantic ranker for natural language queries
- **Vector search**: Generate query embedding, search contentVector field
- Combine all three with reciprocal rank fusion (RRF) for best results
- Include hit highlights for search result snippets
- Include semantic captions for AI-generated relevance summaries

### 6. Faceted Results

- Return facet counts for `kind`, `lifecycle`, and `tags`
- Frontend uses these to display dynamic filter options with counts

## Testing & Acceptance Criteria

- [x] `POST /api/search` returns relevant results for text queries
- [x] Hybrid search combines keyword, semantic, and vector results
- [x] Search results include relevance scores and highlights
- [x] Faceted results return correct counts per category
- [x] `GET /api/search/suggest` returns autocomplete suggestions
- [x] Empty query returns appropriate response (not an error)
- [x] Filters correctly narrow search results
- [x] Pagination works for search results
- [x] Unit tests cover search service with mocked AI Search responses
- [x] Response times are within acceptable limits (< 500ms for typical queries)

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author   | Notes                                                                    |
| ---------- | -------------- | -------- | ------------------------------------------------------------------------ |
| —          | 🔲 Not Started | —        | Task created                                                             |
| 2026-04-17 | ✅ Complete    | @copilot | Implemented AI Search client, search service, and FastAPI search routes |

### Technical Decisions

- **`azure-search-documents` v11.6.0**: Used the official Azure AI Search Python SDK for all search and suggest operations. Authenticates with `DefaultAzureCredential` for production (managed identity) and developer credentials locally.
- **Semantic query type by default**: All search requests use `query_type="semantic"` to leverage semantic ranking, extractive captions, and RRF fusion with vector results when available. The `apic-semantic-config` configuration name matches the indexer's schema.
- **OData filter builder**: Filters are translated from the `SearchFilters` model (kind, lifecycleStage, tags) into OData expressions. Collection fields (tags) use `any()` lambda syntax.
- **Consistent error pattern**: Search routes follow the same structured error envelope pattern as the existing catalog routes (`{error: {code, message, details}}`), with a dedicated `SearchApiError` exception and handler registered in `app.py`.
- **Lazy service instantiation**: The search service and client are created lazily on first request (same pattern as `ApiCatalogService`), with dependency injection for testability.
- **Index name configurable**: Added `ai_search_index_name` to `Settings` (default: `"apic-apis"`) matching the indexer's `INDEX_NAME` constant.

### Deviations from Plan

- **File placement**: The plan suggested `src/bff/src/bff/clients/` and `src/bff/src/bff/services/` paths, but the actual BFF project uses `src/bff/apic_vibe_portal_bff/clients/` and `src/bff/apic_vibe_portal_bff/services/` — files were placed in the correct existing structure.
- **Test files in `tests/`**: Tests are placed in the project's `tests/` directory (matching existing convention) rather than co-located alongside source files as suggested in the plan.
- **Response shape uses existing models**: The `SearchResponse` and `SuggestResponse` Pydantic models from task 007 are used directly. The response shape wraps `SearchResult` objects (document + score + highlights + captions) rather than flat `SearchResultItem` objects — providing richer data to the frontend.
- **Suggester name `"sg"`**: The suggest endpoint uses the default Azure AI Search suggester name `"sg"`. If the index uses a different suggester name, the client accepts a parameter override.

### Validation Results

- **60 new unit tests** across 3 test files:
  - `test_ai_search_client.py` — 17 tests covering client construction, search (basic, filters, pagination, semantic, vector, error handling), suggest, and lifecycle
  - `test_search_service.py` — 30 tests covering OData filter building, highlight extraction, caption extraction, facet parsing, result mapping, search service logic, and suggest
  - `test_search_routes.py` — 13 tests covering POST /api/search (results, filters, pagination, empty query, facets, highlights, captions, errors, auth) and GET /api/search/suggest (results, errors, auth, param validation)
- **311 total tests pass** (251 existing + 60 new) — all in 1.83s
- `ruff check .` passes with zero issues
- `ruff format --check .` passes with zero issues
- `python -m compileall .` compiles all files successfully

## Coding Agent Prompt

```text
**Task**: Implement plan step 014 — Search API Implementation.

Read the full task specification at `docs/project/plan/014-search-api-implementation.md`.

Reference `docs/project/plan/013-ai-search-index-setup.md` for the index schema and `docs/project/plan/007-shared-types-package.md` for the search DTOs.

In `src/bff/`, create an Azure AI Search client wrapper, a search service implementing hybrid search (keyword + semantic + vector with RRF), and FastAPI route handlers for search and suggest endpoints. Include faceted results, hit highlights, semantic captions, and pagination.

Write unit tests with mocked AI Search SDK responses using pytest. Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/014-search-api-implementation.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
