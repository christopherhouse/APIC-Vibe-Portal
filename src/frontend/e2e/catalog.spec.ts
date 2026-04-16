import { test, expect, type Page } from '@playwright/test';
import type { PaginationMeta } from '@apic-vibe-portal/shared';

/**
 * Shape matching the BFF's actual response (ApiDefinition with arrays).
 * The frontend maps these to ApiCatalogItem via toApiCatalogItem.
 */
interface MockApiDefinition {
  id: string;
  name: string;
  title: string;
  description: string;
  kind: string;
  lifecycleStage: string;
  versions: {
    id: string;
    name: string;
    title: string;
    lifecycleStage: string;
    createdAt: string;
    updatedAt: string;
  }[];
  deployments: {
    id: string;
    title: string;
    environment: { id: string; name: string; title: string; kind: string };
    server: { runtimeUri: string[] };
    createdAt: string;
    updatedAt: string;
  }[];
  createdAt: string;
  updatedAt: string;
}

/**
 * Generate mock API definitions matching the BFF response shape.
 */
function makeMockApis(
  count: number,
  overrides: Partial<MockApiDefinition> = {}
): MockApiDefinition[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `api-${i + 1}`,
    name: `api-${i + 1}`,
    title: `Test API ${i + 1}`,
    description: `Description for API ${i + 1}. This API provides various endpoints for testing purposes.`,
    kind: i % 2 === 0 ? 'rest' : 'graphql',
    lifecycleStage: i % 3 === 0 ? 'production' : i % 3 === 1 ? 'development' : 'deprecated',
    versions: Array.from({ length: i + 1 }, (__, vi) => ({
      id: `v${vi + 1}`,
      name: `v${vi + 1}`,
      title: `Version ${vi + 1}`,
      lifecycleStage: 'production',
      createdAt: new Date(2026, 2, 15 - i).toISOString(),
      updatedAt: new Date(2026, 2, 15 - i).toISOString(),
    })),
    deployments: [
      {
        id: `dep-${i + 1}`,
        title: `Deployment ${i + 1}`,
        environment: { id: 'env-1', name: 'prod', title: 'Production', kind: 'production' },
        server: { runtimeUri: ['https://api.example.com'] },
        createdAt: new Date(2026, 2, 15 - i).toISOString(),
        updatedAt: new Date(2026, 2, 15 - i).toISOString(),
      },
    ],
    createdAt: new Date(2026, 1, 1).toISOString(),
    updatedAt: new Date(2026, 2, 15 - i).toISOString(),
    ...overrides,
  }));
}

/**
 * Mock the BFF /api/catalog endpoint with configurable data.
 */
async function mockCatalogApi(
  page: Page,
  apis: MockApiDefinition[],
  pagination?: Partial<PaginationMeta>
) {
  await page.route('**/api/catalog*', async (route) => {
    const url = new URL(route.request().url());
    const requestedPage = Number(url.searchParams.get('page') ?? '1');
    const requestedPageSize = Number(url.searchParams.get('pageSize') ?? '20');
    const lifecycle = url.searchParams.get('lifecycle');
    const kind = url.searchParams.get('kind');
    const sort = url.searchParams.get('sort');
    const direction = url.searchParams.get('direction') ?? 'asc';

    let filtered = [...apis];

    // Apply lifecycle filter
    if (lifecycle) {
      filtered = filtered.filter((api) => api.lifecycleStage === lifecycle);
    }

    // Apply kind filter
    if (kind) {
      filtered = filtered.filter((api) => api.kind === kind);
    }

    // Apply sort
    if (sort === 'name') {
      filtered.sort((a, b) =>
        direction === 'asc' ? a.title.localeCompare(b.title) : b.title.localeCompare(a.title)
      );
    }

    const totalCount = filtered.length;
    const totalPages = Math.ceil(totalCount / requestedPageSize);
    const start = (requestedPage - 1) * requestedPageSize;
    const pageItems = filtered.slice(start, start + requestedPageSize);

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: pageItems,
        meta: {
          page: requestedPage,
          pageSize: requestedPageSize,
          totalCount,
          totalPages,
          ...pagination,
        },
      }),
    });
  });
}

test.describe('API Catalog Page', () => {
  test('displays catalog page heading and APIs', async ({ page }) => {
    const apis = makeMockApis(6);
    await mockCatalogApi(page, apis);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByText('Browse and discover APIs')).toBeVisible();

    // Check that API cards are rendered
    await expect(page.getByText('Test API 1')).toBeVisible();
    await expect(page.getByText('Test API 6')).toBeVisible();
  });

  test('homepage redirects to /catalog', async ({ page }) => {
    const apis = makeMockApis(3);
    await mockCatalogApi(page, apis);
    await page.goto('/');

    await expect(page).toHaveURL(/\/catalog/);
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
  });

  test('shows empty state when no APIs match', async ({ page }) => {
    await mockCatalogApi(page, []);
    await page.goto('/catalog');

    await expect(page.getByText('No APIs found')).toBeVisible();
    await expect(page.getByText(/Try adjusting your filters/)).toBeVisible();
  });

  test('displays loading skeleton while fetching data', async ({ page }) => {
    // Delay the API response to observe the skeleton
    await page.route('**/api/catalog*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: makeMockApis(3),
          meta: { page: 1, pageSize: 20, totalCount: 3, totalPages: 1 },
        }),
      });
    });

    await page.goto('/catalog');
    await expect(page.getByTestId('catalog-skeleton')).toBeVisible();
    // Wait for data to load
    await expect(page.getByText('Test API 1')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Catalog Filtering', () => {
  test('lifecycle filter narrows displayed APIs', async ({ page }) => {
    const apis = makeMockApis(9);
    await mockCatalogApi(page, apis);
    await page.goto('/catalog');

    // All APIs should be visible initially
    await expect(page.getByText('Test API 1')).toBeVisible();

    // Click the Production lifecycle filter
    await page.getByLabel('Filter by Production').click();

    // URL should update with lifecycle param
    await expect(page).toHaveURL(/lifecycle=production/);

    // Wait for filtered results - production APIs should be visible
    await expect(page.getByText('Test API 1')).toBeVisible(); // index 0, 0%3=0 => production
    await expect(page.getByText('Test API 4')).toBeVisible(); // index 3, 3%3=0 => production
  });

  test('kind filter narrows displayed APIs', async ({ page }) => {
    const apis = makeMockApis(6);
    await mockCatalogApi(page, apis);
    await page.goto('/catalog');

    await expect(page.getByText('Test API 1')).toBeVisible();

    // Click the REST kind filter
    await page.getByLabel('Filter by REST').click();

    // URL should update with kind param
    await expect(page).toHaveURL(/kind=rest/);
  });

  test('filter state is reflected in URL for shareability', async ({ page }) => {
    const apis = makeMockApis(6);
    await mockCatalogApi(page, apis);

    // Navigate directly with filter params
    await page.goto('/catalog?lifecycle=production');

    // The production radio should be checked
    await expect(page.getByLabel('Filter by Production')).toBeChecked();
  });
});

test.describe('Catalog Sorting', () => {
  test('sort controls are visible and functional', async ({ page }) => {
    const apis = makeMockApis(6);
    await mockCatalogApi(page, apis);
    await page.goto('/catalog');

    // Sort select should be visible
    const sortSelect = page.getByRole('combobox', { name: /sort by/i });
    await expect(sortSelect).toBeVisible();

    // Click to open dropdown
    await sortSelect.click();

    // Select Name A-Z sort
    await page.getByRole('option', { name: /Name \(A–Z\)/i }).click();

    // URL should update with sort params
    await expect(page).toHaveURL(/sort=name/);
    await expect(page).toHaveURL(/direction=asc/);
  });
});

test.describe('Catalog Pagination', () => {
  test('pagination shows item count and page controls', async ({ page }) => {
    const apis = makeMockApis(25);
    await mockCatalogApi(page, apis);
    await page.goto('/catalog');

    // Should show pagination info
    await expect(page.getByTestId('pagination-info')).toContainText('Showing 1–20 of 25 APIs');
  });

  test('page navigation works', async ({ page }) => {
    const apis = makeMockApis(25);
    await mockCatalogApi(page, apis);
    await page.goto('/catalog');

    await expect(page.getByTestId('pagination-info')).toContainText('Showing 1–20 of 25 APIs');

    // Click page 2
    await page.getByRole('button', { name: /go to page 2/i }).click();
    await expect(page).toHaveURL(/page=2/);
    await expect(page.getByTestId('pagination-info')).toContainText('Showing 21–25 of 25 APIs');
  });
});

test.describe('Catalog View Toggle', () => {
  test('grid/list toggle switches view mode', async ({ page }) => {
    const apis = makeMockApis(3);
    await mockCatalogApi(page, apis);
    await page.goto('/catalog');

    // Default should be grid view
    await expect(page.getByTestId('catalog-grid')).toBeVisible();

    // Switch to list view
    await page.getByLabel('List view').click();
    await expect(page.getByTestId('catalog-list')).toBeVisible();

    // Switch back to grid view
    await page.getByLabel('Grid view').click();
    await expect(page.getByTestId('catalog-grid')).toBeVisible();
  });
});

test.describe('Catalog Card Navigation', () => {
  test('clicking an API card navigates to detail page', async ({ page }) => {
    const apis = makeMockApis(3);
    await mockCatalogApi(page, apis);
    await page.goto('/catalog');

    await expect(page.getByText('Test API 1')).toBeVisible();

    // Click on the first API card
    await page.getByText('Test API 1').click();

    // Should navigate to the detail page
    await expect(page).toHaveURL(/\/catalog\/api-1/);
  });
});
