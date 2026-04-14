# 009 - Phase 1 MVP: API Catalog Listing Page (Frontend)

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA
- [Product Charter](../apic_product_charter.md) — Improve API discovery; primary goal
- [Product Spec](../apic_portal_spec.md) — API catalog browsing UI

## Overview
Build the API catalog listing page in the frontend — the primary landing experience for developers. This page displays all APIs from Azure API Center in a browsable, filterable, sortable grid/list view.

## Dependencies
- **004** — Frontend project setup (Next.js, components)
- **006** — Shared types package (API models)
- **008** — BFF API catalog endpoints (data source)

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
**Task**: Implement plan step 009 — API Catalog Listing Page.

Read the full task specification at `docs/project/plan/009-frontend-api-catalog-page.md`.

Reference `docs/project/plan/004-frontend-nextjs-setup.md` for the frontend structure, `docs/project/plan/008-bff-api-catalog-endpoints.md` for the BFF API contract, and `docs/project/plan/006-shared-types-package.md` for the shared types.

Create the `/catalog` page in the Next.js app with: an API card grid/list view, lifecycle and kind filters, sorting controls, pagination, view mode toggle, URL-based filter state, loading skeletons, empty states, and responsive layout. Use server components for initial SSR and client-side data fetching for filter/sort/page changes.

Write unit tests for all components. Verify the build succeeds, linting passes, and all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/009-frontend-api-catalog-page.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
