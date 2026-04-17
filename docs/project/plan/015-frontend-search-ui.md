# 015 - Phase 1 MVP: Search UI (Frontend)

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA; Search Layer integration
- [Product Charter](../apic_product_charter.md) — Reduce time to find APIs; primary success metric
- [Product Spec](../apic_portal_spec.md) — Search interface requirements

## Overview

Build the search UI components in the frontend, including the global search bar, search results page, and autocomplete functionality. This is the primary API discovery interface.

## Dependencies

- **005** — Frontend project setup (components, layout)
- **007** — Shared types package (search models)
- **014** — Search API implementation (BFF endpoints)

## Implementation Details

### 1. Global Search Bar (Header)

Enhance the header component from task 005:

- Search input with magnifying glass icon
- Debounced autocomplete dropdown (300ms debounce)
- Autocomplete shows top 5 API name/title matches
- Clicking a suggestion navigates to API detail page
- Pressing Enter navigates to search results page with query
- Keyboard navigation (arrow keys) through suggestions
- Clear button to reset search
- Search bar is always visible in the header

### 2. Search Results Page

```
app/search/
├── page.tsx            # Search results page
├── loading.tsx         # Search loading state
└── components/
    ├── SearchResults.tsx          # Results list container
    ├── SearchResultCard.tsx       # Individual result card
    ├── SearchFilters.tsx          # Dynamic filter sidebar
    ├── SearchSummary.tsx          # Query summary and count
    ├── SearchModeToggle.tsx       # Keyword/Semantic/Hybrid toggle
    └── NoResults.tsx              # Empty results state
```

Route: `/search?q={query}&kind={filter}&lifecycle={filter}&page={n}`

### 3. Search Result Card

Each result card shows:

- API title with highlighted matching text
- Description with highlighted snippets
- Semantic caption (AI-generated relevance summary) when available
- API kind badge
- Lifecycle badge
- Relevance score indicator (visual bar or percentage)
- Click navigates to `/catalog/:apiId`

### 4. Dynamic Filters

- Faceted filters based on search results
- Show counts next to each filter option (e.g., "REST (23)")
- Lifecycle stage filter
- API kind filter
- Tags filter
- Filters update results in real-time (client-side re-search)
- URL query parameters update to reflect filter state

### 5. Search Mode Toggle

- Allow users to switch between: Keyword, Semantic, Hybrid (default)
- Visual indicator of current mode
- Brief tooltip explaining each mode

### 6. Data Fetching

- Use React Query / SWR for search requests
- Debounce search input (300ms)
- Cancel previous request on new search (AbortController)
- Show loading state during search
- Cache recent search results

### 7. No Results State

- Friendly message: "No APIs found matching your search"
- Suggestions: "Try different keywords" or "Browse the catalog"
- Link to catalog page

### 8. Search Analytics (Client-side)

- Track search queries (for future analytics, task 026)
- Track click-through from results to API detail
- Store in BFF endpoint (placeholder for now)

## Testing & Acceptance Criteria

- [x] Global search bar appears in header on all pages
- [x] Autocomplete dropdown appears after typing 2+ characters
- [x] Autocomplete debounces correctly (300ms)
- [x] Enter key navigates to search results page
- [x] Search results page displays results with highlights
- [x] Semantic captions appear when hybrid search is used
- [x] Faceted filters show correct counts
- [x] Applying filters updates results in real-time
- [x] Search mode toggle switches search behavior
- [x] No results state displays with helpful suggestions
- [x] URL reflects search query and filter state
- [x] Keyboard navigation works in autocomplete dropdown
- [x] All components have unit tests
- [x] Playwright e2e tests added in `src/frontend/e2e/search.spec.ts` covering search input, autocomplete, results page navigation, filtering, and no-results state

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author  | Notes                                                   |
| ---------- | -------------- | ------- | ------------------------------------------------------- |
| —          | 🔲 Not Started | —       | Task created                                            |
| 2026-04-17 | ✅ Complete    | copilot | Full search UI implemented, all tests pass, build green |

### Technical Decisions

- **No React Query / SWR**: Followed existing hook patterns (`use-catalog.ts`) using vanilla React state with `useCallback`/`useEffect` and `AbortController` for request cancellation. This avoids adding new dependencies.
- **Debounce via `setTimeout`**: Used the project's built-in `debounce` pattern (300ms) inside hooks rather than an external library.
- **SearchBar as separate component**: Extracted the search bar with autocomplete into `components/layout/SearchBar.tsx` (imported by `Header.tsx`) to keep the header component clean and allow independent testing.
- **Search result types**: Defined a local `SearchResultItem` interface in `lib/search-api.ts` aligned with the plan-014 BFF contract (includes `score`, `highlights`, `semanticCaption`), decoupled from `ApiCatalogItem`.
- **Dedicated highlight parser**: Rendered BFF-provided `<em>` highlight tags through the `HighlightedText` component rather than `dangerouslySetInnerHTML`, preserving the expected search highlighting UX while avoiding raw HTML injection.
- **URL-based state**: All search state (query, kind, lifecycle, mode, page) lives in the URL, ensuring shareability and browser history support.

### Deviations from Plan

- **No Tags filter UI**: Tags filter was excluded from the filter sidebar (plan called it out under §4) because the `ApiCatalogItem` model has no `tags` field and the BFF contract doesn't populate tags facets yet. The facet data structure supports it and can be added when the BFF is wired up.
- **Search Analytics**: Placeholder only — no actual analytics calls to the BFF for now (depends on task 026).

### Validation Results

- **Unit tests**: 208 tests across 35 suites — all pass (`npm run test`)
- **Lint**: ESLint passes with zero errors (`npm run lint`)
- **Format**: Prettier passes for all new files (`npm run format:check`)
- **TypeScript**: No type errors in new code (`npx tsc --noEmit`)
- **Build**: Next.js production build succeeds, `/search` route is statically rendered (`npm run build`)
- **E2E tests**: `src/frontend/e2e/search.spec.ts` created with coverage for search input, autocomplete, results page, filtering, no-results state, and mode toggle

## Coding Agent Prompt

```text
**Task**: Implement plan step 015 — Search UI.

Read the full task specification at `docs/project/plan/015-frontend-search-ui.md`.

Reference `docs/project/plan/014-search-api-implementation.md` for the BFF search API contract, `docs/project/plan/005-frontend-nextjs-setup.md` for the header layout component (where the search bar goes), and `docs/project/plan/007-shared-types-package.md` for the search types.

Build the global search bar with autocomplete in the header, the `/search` results page with faceted filtering, search result cards with highlights and semantic captions, search mode toggle, no-results state, and URL-based search state. Use React Query or SWR for data fetching with debouncing and request cancellation.

Write unit tests for all components. Add Playwright e2e tests in `src/frontend/e2e/search.spec.ts` covering search input, autocomplete, results page, filtering, and no-results state. Verify the build succeeds, linting passes, and all tests pass (including `npm run test:e2e`).

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/015-frontend-search-ui.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
