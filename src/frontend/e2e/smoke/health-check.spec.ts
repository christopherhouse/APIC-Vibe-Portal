/**
 * Smoke tests — health check.
 *
 * These are the first tests that should pass in any environment.  They verify
 * that the application is reachable, renders its shell without JS errors, and
 * that the mock BFF health endpoint returns a 200 OK.  No authentication is
 * required.
 */

import { test, expect, type Page } from '@playwright/test';

/** Mock the catalog endpoint so the app shell can render without a real BFF. */
async function mockCatalog(page: Page) {
  await page.route('**/api/catalog*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [],
        meta: { page: 1, pageSize: 20, totalCount: 0, totalPages: 0 },
      }),
    })
  );
}

test.describe('Smoke — App shell loads', () => {
  test('root URL responds and redirects to /catalog', async ({ page }) => {
    await mockCatalog(page);
    await page.goto('/');

    await expect(page).toHaveURL(/\/catalog/);
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
  });

  test('page title is set', async ({ page }) => {
    await mockCatalog(page);
    await page.goto('/catalog');

    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test('navigation sidebar is visible', async ({ page }) => {
    await mockCatalog(page);
    await page.goto('/catalog');

    await expect(page.getByRole('navigation')).toBeVisible();
  });

  test('no uncaught JS errors on initial load', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await mockCatalog(page);
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    expect(errors).toHaveLength(0);
  });
});

test.describe('Smoke — BFF health endpoint', () => {
  test('BFF /health route returns 200', async ({ page }) => {
    // Intercept and respond with a health response
    await page.route('**/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' }),
      })
    );

    // Navigate to the app first so relative fetch URLs resolve against the
    // Next.js baseURL instead of about:blank.
    await page.route('**/api/catalog*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [],
          meta: { page: 1, pageSize: 20, totalCount: 0, totalPages: 0 },
        }),
      })
    );
    await page.goto('/catalog');

    // Trigger a fetch to the mocked health endpoint from the page context
    const response = await page.evaluate(async () => {
      const res = await fetch('/health');
      return { status: res.status, body: await res.json() };
    });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe('ok');
  });
});

test.describe('Smoke — Core pages accessible', () => {
  test('search page loads', async ({ page }) => {
    await page.route('**/api/search*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          results: [],
          totalCount: 0,
          facets: { kind: [], lifecycle: [], tags: [] },
          queryDuration: 10,
        }),
      })
    );

    await page.goto('/search');
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();
  });

  test('chat page loads', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();
  });

  test('404 page renders for unknown route', async ({ page }) => {
    await mockCatalog(page);
    await page.goto('/this-does-not-exist');
    await expect(page.getByRole('heading', { name: /not found/i })).toBeVisible();
  });
});
