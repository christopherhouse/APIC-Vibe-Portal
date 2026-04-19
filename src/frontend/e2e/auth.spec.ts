/**
 * E2E tests for authentication UI flows.
 *
 * Since Entra ID authentication requires a live Azure AD tenant, these tests
 * exercise the authentication UI using Playwright's page.addInitScript() to
 * inject a mock AuthUser — the same mechanism used by the admin e2e tests and
 * documented in src/frontend/lib/auth/use-auth.ts.
 *
 * The tests verify:
 *  - Unauthenticated state: "Sign in" button is visible in the header
 *  - Authenticated state: User avatar is shown and user info is accessible
 *  - User menu: User name, email, and "Sign out" are shown in the dropdown
 *  - Access control: Protected pages are accessible when authenticated
 */

import { test, expect, type Page } from '@playwright/test';

interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

const MOCK_USER: AuthUser = {
  name: 'Jane Developer',
  email: 'jane@contoso.com',
  id: 'user-jane-1',
  roles: ['Portal.User'],
};

const MOCK_ADMIN: AuthUser = {
  name: 'Alice Admin',
  email: 'alice@contoso.com',
  id: 'user-alice-1',
  roles: ['Portal.Admin'],
};

/** Inject a mock AuthUser into the page before it loads. */
async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

/** Mock the BFF /api/catalog endpoint so the app shell loads cleanly. */
async function mockCatalogRoute(page: Page) {
  await page.route('**/api/catalog*', async (route) => {
    if (!route.request().url().includes('/api/catalog/')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [],
          meta: { page: 1, pageSize: 20, totalCount: 0, totalPages: 0 },
        }),
      });
    } else {
      await route.continue();
    }
  });
}

// ---------------------------------------------------------------------------
// Unauthenticated state
// ---------------------------------------------------------------------------

test.describe('Authentication — Unauthenticated State', () => {
  test('shows Sign in button in header when not authenticated', async ({ page }) => {
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    // The "Sign in" button should be visible in the header
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('user avatar / user menu is NOT visible when unauthenticated', async ({ page }) => {
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    await expect(page.getByRole('button', { name: /user menu/i })).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Authenticated state
// ---------------------------------------------------------------------------

test.describe('Authentication — Authenticated State', () => {
  test('shows user avatar instead of Sign in when authenticated', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    // User menu button (avatar) should be visible; Sign in should not
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).not.toBeVisible();
  });

  test('user menu displays name, email, and Sign out option', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    // Open the user menu
    await page.getByRole('button', { name: /user menu/i }).click();

    // User info and sign-out should appear in the dropdown
    await expect(page.getByText(MOCK_USER.name)).toBeVisible();
    await expect(page.getByText(MOCK_USER.email)).toBeVisible();
    await expect(page.getByText('Sign out')).toBeVisible();
  });

  test('user initials avatar shows correctly in header', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    // Avatar button should display the user's initials (JD for Jane Developer)
    const avatarButton = page.getByRole('button', { name: /user menu/i });
    await expect(avatarButton).toBeVisible();
    await expect(avatarButton).toContainText('JD');
  });

  test('closing the user menu hides the dropdown', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    // Open the menu
    await page.getByRole('button', { name: /user menu/i }).click();
    await expect(page.getByText('Sign out')).toBeVisible();

    // Press Escape to close
    await page.keyboard.press('Escape');
    await expect(page.getByText('Sign out')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Admin user state
// ---------------------------------------------------------------------------

test.describe('Authentication — Admin User', () => {
  test('admin user sees Admin nav section in sidebar', async ({ page }) => {
    await setMockUser(page, MOCK_ADMIN);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    // Admin section should be present for Portal.Admin role
    const adminNav = page.getByRole('navigation', { name: /admin navigation/i });
    await expect(adminNav).toBeVisible();
  });

  test('regular user does NOT see Admin nav section', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByRole('navigation', { name: /admin navigation/i })).not.toBeVisible();
  });

  test('unauthenticated user does NOT see Admin nav section', async ({ page }) => {
    // No mock user → unauthenticated
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByRole('navigation', { name: /admin navigation/i })).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Protected page access
// ---------------------------------------------------------------------------

test.describe('Authentication — Page Access', () => {
  test('authenticated user can access the catalog page', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
  });

  test('authenticated user can access the chat page', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await page.goto('/chat');

    await expect(page.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();
  });

  test('authenticated user can access the search page', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await page.route('**/api/search', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          results: [],
          totalCount: 0,
          facets: { kind: [], lifecycle: [], tags: [] },
          queryDuration: 10,
        }),
      });
    });
    await page.goto('/search?q=test');

    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();
  });
});
