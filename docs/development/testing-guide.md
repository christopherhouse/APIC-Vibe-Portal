# Testing Guide

This guide describes the testing strategy, tools, and conventions for the APIC Vibe Portal AI.

## Testing Philosophy

- **Test behaviour, not implementation** — tests should describe what the user or system can do, not how the code works internally
- **Use mocks at the boundary** — mock external services (BFF API, Azure) at the network layer, not by replacing internal modules
- **Prefer integration over unit** — component tests with React Testing Library are more valuable than isolated unit tests of helpers
- **E2E for user journeys** — critical user flows must be covered by Playwright E2E tests

## Test Types

### Unit Tests (Jest + React Testing Library)

Located in `src/frontend/__tests__/` and `src/shared/__tests__/`.

**What to test**:

- Utility functions and data transformation logic
- Custom React hooks (`renderHook`)
- Individual components that contain significant logic
- Shared type validation utilities

**Tools**:

- **Jest 30** — test runner
- **React Testing Library (RTL)** — component rendering and interaction
- **jest-dom** — custom DOM matchers (`toBeVisible`, `toHaveValue`, etc.)
- **MSW** (if used) — mock service worker for BFF mocking in unit tests

**Run**:

```bash
# All unit tests
npm run test

# Watch mode
npm run test:watch

# With coverage
npm run test:ci
```

**Coverage target**: > 80% for business logic utilities.

### E2E Tests (Playwright)

Located in `src/frontend/e2e/`.

**Directory structure**:

```
e2e/
├── smoke/                     # Basic health and auth smoke tests
├── features/                  # Feature-specific tests (catalog, search, chat…)
├── journeys/                  # Full user journey tests
├── cross-cutting/             # Accessibility, performance, security
├── regression/                # Full regression suite
├── mock-server/               # Shared mock BFF server
└── *.spec.ts                  # Legacy flat test files (still valid)
```

**Tools**:

- **Playwright** — cross-browser E2E testing (Chromium, Firefox, WebKit)
- **@axe-core/playwright** — WCAG 2.1 AA accessibility checks
- **page.route()** — BFF request interception (no real Azure needed)

**Run**:

```bash
# All E2E tests
npm run test:e2e --workspace=@apic-vibe-portal/frontend

# Chromium only
npm run test:e2e:chromium --workspace=@apic-vibe-portal/frontend

# Single file
npx playwright test e2e/catalog.spec.ts --project=chromium

# UI mode (interactive debugger)
npm run test:e2e:ui --workspace=@apic-vibe-portal/frontend
```

### BFF Tests (pytest)

Located in `src/bff/tests/`.

**What to test**:

- FastAPI router handlers (using `TestClient` from `httpx`)
- Business logic in service modules
- Data transformation and mapping
- Authentication middleware

**Run**:

```bash
cd src/bff
uv run pytest
uv run pytest --cov --cov-report=term-missing  # with coverage
```

## Writing E2E Tests

### BFF Mocking Pattern

All E2E tests mock the BFF using `page.route()`. This pattern ensures tests are deterministic and do not require Azure credentials.

```typescript
import { test, expect } from '@playwright/test';

test('catalog displays APIs', async ({ page }) => {
  // 1. Set up mock before navigating
  await page.route('**/api/catalog*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [{ id: 'api-1', title: 'Payments API' /* ... */ }],
        meta: { page: 1, pageSize: 20, totalCount: 1, totalPages: 1 },
      }),
    })
  );

  // 2. Navigate
  await page.goto('/catalog');

  // 3. Assert
  await expect(page.getByText('Payments API')).toBeVisible();
});
```

### Mock User Injection

To simulate an authenticated user, inject via `window.__PLAYWRIGHT_USER__`:

```typescript
async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}
```

Must be called **before** `page.goto()`.

### Reusable Mock Data

Use `generateMockApis()` and `generateMockSpec()` from `e2e/mock-server/index.ts` for consistent test data:

```typescript
import { generateMockApis } from '../mock-server';

const apis = generateMockApis(5);
```

## Test Data Guidelines

- Mock data should be **realistic** but not real (no real API names, real users, or real credentials)
- Use fixed seeds or deterministic generation so tests are reproducible
- Keep mock data minimal — only include fields the test actually needs

## Accessibility Testing

Accessibility tests use `@axe-core/playwright`:

```typescript
import AxeBuilder from '@axe-core/playwright';

test('catalog has no critical axe violations', async ({ page }) => {
  await page.goto('/catalog');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  const criticalViolations = results.violations.filter(
    (v) => v.impact === 'critical' || v.impact === 'serious'
  );
  expect(criticalViolations).toHaveLength(0);
});
```

Target: **zero critical/serious violations** on all pages.

## CI Integration

E2E tests run in CI via the `e2e-frontend` job in `.github/workflows/ci.yml`:

1. Next.js dev server starts on port 3000
2. Playwright tests run against it (Chromium only in CI for speed)
3. HTML test report is uploaded as a CI artifact on failure

Unit tests run in the `test-frontend` job.

## Related Documentation

- **[Local Development](local-development.md)**
- **[Architecture Deep Dive](architecture-deep-dive.md)**
- **[Contributing](contributing.md)**
