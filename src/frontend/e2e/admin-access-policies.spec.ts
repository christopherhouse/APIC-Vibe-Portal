/**
 * E2E tests for the Admin — API Access Policies UI.
 *
 * Uses page.route() to mock the BFF admin endpoints and
 * page.addInitScript() to inject a mock Portal.Admin user so the
 * sidebar admin nav and page content render correctly without a live
 * Entra ID session.
 *
 * Screenshots are captured at key points:
 *  - Sidebar with Admin section visible (admin user)
 *  - Sidebar without Admin section (regular user)
 *  - Access Policies page — empty state
 *  - Access Policies page — populated table
 *  - New Policy dialog — open
 *  - Edit Policy dialog — pre-populated
 *  - Delete confirmation dialog
 *  - Access Denied view (non-admin)
 */

import { test, expect, type Page } from '@playwright/test';
import type { AccessPolicy } from '../../lib/admin-api';
import * as path from 'node:path';
import * as fs from 'node:fs';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

const ADMIN_USER: AuthUser = {
  name: 'Alice Admin',
  email: 'alice@contoso.com',
  id: 'user-admin-1',
  roles: ['Portal.Admin'],
};

const REGULAR_USER: AuthUser = {
  name: 'Bob Developer',
  email: 'bob@contoso.com',
  id: 'user-dev-1',
  roles: ['Portal.User'],
};

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_POLICIES: AccessPolicy[] = [
  {
    apiName: 'petstore-api',
    apiId: 'api-1',
    allowedGroups: ['aad-group-platform-engineers', 'aad-group-api-consumers'],
    isPublic: false,
    createdAt: '2026-01-15T10:00:00Z',
    updatedAt: '2026-03-20T14:30:00Z',
  },
  {
    apiName: 'weather-api',
    apiId: 'api-2',
    allowedGroups: [],
    isPublic: true,
    createdAt: '2026-02-01T08:00:00Z',
    updatedAt: '2026-02-01T08:00:00Z',
  },
  {
    apiName: 'internal-hr-api',
    apiId: 'api-3',
    allowedGroups: ['aad-group-hr-team'],
    isPublic: false,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  },
  {
    apiName: 'locked-api',
    apiId: 'api-4',
    allowedGroups: [],
    isPublic: false,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-02T00:00:00Z',
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Screenshot directory — /tmp so it isn't committed */
const SCREENSHOT_DIR = path.join('/tmp', 'admin-ui-screenshots');

/** Ensure screenshot directory exists */
function ensureScreenshotDir() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

/** Full path for a named screenshot */
function screenshotPath(name: string): string {
  return path.join(SCREENSHOT_DIR, `${name}.png`);
}

/** Inject a mock AuthUser into the page before it loads. */
async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

/** Mock the BFF /api/catalog endpoint (needed so the app shell loads cleanly). */
async function mockCatalogRoute(page: Page) {
  await page.route('**/api/catalog*', async (route) => {
    const url = route.request().url();
    // Only intercept list requests, not detail
    if (!url.includes('/api/catalog/')) {
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

/** Mock all admin access-policy BFF routes. */
async function mockAdminRoutes(
  page: Page,
  policies: AccessPolicy[] = MOCK_POLICIES
) {
  // GET /api/admin/access-policies → list
  await page.route('**/api/admin/access-policies', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(policies),
      });
    } else {
      await route.continue();
    }
  });

  // PUT /api/admin/access-policies/:name → upsert
  await page.route('**/api/admin/access-policies/**', async (route) => {
    const method = route.request().method();
    if (method === 'PUT') {
      const url = route.request().url();
      const apiName = decodeURIComponent(url.split('/api/admin/access-policies/')[1]);
      const body = JSON.parse(route.request().postData() ?? '{}') as Partial<AccessPolicy>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          apiName,
          apiId: '',
          allowedGroups: body.allowedGroups ?? [],
          isPublic: body.isPublic ?? false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }),
      });
    } else if (method === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else {
      await route.continue();
    }
  });

  // POST /api/admin/access-policies/cache/invalidate
  await page.route('**/api/admin/access-policies/cache/invalidate', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
}

// ---------------------------------------------------------------------------
// Tests: Sidebar RBAC
// ---------------------------------------------------------------------------

test.describe('Sidebar RBAC — Admin section visibility', () => {
  test('admin user sees Admin nav section in sidebar', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    // Wait for the page to load
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    // Admin section should be visible
    const adminSection = page.getByRole('navigation', { name: /admin navigation/i });
    await expect(adminSection).toBeVisible();
    await expect(page.getByRole('link', { name: /access policies/i })).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: screenshotPath('sidebar-admin-user'), fullPage: false });
    console.log(`Screenshot saved: ${screenshotPath('sidebar-admin-user')}`);
  });

  test('regular user does NOT see Admin nav section in sidebar', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, REGULAR_USER);
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    // Admin section should NOT be visible
    await expect(page.getByRole('navigation', { name: /admin navigation/i })).not.toBeVisible();
    await expect(page.getByRole('link', { name: /access policies/i })).not.toBeVisible();

    // Take screenshot
    await page.screenshot({ path: screenshotPath('sidebar-regular-user'), fullPage: false });
    console.log(`Screenshot saved: ${screenshotPath('sidebar-regular-user')}`);
  });

  test('unauthenticated / no-MSAL user does NOT see Admin section', async ({ page }) => {
    ensureScreenshotDir();
    // No mock user → user is null → no admin section
    await mockCatalogRoute(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /access policies/i })).not.toBeVisible();

    await page.screenshot({ path: screenshotPath('sidebar-no-user'), fullPage: false });
    console.log(`Screenshot saved: ${screenshotPath('sidebar-no-user')}`);
  });
});

// ---------------------------------------------------------------------------
// Tests: Access Denied (non-admin visiting /admin/access-policies)
// ---------------------------------------------------------------------------

test.describe('Access Denied — non-admin visiting admin page', () => {
  test('regular user sees Access Denied when visiting /admin/access-policies', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, REGULAR_USER);
    await page.goto('/admin/access-policies');

    await expect(page.getByText(/access denied/i)).toBeVisible();
    await expect(page.getByText(/Portal\.Admin/)).toBeVisible();

    await page.screenshot({ path: screenshotPath('access-denied-regular-user'), fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath('access-denied-regular-user')}`);
  });

  test('unauthenticated user sees Access Denied', async ({ page }) => {
    ensureScreenshotDir();
    await page.goto('/admin/access-policies');

    await expect(page.getByText(/access denied/i)).toBeVisible();

    await page.screenshot({ path: screenshotPath('access-denied-no-user'), fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath('access-denied-no-user')}`);
  });
});

// ---------------------------------------------------------------------------
// Tests: Admin page — empty state
// ---------------------------------------------------------------------------

test.describe('Admin Access Policies — empty state', () => {
  test('shows empty state and action buttons when no policies exist', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, []);

    await page.goto('/admin/access-policies');

    await expect(page.getByText('API Access Policies')).toBeVisible();
    await expect(page.getByTestId('add-policy-button')).toBeVisible();
    await expect(page.getByTestId('refresh-cache-button')).toBeVisible();
    await expect(page.getByTestId('policies-empty-state')).toBeVisible();
    await expect(page.getByText(/No access policies configured/i)).toBeVisible();

    await page.screenshot({ path: screenshotPath('admin-page-empty-state'), fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath('admin-page-empty-state')}`);
  });
});

// ---------------------------------------------------------------------------
// Tests: Admin page — populated table
// ---------------------------------------------------------------------------

test.describe('Admin Access Policies — populated table', () => {
  test('shows policy table with all rows when policies exist', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, MOCK_POLICIES);

    await page.goto('/admin/access-policies');

    await expect(page.getByText('API Access Policies')).toBeVisible();
    await expect(page.getByTestId('policies-table')).toBeVisible();

    // Verify all policy rows are shown
    await expect(page.getByTestId('policy-row-petstore-api')).toBeVisible();
    await expect(page.getByTestId('policy-row-weather-api')).toBeVisible();
    await expect(page.getByTestId('policy-row-internal-hr-api')).toBeVisible();
    await expect(page.getByTestId('policy-row-locked-api')).toBeVisible();

    // Verify chips — use first() to avoid strict mode failure when multiple match
    await expect(page.getByText('Public').first()).toBeVisible();
    await expect(page.getByText('Restricted').first()).toBeVisible();

    await page.screenshot({ path: screenshotPath('admin-page-table'), fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath('admin-page-table')}`);
  });

  test('petstore-api row shows group OID chips', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, MOCK_POLICIES);

    await page.goto('/admin/access-policies');
    await expect(page.getByTestId('policies-table')).toBeVisible();

    await expect(page.getByText('aad-group-platform-engineers')).toBeVisible();
    await expect(page.getByText('aad-group-api-consumers')).toBeVisible();

    // Zoom in on the petstore row
    const row = page.getByTestId('policy-row-petstore-api');
    await row.screenshot({ path: screenshotPath('policy-row-petstore') });
    console.log(`Screenshot saved: ${screenshotPath('policy-row-petstore')}`);
  });

  test('locked-api row shows inaccessible warning', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, MOCK_POLICIES);

    await page.goto('/admin/access-policies');
    await expect(page.getByTestId('policies-table')).toBeVisible();

    await expect(page.getByText(/No groups — API inaccessible/)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Tests: New Policy dialog
// ---------------------------------------------------------------------------

test.describe('New Policy dialog', () => {
  test('opens create dialog when New Policy button is clicked', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, []);

    await page.goto('/admin/access-policies');
    await expect(page.getByTestId('add-policy-button')).toBeVisible();

    await page.getByTestId('add-policy-button').click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('New Access Policy')).toBeVisible();

    await page.screenshot({ path: screenshotPath('dialog-new-policy-empty'), fullPage: false });
    console.log(`Screenshot saved: ${screenshotPath('dialog-new-policy-empty')}`);
  });

  test('new policy dialog with API name and group filled in', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, []);

    await page.goto('/admin/access-policies');
    await page.getByTestId('add-policy-button').click();
    await expect(page.getByRole('dialog')).toBeVisible();

    // Fill in API name
    await page.getByTestId('api-name-input').fill('my-new-api');

    // Add two groups
    await page.getByTestId('group-oid-input').fill('aad-group-developers');
    await page.getByTestId('add-group-button').click();
    await page.getByTestId('group-oid-input').fill('aad-group-qa-team');
    await page.getByTestId('add-group-button').click();

    await expect(page.getByTestId('group-chip-aad-group-developers')).toBeVisible();
    await expect(page.getByTestId('group-chip-aad-group-qa-team')).toBeVisible();

    await page.screenshot({ path: screenshotPath('dialog-new-policy-filled'), fullPage: false });
    console.log(`Screenshot saved: ${screenshotPath('dialog-new-policy-filled')}`);
  });

  test('new policy dialog with isPublic toggled on', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, []);

    await page.goto('/admin/access-policies');
    await page.getByTestId('add-policy-button').click();
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.getByTestId('api-name-input').fill('my-public-api');
    // Toggle isPublic switch — use role=switch since MUI renders an <input role="switch">
    const publicSwitch = page.getByRole('switch');
    await publicSwitch.click();

    // Group section should now be hidden (isPublic = true)
    await expect(page.getByTestId('group-oid-input')).not.toBeVisible();

    await page.screenshot({ path: screenshotPath('dialog-new-policy-public'), fullPage: false });
    console.log(`Screenshot saved: ${screenshotPath('dialog-new-policy-public')}`);
  });

  test('saving a new policy refreshes the table', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);

    const policies = [...MOCK_POLICIES];

    // First load: empty
    await page.route('**/api/admin/access-policies', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(policies),
        });
      } else {
        await route.continue();
      }
    });
    await mockAdminRoutes(page, policies);

    await page.goto('/admin/access-policies');
    await expect(page.getByTestId('policies-table')).toBeVisible();

    await page.getByTestId('add-policy-button').click();
    await page.getByTestId('api-name-input').fill('brand-new-api');
    await page.getByTestId('save-policy-button').click();

    // After save, dialog should close and table should remain
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('policies-table')).toBeVisible();

    await page.screenshot({ path: screenshotPath('after-save-policy'), fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath('after-save-policy')}`);
  });
});

// ---------------------------------------------------------------------------
// Tests: Edit Policy dialog
// ---------------------------------------------------------------------------

test.describe('Edit Policy dialog', () => {
  test('clicking Edit opens pre-populated dialog', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, MOCK_POLICIES);

    await page.goto('/admin/access-policies');
    await expect(page.getByTestId('policies-table')).toBeVisible();

    // Click edit on petstore-api
    await page.getByTestId('edit-policy-petstore-api').click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Edit Policy: petstore-api')).toBeVisible();

    // Groups should be pre-populated
    await expect(page.getByTestId('group-chip-aad-group-platform-engineers')).toBeVisible();
    await expect(page.getByTestId('group-chip-aad-group-api-consumers')).toBeVisible();

    // API name field should be disabled
    const apiNameInput = page.getByTestId('api-name-input');
    await expect(apiNameInput).toBeDisabled();

    await page.screenshot({ path: screenshotPath('dialog-edit-policy'), fullPage: false });
    console.log(`Screenshot saved: ${screenshotPath('dialog-edit-policy')}`);
  });
});

// ---------------------------------------------------------------------------
// Tests: Delete Policy dialog
// ---------------------------------------------------------------------------

test.describe('Delete Policy dialog', () => {
  test('clicking Delete opens confirmation dialog', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, MOCK_POLICIES);

    await page.goto('/admin/access-policies');
    await expect(page.getByTestId('policies-table')).toBeVisible();

    // Click delete on internal-hr-api
    await page.getByTestId('delete-policy-internal-hr-api').click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Delete Access Policy')).toBeVisible();
    // Use first() to avoid strict mode failure when the api name appears in both table row and dialog
    await expect(page.getByText(/internal-hr-api/).first()).toBeVisible();
    await expect(page.getByTestId('confirm-delete-button')).toBeVisible();

    await page.screenshot({ path: screenshotPath('dialog-delete-policy'), fullPage: false });
    console.log(`Screenshot saved: ${screenshotPath('dialog-delete-policy')}`);
  });

  test('confirming delete closes dialog', async ({ page }) => {
    ensureScreenshotDir();
    await setMockUser(page, ADMIN_USER);
    await mockAdminRoutes(page, MOCK_POLICIES);

    await page.goto('/admin/access-policies');
    await expect(page.getByTestId('policies-table')).toBeVisible();

    await page.getByTestId('delete-policy-weather-api').click();
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.getByTestId('confirm-delete-button').click();
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 });

    await page.screenshot({ path: screenshotPath('after-delete-policy'), fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath('after-delete-policy')}`);
  });
});
