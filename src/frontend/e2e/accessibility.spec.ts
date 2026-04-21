/**
 * Accessibility E2E tests using axe-core via @axe-core/playwright.
 *
 * These tests check each major page for WCAG 2.1 AA accessibility violations.
 * The goal is zero critical/serious violations across all routes.
 *
 * Pages are tested against mocked API responses so the tests run without a
 * real backend, consistent with the rest of the E2E suite.
 */

import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Standard set of axe rules to run (WCAG 2.1 AA). */
const AXE_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

/** Run axe on the current page and assert zero critical/serious violations. */
async function checkAccessibility(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(AXE_TAGS)
    .analyze();

  const critical = results.violations.filter((v) => v.impact === 'critical');
  const serious = results.violations.filter((v) => v.impact === 'serious');

  const failures = [...critical, ...serious];

  if (failures.length > 0) {
    const msg = failures
      .map(
        (v) =>
          `[${v.impact}] ${v.id}: ${v.description}\n  Nodes: ${v.nodes
            .slice(0, 3)
            .map((n) => n.html)
            .join(', ')}`
      )
      .join('\n\n');
    throw new Error(`axe found ${failures.length} critical/serious violation(s):\n${msg}`);
  }
}

/** Minimal catalog mock — reused across tests that just need the page to load. */
async function mockCatalogApi(page: Page) {
  await page.route('**/api/catalog*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: Array.from({ length: 3 }, (_, i) => ({
          id: `api-${i + 1}`,
          name: `api-${i + 1}`,
          title: `Test API ${i + 1}`,
          description: `Description for test API ${i + 1}`,
          kind: 'rest',
          lifecycleStage: 'production',
          versions: [{ id: 'v1', name: 'v1', title: 'v1', lifecycleStage: 'production', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }],
          deployments: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        })),
        meta: { page: 1, pageSize: 10, totalCount: 3, totalPages: 1 },
      }),
    })
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Accessibility — catalog page', () => {
  test('has no critical/serious axe violations', async ({ page }) => {
    await mockCatalogApi(page);
    await page.goto('/catalog');
    // Wait for catalog content to render
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await checkAccessibility(page);
  });
});

test.describe('Accessibility — search page', () => {
  test('has no critical/serious axe violations', async ({ page }) => {
    await mockCatalogApi(page);
    await page.route('**/api/search*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          results: [],
          totalCount: 0,
          facets: {
            kind: [],
            lifecycle: [],
            tags: [],
          },
          queryDuration: 10,
        }),
      })
    );
    await page.goto('/search');
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();
    await checkAccessibility(page);
  });
});

test.describe('Accessibility — not found page', () => {
  test('has no critical/serious axe violations', async ({ page }) => {
    await mockCatalogApi(page);
    await page.goto('/this-page-does-not-exist');
    await expect(page.getByRole('heading', { name: /not found/i })).toBeVisible();
    await checkAccessibility(page);
  });
});

test.describe('Accessibility — skip-to-content link', () => {
  test('skip-to-content link is present and targets main content', async ({ page }) => {
    await mockCatalogApi(page);
    await page.goto('/catalog');

    // The skip link should be in the DOM (even if visually hidden)
    const skipLink = page.locator('a.skip-to-content');
    await expect(skipLink).toBeAttached();
    await expect(skipLink).toHaveAttribute('href', '#main-content');

    // The main landmark should have id="main-content"
    const main = page.locator('#main-content');
    await expect(main).toBeAttached();
  });

  test('skip-to-content link is the first focusable element', async ({ page }) => {
    await mockCatalogApi(page);
    await page.goto('/catalog');

    // Tab once from the top of the page — the skip link should receive focus first
    await page.keyboard.press('Tab');
    const focused = page.locator(':focus');
    await expect(focused).toHaveAttribute('href', '#main-content');
  });
});
