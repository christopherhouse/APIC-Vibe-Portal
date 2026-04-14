# 014 - Phase 1 MVP: Search API Implementation (BFF)

> **🔲 Status: Not Started**
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
