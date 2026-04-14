# 012 - Phase 1 MVP: Search API Implementation (BFF)

## References
- [Architecture Document](../apic_architecture.md) — Hybrid search for retrieval; Search Layer: AI Search
- [Product Charter](../apic_product_charter.md) — Reduce time to find APIs; core success metric
- [Product Spec](../apic_portal_spec.md) — Search functionality specifications

## Overview
Implement the search API endpoints in the BFF that perform hybrid search (keyword + semantic + vector) against Azure AI Search, providing intelligent API discovery capabilities.

## Dependencies
- **005** — BFF API project setup
- **006** — Shared types package (search DTOs)
- **011** — AI Search index setup (index must exist with data)

## Implementation Details

### 1. Search Client
```
src/bff/src/clients/
├── ai-search-client.ts        # Azure AI Search client wrapper
└── ai-search-client.test.ts
```

- Use `@azure/search-documents` SDK
- Authenticate with DefaultAzureCredential
- Configure for hybrid search (keyword + semantic + vector)

### 2. Search Service
```
src/bff/src/services/
├── search.service.ts           # Search business logic
└── search.service.test.ts
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
  query: string;                    // Search text
  filters?: {
    kind?: ApiKind[];               // Filter by API kind
    lifecycle?: ApiLifecycle[];     // Filter by lifecycle
    tags?: string[];                // Filter by tags
  };
  page?: number;
  pageSize?: number;
  searchMode?: 'keyword' | 'semantic' | 'hybrid';  // Default: hybrid
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
  semanticCaption?: string;     // AI-generated caption
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
- [ ] `POST /api/search` returns relevant results for text queries
- [ ] Hybrid search combines keyword, semantic, and vector results
- [ ] Search results include relevance scores and highlights
- [ ] Faceted results return correct counts per category
- [ ] `GET /api/search/suggest` returns autocomplete suggestions
- [ ] Empty query returns appropriate response (not an error)
- [ ] Filters correctly narrow search results
- [ ] Pagination works for search results
- [ ] Unit tests cover search service with mocked AI Search responses
- [ ] Response times are within acceptable limits (< 500ms for typical queries)

## Coding Agent Prompt

> **Task**: Implement plan step 012 — Search API Implementation.
>
> Read the full task specification at `docs/project/plan/012-search-api-implementation.md`.
>
> Reference `docs/project/plan/011-ai-search-index-setup.md` for the index schema and `docs/project/plan/006-shared-types-package.md` for the search DTOs.
>
> In `src/bff/`, create an Azure AI Search client wrapper, a search service implementing hybrid search (keyword + semantic + vector with RRF), and Express route handlers for search and suggest endpoints. Include faceted results, hit highlights, semantic captions, and pagination.
>
> Write unit tests with mocked AI Search SDK responses. Verify the build succeeds and all tests pass.
