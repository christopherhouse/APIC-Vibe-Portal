# 011 - Phase 1 MVP: API Catalog Listing Page (Frontend)

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA
- [Product Charter](../apic_product_charter.md) — Improve API discovery; primary goal
- [Product Spec](../apic_portal_spec.md) — API catalog browsing UI

## Overview

Build the API catalog listing page in the frontend — the primary landing experience for developers. This page displays all APIs from Azure API Center in a browsable, filterable, sortable grid/list view.

## Dependencies

- **005** — Frontend project setup (Next.js, components)
- **007** — Shared types package (API models)
- **010** — BFF API catalog endpoints (data source)

## Implementation Details

### 1. Page Route

- Route: `/catalog` (Next.js App Router page)
- Also serve as the homepage redirect target (`/` → `/catalog`)

### 2. Page Structure

```
app/catalog/
├── page.tsx            # Server component: initial data fetch
├── loading.tsx         # Catalog loading skeleton
├── error.tsx           # Error state
└── components/
    ├── ApiCatalogGrid.tsx       # Grid/List view container
    ├── ApiCard.tsx              # Individual API card
    ├── CatalogFilters.tsx       # Filter sidebar/bar
    ├── CatalogSort.tsx          # Sort controls
    ├── CatalogPagination.tsx    # Pagination controls
    └── ViewToggle.tsx           # Grid/List view toggle
```

### 3. API Card Component

Each API card displays:

- API name/title
- Description (truncated)
- API kind badge (REST, GraphQL, gRPC)
- Lifecycle stage badge (color-coded)
- Version count
- Last updated date
- Click navigates to detail page (`/catalog/:apiId`)

### 4. Filtering

- **Lifecycle Stage**: Multi-select checkboxes (Design, Development, Production, Deprecated, Retired)
- **API Kind**: Multi-select checkboxes (REST, GraphQL, gRPC, SOAP)
- Filters reflected in URL query parameters for shareability
- Filter state managed via URL search params (Next.js `useSearchParams`)

### 5. Sorting

- Sort by: Name (A-Z, Z-A), Last Updated, Created Date
- Default: Last Updated (newest first)

### 6. Pagination

- Page size selector (10, 20, 50)
- Page number navigation with first/last/prev/next
- Total count display ("Showing 1-20 of 147 APIs")

### 7. View Modes

- Grid view (card grid, default)
- List view (compact table rows)
- Persist preference in localStorage

### 8. Data Fetching

- Use server components for initial page load (SSR)
- Use React hooks (`useSWR` or `@tanstack/react-query`) for client-side refetching when filters/sort/page change
- Loading skeletons during data fetch
- Empty state when no APIs match filters

### 9. Responsive Design

- Grid: 3 columns (desktop) → 2 columns (tablet) → 1 column (mobile)
- Filters: sidebar (desktop) → collapsible drawer (mobile)

## Testing & Acceptance Criteria

- [ ] Catalog page renders with API cards from BFF
- [ ] Lifecycle filter correctly filters displayed APIs
- [ ] API kind filter correctly filters displayed APIs
- [ ] Sort controls change the order of displayed APIs
- [ ] Pagination navigates between pages
- [ ] Grid/List toggle switches view mode
- [ ] Clicking an API card navigates to `/catalog/:apiId`
- [ ] Filter state is reflected in URL (shareable links)
- [ ] Empty state shown when no APIs match filters
- [ ] Loading skeletons display during data fetch
- [ ] Page is responsive across desktop, tablet, and mobile
- [ ] All components have unit tests
- [ ] Playwright e2e tests added in `src/frontend/e2e/catalog.spec.ts` covering catalog browsing, filtering, sorting, and navigation to detail pages

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date | Status         | Author | Notes        |
| ---- | -------------- | ------ | ------------ |
| —    | 🔲 Not Started | —      | Task created |
| 2026-04-16 | ✅ Complete | copilot | Full implementation: 6 catalog components (ApiCard, ApiCatalogGrid, CatalogFilters, CatalogSort, CatalogPagination, ViewToggle), catalog API client, useCatalog hook, /catalog page with URL-based filter state, loading skeleton, empty state, responsive layout, grid/list view toggle, homepage redirect. 38 new unit tests (109 total), 12 Playwright e2e tests, build and lint clean. |

### Technical Decisions

- **Client component page**: The `/catalog/page.tsx` is a `'use client'` component rather than a server component because all filtering, sorting, pagination, and view toggle state is managed client-side via URL search params and React hooks. The initial render shows a loading skeleton while data is fetched client-side from the BFF.
- **URL-based filter state**: All filter, sort, and pagination state is stored in URL search params using Next.js `useSearchParams()` and `router.push()`, making filter states shareable via URL and supporting browser back/forward navigation.
- **Stable hook dependencies**: Serialized array params (`lifecycles.join(',')`, `JSON.stringify(params)`) are used as stable dependency keys for `useMemo` and `useCallback` to prevent infinite re-render loops caused by array reference changes.
- **MUI v9 API**: Uses `slotProps` instead of deprecated `PaperProps`/`inputProps` for MUI Drawer and Checkbox, and `aria-label` directly on Checkbox instead of `inputProps`.
- **LocalStorage view mode**: Grid/list view preference is persisted in `localStorage` and read on mount, defaulting to grid view.
- **BFF API client**: Separate `lib/catalog-api.ts` module wraps fetch calls to the BFF's `/api/catalog` endpoint with typed request/response handling, usable both server-side and client-side.
- **Playwright route mocking**: E2e tests use `page.route()` to intercept BFF API calls and return mock data, enabling full catalog page testing without a running BFF server.

### Deviations from Plan

- The plan specified the page as a server component for initial SSR with client-side refetching. The implementation uses a single `'use client'` component because the extensive interactive state (filters, sort, pagination, view toggle) makes server component composition impractical. Loading skeletons provide the same UX during initial data fetch.
- The plan suggested `useSWR` or `@tanstack/react-query` for client-side data fetching. Instead, a lightweight custom `useCatalog` hook was implemented using React's built-in `useState`, `useCallback`, `useEffect`, and `useTransition`, avoiding an additional dependency.
- The plan specified mobile filters as a collapsible drawer. The implementation uses MUI Drawer component for mobile (triggered by a filter icon button), and a fixed sidebar on desktop.

### Validation Results

- **Unit Tests**: 109 total (38 new across 7 test suites), all passing — no regressions from 71 baseline
  - `ApiCard.test.tsx` — 8 tests (grid/list rendering, navigation, badges, version count)
  - `ApiCatalogGrid.test.tsx` — 3 tests (grid mode, list mode, empty state)
  - `CatalogFilters.test.tsx` — 8 tests (lifecycle/kind toggles, clear all, checkbox state)
  - `CatalogSort.test.tsx` — 3 tests (render, display value, sort change callback)
  - `CatalogPagination.test.tsx` — 5 tests (item count display, pagination controls, empty state, page ranges)
  - `ViewToggle.test.tsx` — 5 tests (render, active state, toggle, no double-click)
  - `catalog-api.test.ts` — 6 tests (default fetch, params, filters, error handling)
- **E2e Tests**: 12 Playwright tests in `catalog.spec.ts`, all passing
  - Catalog page heading and API cards display
  - Homepage redirect to /catalog
  - Empty state when no APIs match
  - Loading skeleton during data fetch
  - Lifecycle filter narrows APIs and updates URL
  - Kind filter narrows APIs and updates URL
  - Filter state reflected in URL (shareability)
  - Sort controls functional and update URL
  - Pagination item count and page navigation
  - Grid/list view toggle
  - API card click navigates to detail page
- **Build**: `npm run build` succeeds with no TypeScript errors
- **Lint**: `eslint .` passes with no errors or warnings

## Coding Agent Prompt

```text
**Task**: Implement plan step 011 — API Catalog Listing Page.

Read the full task specification at `docs/project/plan/011-frontend-api-catalog-page.md`.

Reference `docs/project/plan/005-frontend-nextjs-setup.md` for the frontend structure, `docs/project/plan/010-bff-api-catalog-endpoints.md` for the BFF API contract, and `docs/project/plan/007-shared-types-package.md` for the shared types.

Create the `/catalog` page in the Next.js app with: an API card grid/list view, lifecycle and kind filters, sorting controls, pagination, view mode toggle, URL-based filter state, loading skeletons, empty states, and responsive layout. Use server components for initial SSR and client-side data fetching for filter/sort/page changes.

Write unit tests for all components. Verify the build succeeds, linting passes, and all tests pass. Add Playwright e2e tests in `src/frontend/e2e/catalog.spec.ts` covering catalog browsing, filtering, sorting, and card navigation. Run `npm run test:e2e` to verify.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/011-frontend-api-catalog-page.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
