/**
 * E2E tests for the API Comparison feature.
 *
 * All BFF calls are intercepted with page.route() so no live Azure
 * services are required. The tests cover:
 *
 *  - Empty state shown when no APIs are selected
 *  - Selecting 2 APIs triggers a comparison and shows the table
 *  - Adding a 3rd API updates the comparison
 *  - Removing an API updates the comparison correctly
 *  - AI analysis button is visible and can be triggered
 *  - Comparison URL is shareable (IDs in query string)
 *  - Error state when comparison fails
 */

import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_API_SUGGESTIONS = [
  {
    apiId: 'payments-api',
    title: 'Payments API',
    description: 'Handles payment processing',
    kind: 'rest',
  },
  {
    apiId: 'users-api',
    title: 'Users API',
    description: 'Manages user accounts',
    kind: 'rest',
  },
  {
    apiId: 'orders-api',
    title: 'Orders API',
    description: 'Manages orders',
    kind: 'rest',
  },
];

const MOCK_COMPARE_RESULT = {
  apis: [
    {
      id: 'payments-api',
      name: 'payments-api',
      title: 'Payments API',
      description: 'Handles payment processing',
      kind: 'rest',
      lifecycleStage: 'production',
    },
    {
      id: 'users-api',
      name: 'users-api',
      title: 'Users API',
      description: 'Manages user accounts',
      kind: 'rest',
      lifecycleStage: 'production',
    },
  ],
  aspects: [
    {
      aspect: 'metadata.description',
      label: 'Description',
      values: [
        {
          value: 'Handles payment processing',
          display: 'Handles payment processing',
          isBest: false,
        },
        { value: 'Manages user accounts', display: 'Manages user accounts', isBest: false },
      ],
      allEqual: false,
    },
    {
      aspect: 'metadata.kind',
      label: 'Kind',
      values: [
        { value: 'rest', display: 'REST', isBest: false },
        { value: 'rest', display: 'REST', isBest: false },
      ],
      allEqual: true,
    },
  ],
  similarityScore: 0.75,
  aiAnalysis: null,
};

const MOCK_COMPARE_RESULT_THREE_APIS = {
  ...MOCK_COMPARE_RESULT,
  apis: [
    ...MOCK_COMPARE_RESULT.apis,
    {
      id: 'orders-api',
      name: 'orders-api',
      title: 'Orders API',
      description: 'Manages orders',
      kind: 'rest',
      lifecycleStage: 'development',
    },
  ],
  aspects: MOCK_COMPARE_RESULT.aspects.map((a) => ({
    ...a,
    values: [...a.values, { value: 'orders', display: 'orders', isBest: false }],
  })),
};

const MOCK_AI_ANALYSIS = {
  ...MOCK_COMPARE_RESULT,
  aiAnalysis:
    'The **Payments API** and **Users API** share similar architecture patterns. ' +
    'Payments API is optimized for high-throughput transactional workloads, while ' +
    'Users API focuses on CRUD operations for identity management.',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function mockSearchSuggest(page: Page) {
  await page.route('**/api/search/suggest*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ suggestions: MOCK_API_SUGGESTIONS }),
    });
  });
}

async function mockCompareApis(page: Page, threeApis = false) {
  await page.route('**/api/compare', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as { apiIds: string[] };
      const result =
        body.apiIds.length >= 3 || threeApis ? MOCK_COMPARE_RESULT_THREE_APIS : MOCK_COMPARE_RESULT;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(result),
      });
    } else {
      await route.continue();
    }
  });
}

async function mockCompareAiAnalysis(page: Page) {
  await page.route('**/api/compare/ai-analysis', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_AI_ANALYSIS),
      });
    } else {
      await route.continue();
    }
  });
}

async function injectMockUser(page: Page) {
  await page.addInitScript(() => {
    (
      window as Window & {
        __PLAYWRIGHT_USER__?: { name: string; email: string; id: string; roles: string[] };
      }
    ).__PLAYWRIGHT_USER__ = {
      name: 'Sam Developer',
      email: 'sam@contoso.com',
      id: 'user-sam-1',
      roles: ['Portal.User'],
    };
  });
}

// ---------------------------------------------------------------------------
// Tests: Empty state
// ---------------------------------------------------------------------------

test.describe('API Comparison — Empty State', () => {
  test('shows empty state when no APIs are selected', async ({ page }) => {
    await page.goto('/compare');

    await expect(page.getByTestId('compare-empty-state')).toBeVisible();
    await expect(page.getByText(/no apis selected for comparison/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /browse catalog/i })).toBeVisible();
  });

  test('shows selector with "select at least 2 more" hint', async ({ page }) => {
    await page.goto('/compare');

    await expect(page.getByTestId('compare-selector')).toBeVisible();
    await expect(page.getByText(/select at least/i)).toBeVisible();
  });

  test('Browse Catalog button navigates to catalog', async ({ page }) => {
    await page.route('**/api/catalog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [],
          meta: { page: 1, pageSize: 20, totalCount: 0, totalPages: 0 },
        }),
      });
    });

    await page.goto('/compare');
    await page.getByRole('button', { name: /browse catalog/i }).click();
    await expect(page).toHaveURL(/\/catalog/);
  });
});

// ---------------------------------------------------------------------------
// Tests: Selecting APIs
// ---------------------------------------------------------------------------

test.describe('API Comparison — Selecting APIs', () => {
  test.beforeEach(async ({ page }) => {
    await injectMockUser(page);
    await mockSearchSuggest(page);
    await mockCompareApis(page);
    await mockCompareAiAnalysis(page);
  });

  test('search input is visible in the selector', async ({ page }) => {
    await page.goto('/compare');
    await expect(page.getByTestId('compare-search-input')).toBeVisible();
  });

  test('typing in search shows suggestions', async ({ page }) => {
    await page.goto('/compare');

    const searchInput = page.getByTestId('compare-search-input');
    await searchInput.fill('payments');

    // Suggestions should appear
    await expect(page.getByTestId('search-result-payments-api')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Payments API')).toBeVisible();
  });

  test('selecting 2 APIs triggers comparison and shows table', async ({ page }) => {
    // Navigate with 2 APIs pre-selected via URL
    await page.goto('/compare?compare=payments-api,users-api');

    // Table should be visible
    await expect(page.getByTestId('compare-table')).toBeVisible({ timeout: 10000 });

    // Both API names should appear in table header
    await expect(page.getByText('Payments API')).toBeVisible();
    await expect(page.getByText('Users API')).toBeVisible();

    // AI analysis section should be visible
    await expect(page.getByTestId('compare-ai-analysis')).toBeVisible();
  });

  test('comparison URL contains selected API IDs', async ({ page }) => {
    await page.goto('/compare?compare=payments-api,users-api');

    // URL should contain the compare parameter
    await expect(page).toHaveURL(/compare=payments-api%2Cusers-api|compare=payments-api,users-api/);
  });

  test('similarity score is displayed after comparison', async ({ page }) => {
    await page.goto('/compare?compare=payments-api,users-api');

    // Similarity score chip should be visible
    await expect(page.getByText(/75%/)).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Tests: Adding and removing APIs
// ---------------------------------------------------------------------------

test.describe('API Comparison — Add and Remove', () => {
  test.beforeEach(async ({ page }) => {
    await injectMockUser(page);
    await mockSearchSuggest(page);
    await mockCompareApis(page);
    await mockCompareAiAnalysis(page);
  });

  test('selected API chips are displayed', async ({ page }) => {
    await page.goto('/compare?compare=payments-api,users-api');

    // Chips for selected APIs should appear
    await expect(page.getByTestId('selected-chip-payments-api')).toBeVisible();
    await expect(page.getByTestId('selected-chip-users-api')).toBeVisible();
  });

  test('removing an API updates the comparison', async ({ page }) => {
    await page.goto('/compare?compare=payments-api,users-api');

    // Wait for comparison to load
    await expect(page.getByTestId('compare-table')).toBeVisible({ timeout: 10000 });

    // Remove one API via URL navigation (simulates chip delete → URL update)
    await page.goto('/compare?compare=users-api');

    // Should now have only 1 API → empty state
    await expect(page.getByTestId('compare-empty-state')).toBeVisible({ timeout: 5000 });
  });

  test('adding a 3rd API updates the comparison with 3 columns', async ({ page }) => {
    // Start with 3 APIs already selected via URL
    await page.goto('/compare?compare=payments-api,users-api,orders-api');

    // Table should show 3 API columns
    await expect(page.getByTestId('compare-table')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Payments API')).toBeVisible();
    await expect(page.getByText('Users API')).toBeVisible();
    await expect(page.getByText('Orders API')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Tests: AI Analysis
// ---------------------------------------------------------------------------

test.describe('API Comparison — AI Analysis', () => {
  test.beforeEach(async ({ page }) => {
    await injectMockUser(page);
    await mockSearchSuggest(page);
    await mockCompareApis(page);
    await mockCompareAiAnalysis(page);
  });

  test('AI analysis button is visible when comparison is loaded', async ({ page }) => {
    await page.goto('/compare?compare=payments-api,users-api');

    await expect(page.getByTestId('compare-ai-analysis')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('request-ai-analysis-button')).toBeVisible();
  });

  test('clicking Generate AI Analysis fetches and displays analysis', async ({ page }) => {
    await page.goto('/compare?compare=payments-api,users-api');

    // Wait for comparison to load
    await expect(page.getByTestId('request-ai-analysis-button')).toBeVisible({ timeout: 10000 });

    // Click the AI analysis button
    await page.getByTestId('request-ai-analysis-button').click();

    // AI analysis text should appear (check the AI analysis section specifically to avoid strict mode)
    await expect(
      page.getByTestId('compare-ai-analysis').getByText(/optimized for high-throughput/i)
    ).toBeVisible({
      timeout: 10000,
    });
  });
});

// ---------------------------------------------------------------------------
// Tests: Error state
// ---------------------------------------------------------------------------

test.describe('API Comparison — Error State', () => {
  test('shows error alert when comparison fails', async ({ page }) => {
    await injectMockUser(page);

    // Mock a failing comparison endpoint
    await page.route('**/api/compare', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'INTERNAL_ERROR', message: 'Server error' } }),
      });
    });

    await page.goto('/compare?compare=payments-api,users-api');

    // Error alert should be visible
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible();
  });
});
