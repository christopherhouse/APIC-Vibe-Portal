# 011 - Phase 1 MVP: Azure AI Search Index Setup & Indexing Pipeline

## References
- [Architecture Document](../apic_architecture.md) — Search Layer: Azure AI Search; Hybrid search for retrieval
- [Product Charter](../apic_product_charter.md) — Improve API discovery through intelligent search
- [Product Spec](../apic_portal_spec.md) — Search functionality requirements

## Overview
Set up Azure AI Search with an index schema for API metadata and an indexing pipeline that synchronizes data from Azure API Center into the search index. This enables the hybrid (keyword + semantic) search that powers API discovery.

## Dependencies
- **002** — Azure infrastructure (AI Search resource deployed)
- **005** — BFF API project setup
- **007** — API Center data layer (data source for indexing)

## Implementation Details

### 1. Search Index Schema
Define the AI Search index with fields:
| Field | Type | Searchable | Filterable | Sortable | Facetable |
|-------|------|-----------|------------|----------|-----------|
| `id` | String | — | ✓ | — | — |
| `apiName` | String | ✓ | ✓ | ✓ | — |
| `title` | String | ✓ | — | ✓ | — |
| `description` | String | ✓ | — | — | — |
| `kind` | String | — | ✓ | — | ✓ |
| `lifecycleStage` | String | — | ✓ | — | ✓ |
| `versions` | Collection(String) | ✓ | ✓ | — | — |
| `contacts` | Collection(String) | ✓ | — | — | — |
| `tags` | Collection(String) | ✓ | ✓ | — | ✓ |
| `customProperties` | String | ✓ | — | — | — |
| `specContent` | String | ✓ | — | — | — |
| `createdAt` | DateTimeOffset | — | ✓ | ✓ | — |
| `updatedAt` | DateTimeOffset | — | ✓ | ✓ | — |
| `contentVector` | Collection(Single) | — | — | — | — |

### 2. Semantic Configuration
- Enable semantic search with semantic ranking
- Semantic configuration:
  - Title field: `title`
  - Content fields: `description`, `specContent`
  - Keyword fields: `apiName`, `tags`

### 3. Vector Search Configuration
- Add vector search profile using HNSW algorithm
- Vector field: `contentVector` (dimensions matching OpenAI embedding model, e.g., 1536 for text-embedding-ada-002)
- Use Azure OpenAI embeddings for vectorization

### 4. Indexing Pipeline
Create an indexing service in the BFF:
```
src/bff/src/services/
├── search-indexer.service.ts       # Indexing pipeline
└── search-indexer.service.test.ts
```

Operations:
- `fullReindex()` — Fetch all APIs from API Center, generate embeddings, upsert into index
- `incrementalIndex(apiId: string)` — Reindex a single API
- `deleteFromIndex(apiId: string)` — Remove an API from the index
- `getIndexStats()` — Return document count and index size

### 5. Embedding Generation
- Use Azure OpenAI embeddings API to generate vectors
- Combine `title`, `description`, and `specContent` for embedding input
- Chunk large spec content to fit token limits
- Cache embeddings to avoid redundant generation

### 6. Index Management Scripts
Create scripts for operational tasks:
```
scripts/
├── reindex.ts          # Full reindex trigger
└── index-stats.ts      # Print index statistics
```

### 7. Bicep Updates
Add to the AI Search Bicep module:
- Index definition (or document the manual/script-based index creation)
- Skillset for integrated vectorization (optional)

## Testing & Acceptance Criteria
- [ ] Search index is created with correct schema
- [ ] Semantic search configuration is valid
- [ ] Vector search profile is configured with correct dimensions
- [ ] Full reindex processes all APIs from API Center into the search index
- [ ] Incremental index updates a single API document
- [ ] Embeddings are generated using Azure OpenAI
- [ ] Index statistics report correct document count
- [ ] Unit tests cover indexing service with mocked dependencies
- [ ] Reindex script runs successfully end-to-end (integration test)

## Coding Agent Prompt

> **Task**: Implement plan step 011 — Azure AI Search Index Setup & Indexing Pipeline.
>
> Read the full task specification at `docs/project/plan/011-ai-search-index-setup.md`.
>
> Reference the architecture at `docs/project/apic_architecture.md` (Search Layer: AI Search, hybrid search), `docs/project/plan/002-sprint-zero-azure-infra-bicep.md` for the AI Search resource, and `docs/project/plan/007-api-center-data-layer.md` for the data source.
>
> In the BFF, create the search index schema definition (fields, semantic config, vector config), an indexing service that syncs API Center data into the AI Search index with Azure OpenAI embeddings, and operational scripts for full/incremental reindexing. Write unit tests with mocked Azure SDK calls.
>
> Verify the build succeeds and all tests pass.
