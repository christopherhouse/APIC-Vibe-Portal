/**
 * Admin user journey E2E test.
 *
 * Simulates the workflow of a portal administrator who needs to:
 *   1. Authenticate as an admin (Portal.Admin role)
 *   2. View the analytics dashboard
 *   3. Check portal usage trends
 *   4. Navigate to agent management
 *   5. Review search analytics
 *   6. Check the governance overview
 *
 * All BFF calls are intercepted with page.route().
 */

import { test, expect, type Page } from '@playwright/test';
import { generateMockApis } from '../mock-server';

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

async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

async function setupAdminMocks(page: Page) {
  const apis = generateMockApis(10);

  // Catalog
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

  // Analytics summary
  await page.route('**/api/analytics/summary*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          totalUsers: 1234,
          totalPageViews: 5678,
          totalSearchQueries: 910,
          totalChatInteractions: 234,
          avgSessionDurationSeconds: 185,
          usersTrend: 12.5,
          pageViewsTrend: -3.2,
          searchQueriesTrend: 0,
          chatInteractionsTrend: 20.1,
        },
      }),
    });
  });

  // Analytics trends
  await page.route('**/api/analytics/trends*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          range: '30d',
          dataPoints: Array.from({ length: 7 }, (_, i) => ({
            date: new Date(2026, 3, 15 + i).toISOString().slice(0, 10),
            users: 50 + i * 5,
            pageViews: 250 + i * 20,
            searchQueries: 60 + i * 6,
          })),
        },
      }),
    });
  });

  // Analytics top APIs
  await page.route('**/api/analytics/top-apis*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: apis.slice(0, 5).map((a, i) => ({
          apiId: a.id,
          apiName: a.title,
          viewCount: 500 - i * 70,
          searchCount: 150 - i * 20,
        })),
      }),
    });
  });

  // Analytics search terms
  await page.route('**/api/analytics/search-terms*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          { term: 'payment api', count: 120 },
          { term: 'rest api', count: 95 },
          { term: 'graphql', count: 78 },
          { term: 'orders', count: 62 },
          { term: 'users', count: 55 },
        ],
      }),
    });
  });

  // Admin agents
  await page.route('**/api/admin/agents', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        agents: [
          {
            id: 'governance-agent',
            name: 'Governance Agent',
            description: 'Analyzes API governance and compliance',
            status: 'active',
            model: 'gpt-4o',
            lastUpdated: '2026-04-21T10:00:00Z',
          },
          {
            id: 'search-agent',
            name: 'Search Agent',
            description: 'Handles semantic search queries',
            status: 'active',
            model: 'gpt-4o-mini',
            lastUpdated: '2026-04-20T14:00:00Z',
          },
        ],
      }),
    });
  });

  // Governance summary
  await page.route('**/api/governance/summary', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          overallScore: 82.5,
          compliantCount: 7,
          totalCount: 10,
          criticalIssues: 1,
          improvement: 2.0,
        },
      }),
    });
  });

  await page.route('**/api/governance/scores*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: apis.slice(0, 5).map((a, i) => ({
          apiId: a.id,
          apiName: a.title,
          score: 90 - i * 7,
          category: i === 0 ? 'Excellent' : 'Good',
          criticalFailures: i === 4 ? 1 : 0,
          lastChecked: new Date().toISOString(),
        })),
      }),
    });
  });

  await page.route('**/api/governance/distribution*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: { excellent: 4, good: 3, needsImprovement: 2, nonCompliant: 1 },
      }),
    });
  });
}

test.describe('Admin Journey', () => {
  test('admin can see admin navigation section', async ({ page }) => {
    await setMockUser(page, ADMIN_USER);
    await setupAdminMocks(page);

    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    // Admin navigation section should be visible
    await expect(page.getByRole('navigation', { name: /admin navigation/i })).toBeVisible();
  });

  test('admin views analytics dashboard', async ({ page }) => {
    await setMockUser(page, ADMIN_USER);
    await setupAdminMocks(page);

    await page.goto('/analytics');
    await expect(page.getByRole('heading', { name: /analytics/i })).toBeVisible({ timeout: 5000 });

    // KPI cards should be visible
    await expect(page.getByTestId('analytics-summary')).toBeVisible({ timeout: 5000 });
  });

  test('admin views agent management page', async ({ page }) => {
    await setMockUser(page, ADMIN_USER);
    await setupAdminMocks(page);

    await page.goto('/admin/agents');
    await expect(page.getByRole('heading', { name: /agent/i })).toBeVisible({ timeout: 5000 });
  });

  test('admin views governance overview', async ({ page }) => {
    await setMockUser(page, ADMIN_USER);
    await setupAdminMocks(page);

    await page.goto('/governance');
    await expect(page.getByRole('heading', { name: /governance/i })).toBeVisible();
    await expect(page.getByTestId('governance-summary')).toBeVisible({ timeout: 5000 });
  });

  test('admin can navigate across all major sections', async ({ page }) => {
    await setMockUser(page, ADMIN_USER);
    await setupAdminMocks(page);

    // Start at catalog
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    // Go to governance
    await page.goto('/governance');
    await expect(page.getByRole('heading', { name: /governance/i })).toBeVisible();

    // Go to analytics
    await page.goto('/analytics');
    await expect(page.getByRole('heading', { name: /analytics/i })).toBeVisible({ timeout: 5000 });

    // Go to agent management
    await page.goto('/admin/agents');
    await expect(page.getByRole('heading', { name: /agent/i })).toBeVisible({ timeout: 5000 });

    // Return to catalog
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
  });
});
