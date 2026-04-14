# 022 - Phase 2: API Comparison Feature

## References
- [Architecture Document](../apic_architecture.md) — AI-powered features for API understanding
- [Product Charter](../apic_product_charter.md) — Phase 2: Governance + Compare
- [Product Spec](../apic_portal_spec.md) — API comparison requirements

## Overview
Build the API comparison feature that allows developers to compare two or more APIs side-by-side. This includes both a structured data comparison and an AI-powered analysis that highlights key differences, similarities, and trade-offs.

## Dependencies
- **007** — API Center data layer (API metadata)
- **008** — BFF API catalog endpoints (API detail data)
- **010** — Frontend API detail page (navigation source)
- **020** — Foundry Agent setup (AI-powered analysis)

## Implementation Details

### 1. Comparison BFF Endpoints
```
src/bff/src/routes/
├── api-compare.routes.ts           # Comparison endpoints
└── api-compare.routes.test.ts
```

Endpoints:
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/compare` | Compare multiple APIs |
| `POST` | `/api/compare/ai-analysis` | AI-powered comparison analysis |

#### Compare Request
```typescript
interface CompareRequest {
  apiIds: string[];               // 2-5 API IDs to compare
  aspects?: CompareAspect[];      // Optional: specific aspects to compare
}

type CompareAspect = 
  | 'metadata'        // Name, description, contacts, license
  | 'versions'        // Version history and current state
  | 'endpoints'       // API endpoints/operations count and types
  | 'governance'      // Governance scores and compliance
  | 'deployments'     // Deployment environments
  | 'specifications'; // Spec format, schemas, security schemes
```

#### Compare Response
```typescript
interface CompareResponse {
  apis: CompareApiSummary[];
  aspects: AspectComparison[];
  aiAnalysis?: string;            // Only in AI analysis endpoint
}
```

### 2. Comparison Service
```
src/bff/src/services/
├── api-compare.service.ts          # Comparison logic
└── api-compare.service.test.ts
```

- Fetch full details for all requested APIs
- Generate structured comparisons across each aspect
- Highlight differences and similarities
- Calculate a "similarity score" between APIs

### 3. AI-Powered Analysis
- Use the agent system (or direct OpenAI) to generate a narrative comparison
- Prompt includes structured data for all compared APIs
- Analysis covers: use case fit, trade-offs, recommendations
- Include governance comparison if scores are available

### 4. Frontend Comparison UI
```
app/compare/
├── page.tsx                # Comparison page
├── loading.tsx
└── components/
    ├── CompareSelector.tsx         # API selection interface
    ├── CompareTable.tsx            # Side-by-side comparison table
    ├── CompareAspectRow.tsx        # Individual aspect row
    ├── CompareAiAnalysis.tsx       # AI analysis section
    ├── CompareAddButton.tsx        # Add API to comparison
    └── CompareEmptyState.tsx       # No APIs selected state
```

### 5. Comparison Table Design
- Side-by-side columns (one per API, max 5)
- Rows grouped by aspect category
- Visual diff highlighting (green for advantages, yellow for differences)
- Sticky headers for API names
- Responsive: horizontal scroll on mobile

### 6. API Selection
- Search-based selection (reuse search component)
- "Add to compare" button on API detail page and catalog cards
- Comparison state stored in URL parameters (`?compare=id1,id2,id3`)
- Minimum 2 APIs required, maximum 5

### 7. Integration with Catalog & Detail Pages
- Add "Compare" button on API cards in catalog
- Add "Add to Compare" button on API detail page
- Show comparison bar at bottom when APIs are selected
- Comparison bar shows selected API count and "Compare" button

## Testing & Acceptance Criteria
- [ ] Comparison endpoint accepts 2-5 API IDs and returns structured comparison
- [ ] Structured comparison covers all aspects (metadata, versions, endpoints, etc.)
- [ ] AI analysis provides meaningful narrative comparison
- [ ] Frontend comparison table renders side-by-side correctly
- [ ] API selector allows adding/removing APIs to compare
- [ ] "Add to compare" works from catalog cards and detail pages
- [ ] Comparison state persists in URL
- [ ] Responsive layout handles mobile/tablet screens
- [ ] Empty state shows when fewer than 2 APIs selected
- [ ] Unit tests cover comparison service and all components

## Coding Agent Prompt

> **Task**: Implement plan step 022 — API Comparison Feature.
>
> Read the full task specification at `docs/project/plan/022-api-comparison-feature.md`.
>
> Reference `docs/project/plan/008-bff-api-catalog-endpoints.md` for the catalog API contract, `docs/project/plan/020-foundry-agent-setup.md` for the agent system powering AI analysis, and `docs/project/plan/010-frontend-api-detail-page.md` for the detail page integration.
>
> In the BFF, create comparison endpoints and a service that generates structured multi-API comparisons with optional AI-powered narrative analysis. In the frontend, create the `/compare` page with side-by-side table, API selector, AI analysis section, and integrate "Add to Compare" buttons in catalog cards and detail pages.
>
> Write unit tests for the comparison service and all frontend components. Verify the build succeeds and all tests pass.
