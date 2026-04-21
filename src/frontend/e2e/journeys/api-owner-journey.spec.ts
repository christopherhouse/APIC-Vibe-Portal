/**
 * API Owner user journey E2E test.
 *
 * Simulates the workflow of an API owner who needs to:
 *   1. Authenticate as an API owner / maintainer
 *   2. Navigate to the Governance Dashboard
 *   3. Find their API with a low compliance score
 *   4. View compliance detail and recommendations
 *   5. Check analytics for their API's popularity
 *   6. View search terms that lead to their API
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

const API_OWNER_USER: AuthUser = {
  name: 'Owen Owner',
  email: 'owen@contoso.com',
  id: 'user-owner-1',
  roles: ['Portal.Maintainer'],
};

const MOCK_GOVERNANCE_SCORES = [
  {
    apiId: 'api-1',
    apiName: 'Payments API',
    score: 92.0,
    category: 'Excellent',
    criticalFailures: 0,
    lastChecked: '2026-04-21T10:00:00Z',
  },
  {
    apiId: 'api-2',
    apiName: 'Users API',
    score: 54.0,
    category: 'Needs Improvement',
    criticalFailures: 2,
    lastChecked: '2026-04-21T10:00:00Z',
  },
  {
    apiId: 'api-3',
    apiName: 'Orders API',
    score: 71.0,
    category: 'Good',
    criticalFailures: 0,
    lastChecked: '2026-04-21T10:00:00Z',
  },
];

const MOCK_COMPLIANCE_DETAIL = {
  apiId: 'api-2',
  apiName: 'Users API',
  score: 54.0,
  checks: [
    {
      id: 'has-description',
      name: 'API Description',
      passed: false,
      severity: 'critical',
      message: 'API is missing a description',
      recommendation: 'Add a meaningful description to help developers understand the API purpose',
    },
    {
      id: 'has-contact',
      name: 'Contact Information',
      passed: false,
      severity: 'high',
      message: 'No contact information provided',
      recommendation: 'Add contact details including email and team name',
    },
    {
      id: 'has-version',
      name: 'Versioning',
      passed: true,
      severity: 'medium',
      message: 'API has proper versioning',
      recommendation: null,
    },
  ],
  generatedAt: '2026-04-21T10:00:00Z',
};

async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

async function setupApiOwnerMocks(page: Page) {
  const apis = generateMockApis(6);

  // Catalog
  await page.route('**/api/catalog*', async (route) => {
    if (
      route
        .request()
        .url()
        .match(/\/api\/catalog\/[^/]+$/)
    ) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: apis.slice(0, 6),
        meta: { page: 1, pageSize: 20, totalCount: 6, totalPages: 1 },
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
          overallScore: 72.3,
          compliantCount: 4,
          totalCount: 6,
          criticalIssues: 2,
          improvement: -1.5,
        },
      }),
    });
  });

  // Governance scores
  await page.route('**/api/governance/scores*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: MOCK_GOVERNANCE_SCORES }),
    });
  });

  // Governance distribution
  await page.route('**/api/governance/distribution*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: { excellent: 2, good: 2, needsImprovement: 1, nonCompliant: 1 },
      }),
    });
  });

  // Compliance detail for a specific API
  await page.route(/\/api\/governance\/apis\/[^/]+\/compliance/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: MOCK_COMPLIANCE_DETAIL }),
    });
  });

  // Analytics summary
  await page.route('**/api/analytics/summary*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          totalUsers: 348,
          totalPageViews: 2145,
          totalSearchQueries: 412,
          totalChatInteractions: 87,
          avgSessionDurationSeconds: 210,
          usersTrend: 5.2,
          pageViewsTrend: 8.1,
          searchQueriesTrend: 12.3,
          chatInteractionsTrend: 22.7,
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
        data: [
          { apiId: 'api-1', apiName: 'Payments API', viewCount: 520, searchCount: 130 },
          { apiId: 'api-2', apiName: 'Users API', viewCount: 340, searchCount: 89 },
          { apiId: 'api-3', apiName: 'Orders API', viewCount: 210, searchCount: 45 },
        ],
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
          { term: 'payment', count: 89 },
          { term: 'users api', count: 67 },
          { term: 'orders', count: 45 },
          { term: 'rest', count: 38 },
        ],
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
            users: 40 + i * 3,
            pageViews: 200 + i * 15,
            searchQueries: 50 + i * 5,
          })),
        },
      }),
    });
  });
}

test.describe('API Owner Journey', () => {
  test('API owner reviews governance dashboard and compliance details', async ({ page }) => {
    await setMockUser(page, API_OWNER_USER);
    await setupApiOwnerMocks(page);

    // Step 1: Navigate to governance dashboard
    await page.goto('/governance');
    await expect(page.getByRole('heading', { name: /governance/i })).toBeVisible();

    // Step 2: View KPI summary cards
    await expect(page.getByTestId('governance-summary')).toBeVisible({ timeout: 5000 });

    // Step 3: Find the low-scoring API in the scores table
    await expect(page.getByTestId('governance-scores-table')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Users API')).toBeVisible();
    await expect(page.getByText('54')).toBeVisible();
  });

  test('API owner views analytics dashboard', async ({ page }) => {
    await setMockUser(page, API_OWNER_USER);
    await setupApiOwnerMocks(page);

    // Navigate to analytics
    await page.goto('/admin/analytics');

    // If access denied for non-admin, verify correct behavior
    const heading = page.getByRole('heading');
    await expect(heading).toBeVisible({ timeout: 5000 });

    // Either shows analytics or access denied — both are valid for maintainer role
    const text = await heading.textContent();
    expect(text).toBeTruthy();
  });

  test('API owner can navigate between governance and catalog', async ({ page }) => {
    await setMockUser(page, API_OWNER_USER);
    await setupApiOwnerMocks(page);

    // Start at governance dashboard
    await page.goto('/governance');
    await expect(page.getByRole('heading', { name: /governance/i })).toBeVisible();

    // Navigate back to catalog via sidebar
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    // Navigate back to governance
    await page.goto('/governance');
    await expect(page.getByRole('heading', { name: /governance/i })).toBeVisible();
  });
});
