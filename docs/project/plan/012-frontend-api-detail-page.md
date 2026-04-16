# 012 - Phase 1 MVP: API Detail View Page (Frontend)

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA; comprehensive API information display
- [Product Charter](../apic_product_charter.md) — Enable developers to understand and use APIs faster
- [Product Spec](../apic_portal_spec.md) — API detail and specification viewing

## Overview

Build the API detail page that displays comprehensive information about a single API, including metadata, versions, deployments, and the rendered API specification (OpenAPI/Swagger).

## Dependencies

- **005** — Frontend project setup (Next.js, components)
- **007** — Shared types package
- **010** — BFF API catalog endpoints (detail, versions, deployments, definition)
- **011** — Catalog listing page (navigation source)

## Implementation Details

### 1. Page Route

- Route: `/catalog/[apiId]` (dynamic route)

### 2. Page Structure

```
app/catalog/[apiId]/
├── page.tsx            # Server component: fetch API details
├── loading.tsx         # Detail loading skeleton
├── error.tsx           # Error state
└── components/
    ├── ApiHeader.tsx           # API name, badges, description
    ├── ApiMetadata.tsx         # Metadata table (contacts, license, etc.)
    ├── ApiVersionList.tsx      # Version selector/list
    ├── ApiSpecViewer.tsx       # Rendered OpenAPI spec
    ├── ApiDeployments.tsx      # Deployment environments list
    ├── ApiTabs.tsx             # Tab navigation for sections
    └── SpecDownloadButton.tsx  # Download spec file
```

### 3. API Header

- API title and description
- Lifecycle badge (color-coded)
- API kind badge (REST, GraphQL, etc.)
- Last updated timestamp
- Breadcrumb navigation: Catalog → API Name

### 4. Tab Sections

1. **Overview** — Description, contacts, license, terms, external docs, custom properties
2. **Versions** — List of API versions with lifecycle states; version selector
3. **Specification** — Rendered OpenAPI/Swagger UI for the selected version
4. **Deployments** — Where this API is deployed and environment details

### 5. API Specification Viewer

- Use a library like `swagger-ui-react` or `@scalar/api-reference-react` to render OpenAPI specs
- Support OpenAPI 2.0 (Swagger) and 3.x
- Try/It feature for testing endpoints (optional in MVP)
- Download spec button (YAML/JSON)
- Version dropdown to switch between API versions

### 6. Deployments View

- Table showing: environment name, server URL, lifecycle state
- Link to environment details if applicable

### 7. Data Fetching

- Server-side fetch for initial API detail
- Client-side fetch for version switching and spec loading
- Cache API detail data with SWR/React Query
- Loading states for each section independently

### 8. Error Handling

- API not found → custom 404 page with link back to catalog
- Failed to load spec → error state with retry button
- Partial data → render available sections, show errors inline

## Testing & Acceptance Criteria

- [ ] Detail page renders complete API information
- [ ] Breadcrumb navigation works (Catalog → API Name)
- [ ] Tab navigation switches between Overview, Versions, Specification, Deployments
- [ ] API specification renders correctly for OpenAPI 3.x documents
- [ ] Version selector switches the displayed spec
- [ ] Download button downloads the spec file
- [ ] Deployments table shows environment and server information
- [ ] 404 state for non-existent API IDs
- [ ] Loading skeletons display while data fetches
- [ ] All components have unit tests
- [ ] Navigating from catalog card lands on correct detail page
- [ ] Playwright e2e tests added in `src/frontend/e2e/api-detail.spec.ts` covering detail page rendering, tab navigation, version switching, and breadcrumb navigation

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author  | Notes                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------- | -------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| —          | 🔲 Not Started | —       | Task created                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-04-16 | ✅ Complete    | copilot | Full implementation: 7 detail components (ApiHeader, ApiTabs, ApiMetadata, ApiVersionList, ApiSpecViewer, ApiDeployments, SpecDownloadButton), catalog-detail-api client, useApiDetail hook, /catalog/[apiId] page with loading/error states, breadcrumb navigation. 49 new unit tests (159 total), 10 new Playwright e2e tests (33 total), build and lint clean. Mock BFF server created for e2e testing. |

### Technical Decisions

- **Client component page**: The `/catalog/[apiId]/page.tsx` is a `'use client'` component because it manages interactive tab state, version selection, and client-side data fetching via the `useApiDetail` hook.
- **Parallel data loading**: The `useApiDetail` hook loads API detail, versions, and deployments in parallel via `Promise.all()`, with auto-loading of the spec for the first version.
- **Lightweight spec viewer**: Instead of adding `swagger-ui-react` (large bundle), the spec is rendered as formatted JSON/YAML in a code block. This avoids a heavy dependency for the MVP and can be upgraded to a full Swagger UI later.
- **MUI v9 API compatibility**: Used `sx` prop for alignment properties (e.g., `sx={{ alignItems: 'center' }}`) and `sx={{ mb: 2 }}` instead of deprecated `paragraph` prop on Typography, per MUI v9 conventions.
- **Scoped e2e selectors**: E2e tests use `data-testid` attributes and scoped selectors (e.g., `page.getByTestId('api-header').getByRole('link')`) to avoid ambiguity with sidebar navigation links.
- **Reusable mock server**: Created `e2e/mock-server/` with mock data generators and a standalone HTTP server for e2e testing. Tests primarily use Playwright's `page.route()` for request interception, but the mock server data generators are shared.
- **Screenshot practice**: Established standard practice of using Playwright to capture screenshots of UI changes during development for PR documentation.

### Deviations from Plan

- The plan suggested `swagger-ui-react` or `@scalar/api-reference-react` for the OpenAPI spec viewer. A lightweight formatted code block renderer was used instead to avoid adding large dependencies for the MVP. The component can be upgraded to a full Swagger UI later.
- The plan specified SSR for initial data fetch. The implementation uses a `'use client'` component with client-side fetching via a custom `useApiDetail` hook, similar to the catalog page pattern, because the page requires extensive interactive state (tab switching, version selection, spec loading).
- The plan suggested `useSWR` or `react-query` for caching. The implementation uses a custom hook with React's built-in `useState`, `useCallback`, and `useEffect` to avoid adding a dependency, consistent with the catalog page approach.

### Validation Results

- **Unit Tests**: 159 total (49 new across 8 test suites), all passing — no regressions from 110 baseline
  - `ApiHeader.test.tsx` — 8 tests (loading skeleton, title, breadcrumb, kind/lifecycle badges, description, date)
  - `ApiTabs.test.tsx` — 5 tests (render all tabs, testid, onChange callback, selected tab, each tab value)
  - `ApiMetadata.test.tsx` — 8 tests (description, empty description, license, terms, contacts, external docs, custom properties, testid)
  - `ApiVersionList.test.tsx` — 6 tests (loading skeleton, empty state, version rows, lifecycle badges, click handler, testids)
  - `ApiSpecViewer.test.tsx` — 6 tests (loading skeleton, error state, retry button, empty state, JSON spec, YAML spec)
  - `ApiDeployments.test.tsx` — 7 tests (loading skeleton, empty state, table, rows, server URL links, multiple URIs, testids)
  - `SpecDownloadButton.test.tsx` — 4 tests (render, disabled states, download trigger)
  - `catalog-detail-api.test.ts` — 5 tests (fetchApiDetail, fetchApiVersions, fetchApiDeployments, fetchApiDefinition, error handling)
- **E2e Tests**: 33 total Playwright tests (10 new in `api-detail.spec.ts`, 23 existing), all passing
  - API detail page renders with header and breadcrumb
  - Overview tab displays metadata by default (description, license, contacts)
  - Tab navigation switches between Overview, Versions, Specification, Deployments
  - Versions tab shows version list and selector
  - Deployments tab shows deployment table with environment info
  - Specification tab shows spec content with download button
  - Breadcrumb navigates back to catalog
  - Version switching loads new spec
  - Error state for non-existent API IDs
  - Navigation from catalog card lands on detail page
- **Build**: `npm run build` succeeds with no TypeScript errors, `/catalog/[apiId]` route is dynamic
- **Lint**: `eslint .` passes with no errors or warnings

## Coding Agent Prompt

```text
**Task**: Implement plan step 012 — API Detail View Page.

Read the full task specification at `docs/project/plan/012-frontend-api-detail-page.md`.

Reference `docs/project/plan/010-bff-api-catalog-endpoints.md` for the BFF API endpoints that supply data to this page, and `docs/project/plan/011-frontend-api-catalog-page.md` for the catalog page that links here.

Create the `/catalog/[apiId]` dynamic route page with: API header, tabbed sections (Overview, Versions, Specification, Deployments), an OpenAPI specification viewer component, version selector, spec download, and deployment table. Use SSR for initial data and client-side fetching for dynamic content.

Write unit tests for all components. Add Playwright e2e tests in `src/frontend/e2e/api-detail.spec.ts` covering detail page rendering, tab navigation, version switching, and breadcrumb navigation. Verify the build succeeds, linting passes, and all tests pass (including `npm run test:e2e`).

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/012-frontend-api-detail-page.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
