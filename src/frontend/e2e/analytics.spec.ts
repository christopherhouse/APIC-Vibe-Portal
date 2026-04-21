import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockSummary = {
  totalUsers: 1234,
  totalPageViews: 5678,
  totalSearchQueries: 910,
  totalChatInteractions: 234,
  avgSessionDurationSeconds: 185,
  usersTrend: 12.5,
  pageViewsTrend: -3.2,
  searchQueriesTrend: 0,
  chatInteractionsTrend: 20.1,
};

const mockTrends = {
  range: '30d',
  dataPoints: [
    { date: '2026-03-01', activeUsers: 120, pageViews: 450, searches: 80, chatInteractions: 30 },
    { date: '2026-03-15', activeUsers: 145, pageViews: 510, searches: 95, chatInteractions: 42 },
  ],
};

const mockPopularApis = [
  {
    apiId: 'payments-api',
    apiName: 'Payments API',
    viewCount: 500,
    downloadCount: 120,
    chatMentionCount: 45,
  },
  {
    apiId: 'users-api',
    apiName: 'Users API',
    viewCount: 380,
    downloadCount: 90,
    chatMentionCount: 30,
  },
];

const mockSearchTrends = {
  dailyVolume: [
    { date: '2026-03-01', queryCount: 120, zeroResultCount: 10 },
    { date: '2026-03-02', queryCount: 145, zeroResultCount: 8 },
  ],
  topQueries: [
    { queryHash: 'h1', displayTerm: 'payments api', count: 45, avgResultCount: 8 },
    { queryHash: 'h2', displayTerm: 'authentication', count: 32, avgResultCount: 12 },
  ],
  zeroResultQueries: [{ displayTerm: 'unknown-thing', count: 5 }],
  clickThroughRate: 67.5,
  avgResultsPerSearch: 9.2,
  searchModeDistribution: { keyword: 30, semantic: 50, hybrid: 20 },
};

const mockUserActivity = {
  dailyActiveUsers: [
    { date: '2026-03-01', count: 85 },
    { date: '2026-03-02', count: 92 },
  ],
  weeklyActiveUsers: [],
  avgSessionDurationSeconds: 240,
  avgPagesPerSession: 4.5,
  returningUserRate: 62.3,
  featureAdoption: { catalog: 100, search: 80, chat: 50, compare: 30, governance: 20 },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function mockAnalyticsApis(page: Page) {
  await page.route('**/api/analytics/summary*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockSummary),
    });
  });

  await page.route('**/api/analytics/usage-trends*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockTrends),
    });
  });

  await page.route('**/api/analytics/popular-apis*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockPopularApis),
    });
  });

  await page.route('**/api/analytics/search-trends*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockSearchTrends),
    });
  });

  await page.route('**/api/analytics/user-activity*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockUserActivity),
    });
  });
}

async function mockAuthAsRegularUser(page: Page) {
  await page.route('**/auth/me*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'user-2',
        name: 'Regular User',
        email: 'user@example.com',
        roles: [],
      }),
    });
  });
}

// ---------------------------------------------------------------------------
// Overview Dashboard tests
// ---------------------------------------------------------------------------

test.describe('Analytics Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalyticsApis(page);
    await page.goto('/analytics');
  });

  test('should display analytics dashboard', async ({ page }) => {
    await expect(page.getByTestId('analytics-dashboard')).toBeVisible();
    await expect(page.getByRole('heading', { name: /analytics dashboard/i })).toBeVisible();
  });

  test('should display KPI cards', async ({ page }) => {
    await expect(page.getByTestId('total-users-card')).toBeVisible();
    await expect(page.getByTestId('page-views-card')).toBeVisible();
    await expect(page.getByTestId('search-queries-card')).toBeVisible();
    await expect(page.getByTestId('chat-interactions-card')).toBeVisible();
    await expect(page.getByTestId('avg-session-card')).toBeVisible();
  });

  test('should display usage trend chart', async ({ page }) => {
    await expect(page.getByTestId('usage-trend-chart')).toBeVisible();
  });

  test('should display popular APIs chart', async ({ page }) => {
    await expect(page.getByTestId('popular-apis-chart')).toBeVisible();
  });

  test('should display search query list', async ({ page }) => {
    await expect(page.getByTestId('search-query-list')).toBeVisible();
  });

  test('should display time range selector', async ({ page }) => {
    await expect(page.getByTestId('time-range-selector')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Time range selection
// ---------------------------------------------------------------------------

test.describe('Time Range Selection', () => {
  test('should change time range to 7 days', async ({ page }) => {
    await mockAnalyticsApis(page);
    await page.goto('/analytics');

    await expect(page.getByTestId('time-range-selector')).toBeVisible();
    await page.getByTestId('time-range-7d').click();

    // After clicking 7d, the page should still show the dashboard
    await expect(page.getByTestId('analytics-dashboard')).toBeVisible();
  });

  test('should change time range to 90 days', async ({ page }) => {
    await mockAnalyticsApis(page);
    await page.goto('/analytics');

    await page.getByTestId('time-range-90d').click();
    await expect(page.getByTestId('analytics-dashboard')).toBeVisible();
  });

  test('should change time range to 1 year', async ({ page }) => {
    await mockAnalyticsApis(page);
    await page.goto('/analytics');

    await page.getByTestId('time-range-1y').click();
    await expect(page.getByTestId('analytics-dashboard')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Search Analytics page
// ---------------------------------------------------------------------------

test.describe('Search Analytics', () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalyticsApis(page);
    await page.goto('/analytics/search');
  });

  test('should display search analytics dashboard', async ({ page }) => {
    await expect(page.getByTestId('search-analytics-dashboard')).toBeVisible();
    await expect(page.getByRole('heading', { name: /search analytics/i })).toBeVisible();
  });

  test('should display search effectiveness chart', async ({ page }) => {
    await expect(page.getByTestId('search-effectiveness-chart')).toBeVisible();
  });

  test('should display search query list', async ({ page }) => {
    await expect(page.getByTestId('search-query-list')).toBeVisible();
  });

  test('should show zero result queries', async ({ page }) => {
    await expect(page.getByTestId('zero-result-query-0')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// API Popularity page
// ---------------------------------------------------------------------------

test.describe('API Popularity', () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalyticsApis(page);
    await page.goto('/analytics/apis');
  });

  test('should display API popularity dashboard', async ({ page }) => {
    await expect(page.getByTestId('api-popularity-dashboard')).toBeVisible();
    await expect(page.getByRole('heading', { name: /api popularity/i })).toBeVisible();
  });

  test('should display popular APIs chart', async ({ page }) => {
    await expect(page.getByTestId('popular-apis-chart')).toBeVisible();
  });

  test('should display API traffic table', async ({ page }) => {
    await expect(page.getByTestId('api-traffic-table')).toBeVisible();
    await expect(page.getByTestId('api-traffic-row-payments-api')).toBeVisible();
    await expect(page.getByTestId('api-traffic-row-users-api')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// User Engagement page
// ---------------------------------------------------------------------------

test.describe('User Engagement', () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalyticsApis(page);
    await page.goto('/analytics/users');
  });

  test('should display user engagement dashboard', async ({ page }) => {
    await expect(page.getByTestId('user-engagement-dashboard')).toBeVisible();
    await expect(page.getByRole('heading', { name: /user engagement/i })).toBeVisible();
  });

  test('should display user engagement chart', async ({ page }) => {
    await expect(page.getByTestId('user-engagement-chart')).toBeVisible();
  });

  test('should display feature usage chart', async ({ page }) => {
    await expect(page.getByTestId('feature-usage-chart')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Access control
// ---------------------------------------------------------------------------

test.describe('Access Control', () => {
  test('should show access denied for unauthorized users', async ({ page }) => {
    await mockAuthAsRegularUser(page);
    // Mock analytics APIs to return 403
    await page.route('**/api/analytics/**', async (route) => {
      await route.fulfill({ status: 403, body: 'Forbidden' });
    });
    await page.goto('/analytics');

    await expect(page.getByTestId('access-denied-icon')).toBeVisible();
    await expect(page.getByText(/access denied/i)).toBeVisible();
  });

  test('should show export button on overview page', async ({ page }) => {
    await mockAnalyticsApis(page);
    await page.goto('/analytics');

    await expect(page.getByTestId('export-csv-button')).toBeVisible();
  });
});
