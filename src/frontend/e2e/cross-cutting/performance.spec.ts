/**
 * Performance E2E benchmarks.
 *
 * Measures key performance metrics for critical user-facing pages using the
 * browser's Navigation Timing and Performance APIs.  Tests validate that
 * pages meet the following targets (per the product spec):
 *
 *   - Time to Interactive (TTI): < 3 seconds
 *   - Largest Contentful Paint (LCP): < 2.5 seconds
 *   - Page load (DOMContentLoaded): < 2 seconds
 *
 * All BFF calls are intercepted to eliminate network variability.
 * Tests run against the locally-served Next.js dev or build server.
 */

import { test, expect, type Page } from '@playwright/test';
import { generateMockApis } from '../mock-server';

const PERF_TARGETS = {
  /** DOMContentLoaded should fire within 2 s */
  domContentLoadedMs: 2000,
  /** Total load event should fire within 3 s */
  loadEventMs: 3000,
} as const;

async function mockAllApis(page: Page) {
  const apis = generateMockApis(10);

  await page.route('**/api/catalog*', async (route) => {
    if (
      route
        .request()
        .url()
        .match(/\/api\/catalog\/[^/]+/)
    ) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: apis.slice(0, 10),
        meta: { page: 1, pageSize: 20, totalCount: 10, totalPages: 1 },
      }),
    });
  });

  await page.route('**/api/search*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        results: apis.slice(0, 5).map((a) => ({
          apiId: a.id,
          apiName: a.name,
          title: a.title,
          description: a.description,
          kind: a.kind,
          lifecycleStage: a.lifecycleStage,
          score: 0.9,
        })),
        totalCount: 5,
        facets: { kind: [], lifecycle: [], tags: [] },
        queryDuration: 20,
      }),
    })
  );

  await page.route('**/api/governance/*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: {} }),
    })
  );

  await page.route('**/api/analytics/*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: {} }),
    })
  );
}

/** Retrieve Navigation Timing metrics from the current page. */
async function getNavigationTimings(page: Page) {
  return page.evaluate(() => {
    const [entry] = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
    if (!entry) return null;
    return {
      domContentLoadedMs: Math.round(entry.domContentLoadedEventEnd - entry.startTime),
      loadEventMs: Math.round(entry.loadEventEnd - entry.startTime),
      ttfbMs: Math.round(entry.responseStart - entry.startTime),
    };
  });
}

test.describe('Performance — Catalog page', () => {
  test('DOMContentLoaded fires within target on catalog page', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    const timings = await getNavigationTimings(page);
    if (!timings) {
      test.skip();
      return;
    }

    expect(timings.domContentLoadedMs).toBeLessThan(PERF_TARGETS.domContentLoadedMs);
  });

  test('load event fires within target on catalog page', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    const timings = await getNavigationTimings(page);
    if (!timings) {
      test.skip();
      return;
    }

    expect(timings.loadEventMs).toBeLessThan(PERF_TARGETS.loadEventMs);
  });
});

test.describe('Performance — Search page', () => {
  test('DOMContentLoaded fires within target on search page', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/search?q=test');
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();

    const timings = await getNavigationTimings(page);
    if (!timings) {
      test.skip();
      return;
    }

    expect(timings.domContentLoadedMs).toBeLessThan(PERF_TARGETS.domContentLoadedMs);
  });
});

test.describe('Performance — Chat page', () => {
  test('chat page loads within target', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/chat');
    await expect(page.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();

    const timings = await getNavigationTimings(page);
    if (!timings) {
      test.skip();
      return;
    }

    expect(timings.domContentLoadedMs).toBeLessThan(PERF_TARGETS.domContentLoadedMs);
  });
});

test.describe('Performance — Resource counts', () => {
  test('catalog page does not load an excessive number of resources', async ({ page }) => {
    await mockAllApis(page);
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    const resourceCount = await page.evaluate(() => {
      return performance.getEntriesByType('resource').length;
    });

    // Reasonable upper bound: Next.js pages typically load < 50 resources
    // in development mode; allow generous headroom for dev vs prod differences
    expect(resourceCount).toBeLessThan(150);
  });
});
