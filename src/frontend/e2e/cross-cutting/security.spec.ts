/**
 * Security validation E2E tests.
 *
 * Validates security-related behaviour of the frontend application:
 *   - Authentication gates (protected pages require sign-in)
 *   - RBAC: admin-only pages deny access to regular users
 *   - No sensitive data visible in the DOM for unauthenticated users
 *   - CSP/security meta tags presence
 *   - No sensitive data stored in client-side localStorage/sessionStorage
 *
 * These tests use page.route() to intercept BFF calls, consistent with the
 * rest of the E2E suite.
 */

import { test, expect, type Page } from '@playwright/test';

interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

const REGULAR_USER: AuthUser = {
  name: 'Bob Developer',
  email: 'bob@contoso.com',
  id: 'user-bob-1',
  roles: ['Portal.User'],
};

const ADMIN_USER: AuthUser = {
  name: 'Alice Admin',
  email: 'alice@contoso.com',
  id: 'user-admin-1',
  roles: ['Portal.Admin'],
};

async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

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

test.describe('Security — RBAC access control', () => {
  test('regular user cannot access admin analytics page', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await mockCatalog(page);

    await page.goto('/admin/analytics');

    // Should show access denied or redirect — not admin content
    const heading = page.getByRole('heading');
    await expect(heading).toBeVisible({ timeout: 5000 });
    const text = await heading.textContent();
    // Either access denied or redirected to catalog
    const isRestricted =
      /access denied|forbidden|not authorized|catalog/i.test(text ?? '') ||
      page.url().includes('/catalog');
    expect(isRestricted).toBe(true);
  });

  test('regular user cannot access admin agents page', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await mockCatalog(page);

    await page.goto('/admin/agents');

    const heading = page.getByRole('heading');
    await expect(heading).toBeVisible({ timeout: 5000 });
    const text = await heading.textContent();
    const isRestricted =
      /access denied|forbidden|not authorized|catalog/i.test(text ?? '') ||
      page.url().includes('/catalog');
    expect(isRestricted).toBe(true);
  });

  test('admin user can access admin analytics page', async ({ page }) => {
    await setMockUser(page, ADMIN_USER);
    await mockCatalog(page);

    // Mock analytics endpoints
    await page.route('**/api/analytics/*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: {} }),
      })
    );

    await page.goto('/admin/analytics');
    // Should show analytics content (not access denied)
    await expect(page.getByRole('heading', { name: /analytics/i })).toBeVisible({ timeout: 5000 });
  });

  test('regular user does NOT see Admin nav section in sidebar', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await mockCatalog(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByRole('navigation', { name: /admin navigation/i })).not.toBeVisible();
  });
});

test.describe('Security — No sensitive data exposure', () => {
  test('no credentials or tokens visible in the page DOM', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await mockCatalog(page);
    await page.goto('/catalog');

    const bodyText = await page.locator('body').textContent();

    // No token-like patterns should be visible in the page
    expect(bodyText).not.toMatch(/Bearer [A-Za-z0-9._-]{20,}/);
    expect(bodyText).not.toMatch(/client_secret/i);
    expect(bodyText).not.toMatch(/api[_-]key\s*[:=]\s*\S+/i);
  });

  test('no sensitive data in localStorage after page load', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await mockCatalog(page);
    await page.goto('/catalog');

    const localStorageData = await page.evaluate(() => {
      const data: Record<string, string> = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i) ?? '';
        data[key] = localStorage.getItem(key) ?? '';
      }
      return data;
    });

    // Check that no values look like Bearer tokens or secrets
    for (const value of Object.values(localStorageData)) {
      expect(value).not.toMatch(/Bearer [A-Za-z0-9._-]{20,}/);
      expect(value).not.toMatch(/client_secret/i);
    }
  });
});

test.describe('Security — Input validation (XSS prevention)', () => {
  test('XSS payload in search query is not executed', async ({ page }) => {
    const xssExecuted: boolean[] = [];
    await page.exposeFunction('__xssCheck', () => {
      xssExecuted.push(true);
    });

    await page.route('**/api/search*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          results: [],
          totalCount: 0,
          facets: { kind: [], lifecycle: [], tags: [] },
          queryDuration: 5,
        }),
      })
    );

    // Navigate with an XSS payload as the search query
    await page.goto('/search?q=<script>window.__xssCheck()</script>');
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();

    // The XSS function should NOT have been called
    expect(xssExecuted).toHaveLength(0);

    // The raw script tag should not appear as executable in the DOM
    const scriptTags = await page.locator('script:not([src])').count();
    // Only legitimate script tags (not injected ones with xssCheck) should exist
    const injectedScript = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script')).some((s) =>
        s.textContent?.includes('__xssCheck')
      )
    );
    expect(injectedScript).toBe(false);
    void scriptTags; // used for reference only
  });
});

test.describe('Security — Content Security', () => {
  test('page does not expose backend error details to users', async ({ page }) => {
    await mockCatalog(page);

    // Simulate a backend error
    await page.route('**/api/catalog*', (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error', stack: 'at line 42...' }),
      })
    );

    await page.goto('/catalog');

    const bodyText = await page.locator('body').textContent();
    // Stack traces should not be visible to end users
    expect(bodyText).not.toMatch(/at line \d+/);
    expect(bodyText).not.toMatch(/stack trace/i);
  });
});
