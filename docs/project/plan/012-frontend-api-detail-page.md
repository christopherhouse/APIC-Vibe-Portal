# 012 - Phase 1 MVP: API Detail View Page (Frontend)

> **🔲 Status: Not Started**
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
