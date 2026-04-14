# 013 - Phase 1 MVP: Azure AI Search Index Setup & Indexing Pipeline

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Search Layer: Azure AI Search; Hybrid search for retrieval
- [Product Charter](../apic_product_charter.md) — Improve API discovery through intelligent search
- [Product Spec](../apic_portal_spec.md) — Search functionality requirements

## Overview
Set up Azure AI Search with an index schema for API metadata and an indexing pipeline that synchronizes data from Azure API Center into the search index. This enables the hybrid (keyword + semantic) search that powers API discovery.

## Dependencies
- **002** — Azure infrastructure (AI Search resource deployed)
- **006** — BFF API project setup
- **009** — API Center data layer (data source for indexing)

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
src/bff/src/bff/services/
├── search_indexer_service.py       # Indexing pipeline
└── test_search_indexer_service.py
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
├── reindex.py          # Full reindex trigger
└── index_stats.py      # Print index statistics
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
**Task**: Implement plan step 013 — Azure AI Search Index Setup & Indexing Pipeline.

Read the full task specification at `docs/project/plan/013-ai-search-index-setup.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Search Layer: AI Search, hybrid search), `docs/project/plan/002-sprint-zero-azure-infra-bicep.md` for the AI Search resource, and `docs/project/plan/007-api-center-data-layer.md` for the data source.

In the BFF, create the search index schema definition (fields, semantic config, vector config), an indexing service that syncs API Center data into the AI Search index with Azure OpenAI embeddings, and operational Python scripts for full/incremental reindexing. Write unit tests with mocked Azure SDK calls using pytest.

Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/013-ai-search-index-setup.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
