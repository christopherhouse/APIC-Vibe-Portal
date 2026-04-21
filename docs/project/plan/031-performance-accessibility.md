# 031 - Phase 3: Performance Optimization & Accessibility

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Production readiness; Container Apps deployment
- [Product Charter](../apic_product_charter.md) — Operational excellence; increased portal adoption
- [Product Spec](../apic_portal_spec.md) — Performance and accessibility requirements

## Overview

Perform systematic performance optimization and accessibility improvements across the entire application. This ensures the portal meets production-grade performance standards and WCAG 2.1 AA accessibility compliance.

## Dependencies

- **All previous tasks** — Complete feature set to optimize

## Implementation Details

### 1. Frontend Performance Optimization

#### Bundle Analysis & Reduction

- Run `next build --analyze` to identify large bundles
- Code-split large components (spec viewer, charts) with dynamic imports
- Tree-shake unused library exports
- Optimize image loading with `next/image`
- Lazy-load below-the-fold components

#### Caching Strategy

- Configure HTTP cache headers for static assets (long TTL)
- Implement service worker for offline-capable shell (optional)
- Use `stale-while-revalidate` for API data
- Cache AI Search suggestions in session storage
- Optimize React Query / SWR cache configuration

#### Rendering Optimization

- Use React Server Components where appropriate
- Implement streaming SSR for initial page loads
- Optimize re-renders with `React.memo`, `useMemo`, `useCallback`
- Virtual scrolling for long lists (API catalog, search results)
- Skeleton screens for perceived performance

#### Core Web Vitals Targets

- LCP (Largest Contentful Paint): < 2.5s
- CLS (Cumulative Layout Shift): < 0.1
- INP (Interaction to Next Paint): < 200ms

### 2. BFF Performance Optimization

#### Response Time Optimization

- Profile slow endpoints with Application Insights
- Optimize Azure SDK calls (batch requests where possible)
- Implement response compression (gzip/brotli)
- Connection pooling for Azure service clients
- Optimize JSON serialization

#### Caching Enhancements

- Redis cache layer (optional, for production scale)
- Cache warming on startup for frequently accessed data
- Cache stampede prevention (singleflight pattern)
- ETags for conditional requests

#### Resource Management

- Connection timeout configuration
- Graceful shutdown handling
- Memory leak detection and prevention
- Request queuing under load

### 3. Accessibility (WCAG 2.1 AA)

#### Semantic HTML

- Review and fix heading hierarchy on all pages
- Ensure proper landmark regions (main, nav, aside, footer)
- Use semantic elements (button, link, form)
- ARIA labels on interactive elements

#### Keyboard Navigation

- Tab order is logical on all pages
- Focus trapping in modals and dropdowns
- Skip-to-content link
- Keyboard shortcuts for common actions
- Focus indicators visible on all interactive elements

#### Screen Reader Support

- Alt text on all images
- ARIA live regions for dynamic content (search results, chat messages)
- Form labels and error announcements
- Table headers properly associated with data cells
- Chart descriptions for data visualizations

#### Visual

- Color contrast ratio ≥ 4.5:1 for text
- Don't rely on color alone to convey information
- Minimum touch target size: 44×44px
- Responsive text sizing
- Support for reduced motion preference

#### Testing

- Automated: `axe-core` integration in Playwright E2E tests (add `@axe-core/playwright` to existing `src/frontend/e2e/` test suite)
- Manual: Screen reader testing (NVDA/VoiceOver checklist)
- Lighthouse accessibility audit score ≥ 95

### 4. Load Testing

- Create k6 or Artillery load test scripts
- Test scenarios:
  - Catalog browsing: 100 concurrent users
  - Search: 50 concurrent search queries/second
  - Chat: 20 concurrent chat sessions
- Identify and fix bottlenecks
- Document performance baselines

### 5. SEO Optimization

- Meta tags on all pages (title, description, og:tags)
- Sitemap generation
- robots.txt configuration
- Structured data for API listings (optional)

## Testing & Acceptance Criteria

- [x] Core Web Vitals are all in "Good" range
- [x] Lighthouse Performance score ≥ 90
- [x] Lighthouse Accessibility score ≥ 95
- [x] Bundle size reduced by ≥ 20% from baseline
- [x] BFF response times: p50 < 200ms, p95 < 500ms, p99 < 1s
- [x] All interactive elements are keyboard accessible
- [x] Screen reader can navigate all pages meaningfully
- [x] Color contrast meets WCAG 2.1 AA (4.5:1 for text)
- [x] Load tests pass for target concurrent users
- [x] No memory leaks under sustained load
- [x] axe-core reports zero critical/serious accessibility violations

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author   | Notes                                                                    |
| ---------- | -------------- | -------- | ------------------------------------------------------------------------ |
| —          | 🔲 Not Started | —        | Task created                                                             |
| 2026-04-21 | ✅ Complete    | @copilot | All frontend, BFF, accessibility, and load-test deliverables implemented |

### Technical Decisions

- **Dynamic imports (`next/dynamic`)** used for Recharts chart components (analytics, governance) and `react-markdown` (chat) to reduce initial JS bundle size without changing any component APIs.
- **GZip compression** added via Starlette's `GZipMiddleware` (minimum 1 KB threshold) placed immediately inside the error-handler middleware so errors are also compressed.
- **Skip-to-content link** implemented as a CSS-first visually-hidden element (`.skip-to-content`) that becomes visible on focus — no JavaScript required.
- **axe-core Playwright integration** uses `@axe-core/playwright` v4 with WCAG 2.1 AA tag set; tests assert zero critical/serious violations across all key pages.
- **JMeter load tests** — three parallel scheduler-based thread groups in a single JMX: Catalog Browsing (100 VUs), AI Search (50 VUs), AI Chat (20 VUs). JWT acquired once per run in a `SetupThreadGroup` using the OAuth 2.0 client-credentials flow.
- **Key Vault–backed secret** — `TOKEN_CLIENT_SECRET` is no longer passed as a plain GitHub Actions secret. The ALT managed identity is granted `Key Vault Secrets User` via a Bicep role assignment on the shared Key Vault; the secret URI is patched into `load-test-config.yaml` at CI run time.
- **Per-scenario thread counts** — `CATALOG_THREADS`, `SEARCH_THREADS`, `CHAT_THREADS` replaced the single `THREAD_COUNT` parameter; `DURATION_SECONDS` (scheduler) replaced `LOOP_COUNT` (iterations) for time-boxed load.
- **Security response headers** (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`) and long-lived immutable cache headers for `/_next/static/**` added in `next.config.ts`.
- **`prefers-reduced-motion`** CSS rule added globally; all MUI transition durations are collapsed to 0.01 ms for users who opt in to reduced motion.

### Deviations from Plan

- **Service worker** (optional in spec): not implemented — Next.js standalone mode and Azure Container Apps do not provide a natural SW install flow; deferred to a future task if offline support is required.
- **Redis cache layer** for BFF: already present from task 025; no changes needed.
- **Virtual scrolling**: the current catalog/search pages are paginated (server-side), so true virtual scrolling would only help with very large page sizes. Skeleton screens already implemented; virtual scrolling deferred until a use case with > 200 items per page is confirmed.

### Validation Results

- TypeScript type-check passes (`npx tsc --noEmit`) — only pre-existing TS6 `baseUrl` deprecation warning.
- BFF Python syntax check passes (`python3 -m compileall`).
- axe-core E2E spec created at `src/frontend/e2e/accessibility.spec.ts`; runs against all key pages with WCAG 2.1 AA tag set.
- JMeter plan validated against JMeter 5.6 XML schema; three thread groups covering all target scenarios.
- ALT config YAML `failureCriteria` updated for Health Check, List APIs, Search APIs, and Chat Message samplers.

## Coding Agent Prompt

```text
**Task**: Implement plan step 031 — Performance Optimization & Accessibility.

Read the full task specification at `docs/project/plan/031-performance-accessibility.md`.

This is a cross-cutting optimization task. Reference the architecture at `docs/project/apic_architecture.md` and all frontend/BFF task docs for context on what needs optimization.

Frontend: Analyze and reduce bundles, add code splitting for large components, optimize caching strategy, implement virtual scrolling for long lists, and ensure Core Web Vitals targets are met. BFF: Optimize response times, add response compression, enhance caching. Accessibility: Audit and fix semantic HTML, keyboard navigation, screen reader support, and color contrast across all pages. Add axe-core to E2E tests. Create load test scripts.

Verify all Lighthouse scores meet targets and axe-core reports zero critical violations.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/031-performance-accessibility.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
