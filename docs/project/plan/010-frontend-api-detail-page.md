# 010 - Phase 1 MVP: API Detail View Page (Frontend)

## References
- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA; comprehensive API information display
- [Product Charter](../apic_product_charter.md) — Enable developers to understand and use APIs faster
- [Product Spec](../apic_portal_spec.md) — API detail and specification viewing

## Overview
Build the API detail page that displays comprehensive information about a single API, including metadata, versions, deployments, and the rendered API specification (OpenAPI/Swagger).

## Dependencies
- **004** — Frontend project setup (Next.js, components)
- **006** — Shared types package
- **008** — BFF API catalog endpoints (detail, versions, deployments, definition)
- **009** — Catalog listing page (navigation source)

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

## Coding Agent Prompt

> **Task**: Implement plan step 010 — API Detail View Page.
>
> Read the full task specification at `docs/project/plan/010-frontend-api-detail-page.md`.
>
> Reference `docs/project/plan/008-bff-api-catalog-endpoints.md` for the BFF API endpoints that supply data to this page, and `docs/project/plan/009-frontend-api-catalog-page.md` for the catalog page that links here.
>
> Create the `/catalog/[apiId]` dynamic route page with: API header, tabbed sections (Overview, Versions, Specification, Deployments), an OpenAPI specification viewer component, version selector, spec download, and deployment table. Use SSR for initial data and client-side fetching for dynamic content.
>
> Write unit tests for all components. Verify the build succeeds, linting passes, and all tests pass.
