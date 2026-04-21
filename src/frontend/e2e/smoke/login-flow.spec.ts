/**
 * Smoke tests — login flow.
 *
 * Verifies the authentication UI states that can be tested without a live
 * Entra ID tenant.  Uses page.addInitScript() to inject a mock user, which
 * mirrors the mechanism used in the full E2E journey tests.
 */

import { test, expect, type Page } from '@playwright/test';

interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

const SMOKE_USER: AuthUser = {
  name: 'Smoke Tester',
  email: 'smoke@contoso.com',
  id: 'user-smoke-1',
  roles: ['Portal.User'],
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

test.describe('Smoke — Login flow', () => {
  test('unauthenticated: Sign in button is visible', async ({ page }) => {
    await mockCatalog(page);
    await page.goto('/catalog');

    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /user menu/i })).not.toBeVisible();
  });

  test('authenticated: user avatar replaces Sign in button', async ({ page }) => {
    await setMockUser(page, SMOKE_USER);
    await mockCatalog(page);
    await page.goto('/catalog');

    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).not.toBeVisible();
  });

  test('authenticated: user menu shows name, email, and Sign out', async ({ page }) => {
    await setMockUser(page, SMOKE_USER);
    await mockCatalog(page);
    await page.goto('/catalog');

    await page.getByRole('button', { name: /user menu/i }).click();

    await expect(page.getByText(SMOKE_USER.name)).toBeVisible();
    await expect(page.getByText(SMOKE_USER.email)).toBeVisible();
    await expect(page.getByText('Sign out')).toBeVisible();
  });

  test('auth state persists across page navigation', async ({ page }) => {
    await setMockUser(page, SMOKE_USER);
    await mockCatalog(page);
    await page.goto('/catalog');

    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();

    // Navigate to another page
    await page.goto('/chat');
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();
  });
});
