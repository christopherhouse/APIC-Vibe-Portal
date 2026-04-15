# 021 - Phase 1 MVP: End-to-End Integration Testing & MVP Polish

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Full stack: Frontend ↔ BFF ↔ Azure services
- [Product Charter](../apic_product_charter.md) — Phase 1: MVP delivery
- [Product Spec](../apic_portal_spec.md) — MVP feature completeness

## Overview

Validate the complete MVP by implementing end-to-end integration tests, performing cross-cutting quality improvements, and ensuring all Phase 1 features work together seamlessly. This task closes out the MVP phase.

## Dependencies

- **All tasks 001-018** — Complete MVP feature set

## Implementation Details

### 1. E2E Test Suite

Playwright is already installed and configured in `src/frontend/` (set up in task 005). The existing e2e tests in `src/frontend/e2e/` cover the application shell, navigation, and 404 pages. This task extends the suite with comprehensive user-flow tests.

```
src/frontend/e2e/
├── app-shell.spec.ts           # ✅ Already exists (task 005)
├── navigation.spec.ts          # ✅ Already exists (task 005)
├── not-found.spec.ts           # ✅ Already exists (task 005)
├── auth.spec.ts                # Login/logout flows
├── catalog.spec.ts             # API catalog browsing (may exist from task 011)
├── api-detail.spec.ts          # API detail viewing (may exist from task 012)
├── search.spec.ts              # Search and filtering (may exist from task 015)
├── chat.spec.ts                # AI chat interaction (may exist from task 018)
└── full-journey.spec.ts        # Full user journey
```

- Use Playwright for browser automation (already installed and configured in `src/frontend/playwright.config.ts`)
- Configure for Chromium, Firefox, and WebKit (projects already defined in config)
- CI runs e2e tests via the `e2e-frontend` job in `.github/workflows/ci.yml` — extend this as needed
- Run against local dev environment with mocked Azure services

### 2. E2E Test Scenarios

#### Authentication Flow

- User navigates to portal → redirected to login
- User logs in → redirected back to catalog
- User sees their name in header
- User logs out → redirected to login page

#### API Catalog Journey

- Authenticated user sees catalog page with API cards
- User filters by lifecycle "Production" → only production APIs shown
- User sorts by name A-Z → APIs sorted alphabetically
- User clicks an API card → navigates to detail page
- Detail page shows all tabs (Overview, Versions, Spec, Deployments)
- User downloads API specification

#### Search Journey

- User types in global search bar → autocomplete appears
- User submits search → results page shows matches with highlights
- User applies filters → results narrow down
- User clicks a result → navigates to API detail

#### AI Chat Journey

- User opens chat page → suggested prompts shown
- User sends a message → AI responds with relevant API information
- Response includes citations → clicking citation opens API detail
- Conversation maintains context across multiple messages

#### Full User Journey

- Login → Browse catalog → Search for an API → View detail → Ask AI for help → Logout

### 3. MVP Polish Checklist

- [ ] All pages have proper page titles and meta tags
- [ ] Loading states are consistent across all pages
- [ ] Error states are user-friendly with recovery options
- [ ] 404 page is styled and helpful
- [ ] Keyboard navigation works across all interactive elements
- [ ] Focus management is correct after navigation
- [ ] Color contrast meets WCAG 2.1 AA standards
- [ ] Responsive design works at all breakpoints
- [ ] No console errors in production build
- [ ] API response times are acceptable (< 2s for page loads)

### 4. Performance Baseline

- Measure and document:
  - Lighthouse scores (Performance, Accessibility, Best Practices, SEO)
  - Core Web Vitals (LCP, FID, CLS)
  - BFF API response times (p50, p95, p99)
  - Search query latency
  - Chat response time (time to first token)

### 5. Documentation Update

- Update README with MVP feature overview
- Add architecture diagram with deployed component URLs
- Document known limitations and Phase 2 roadmap items

## Testing & Acceptance Criteria

- [ ] All E2E tests pass on Chromium, Firefox, and WebKit
- [ ] Authentication flow works end-to-end
- [ ] Catalog browsing, filtering, and sorting work end-to-end
- [ ] API detail page renders all sections correctly
- [ ] Search returns relevant results with highlights
- [ ] AI chat provides grounded responses with citations
- [ ] No console errors in production build
- [ ] Lighthouse accessibility score ≥ 90
- [ ] All Core Web Vitals are in "Good" range
- [ ] Documentation is up to date with MVP features

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

### Technical Decisions

_No technical decisions recorded yet._

### Deviations from Plan

_No deviations from the original plan._

### Validation Results

_No validation results yet._

## Coding Agent Prompt

```text
**Task**: Implement plan step 021 — End-to-End Integration Testing & MVP Polish.

Read the full task specification at `docs/project/plan/021-e2e-testing-mvp-polish.md`.

This task validates all Phase 1 MVP features (tasks 001-018) work together. Reference the full plan directory at `docs/project/plan/` for the features that should be tested.

Set up Playwright in the `e2e/` directory with tests for: authentication flow, catalog browsing, API detail viewing, search with filters, and AI chat interaction. Create a full user journey test. Perform MVP polish: verify loading states, error states, accessibility, responsive design, and performance.

Run all E2E tests and fix any issues. Measure and document Lighthouse scores and Core Web Vitals. Update the root README with MVP documentation.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/021-e2e-testing-mvp-polish.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
