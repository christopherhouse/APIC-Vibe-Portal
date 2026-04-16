import { test, expect, type Page } from '@playwright/test';
import type { MockApiDefinition } from './mock-server';
import { generateMockApis, generateMockSpec } from './mock-server';

/**
 * Mock all BFF API endpoints for the detail page via Playwright route interception.
 */
async function mockDetailApis(page: Page, apis: MockApiDefinition[]) {
  // Mock catalog list (for catalog page and breadcrumb navigation)
  await page.route('**/api/catalog?*', async (route) => {
    const url = new URL(route.request().url());
    const requestedPage = Number(url.searchParams.get('page') ?? '1');
    const requestedPageSize = Number(url.searchParams.get('pageSize') ?? '20');
    const lifecycle = url.searchParams.get('lifecycle');
    const kind = url.searchParams.get('kind');

    let filtered = [...apis];
    if (lifecycle) filtered = filtered.filter((a) => a.lifecycleStage === lifecycle);
    if (kind) filtered = filtered.filter((a) => a.kind === kind);

    const totalCount = filtered.length;
    const totalPages = Math.ceil(totalCount / requestedPageSize);
    const start = (requestedPage - 1) * requestedPageSize;
    const pageItems = filtered.slice(start, start + requestedPageSize);

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: pageItems,
        meta: { page: requestedPage, pageSize: requestedPageSize, totalCount, totalPages },
      }),
    });
  });

  // Mock API detail endpoint
  await page.route(/\/api\/catalog\/[^/]+$/, async (route) => {
    const url = new URL(route.request().url());
    const apiId = url.pathname.split('/').pop();
    const api = apis.find((a) => a.id === apiId);

    if (!api) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'NOT_FOUND', message: 'API not found' } }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: api }),
    });
  });

  // Mock versions endpoint
  await page.route(/\/api\/catalog\/[^/]+\/versions$/, async (route) => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split('/');
    const apiId = parts[parts.length - 2];
    const api = apis.find((a) => a.id === apiId);

    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(api ? { data: api.versions } : { error: { code: 'NOT_FOUND', message: 'API not found' } }),
    });
  });

  // Mock definition endpoint
  await page.route(/\/api\/catalog\/[^/]+\/versions\/[^/]+\/definition$/, async (route) => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split('/');
    const versionId = parts[parts.length - 2];
    const apiId = parts[parts.length - 4];
    const api = apis.find((a) => a.id === apiId);

    if (!api) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'NOT_FOUND', message: 'API not found' } }),
      });
      return;
    }

    const version = api.versions.find((v) => v.id === versionId);
    if (!version) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Version not found' } }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: generateMockSpec(api.title, version.title) }),
    });
  });

  // Mock deployments endpoint
  await page.route(/\/api\/catalog\/[^/]+\/deployments$/, async (route) => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split('/');
    const apiId = parts[parts.length - 2];
    const api = apis.find((a) => a.id === apiId);

    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(api ? { data: api.deployments } : { error: { code: 'NOT_FOUND', message: 'API not found' } }),
    });
  });
}

test.describe('API Detail Page', () => {
  test('displays API detail with header and breadcrumb', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);
    await page.goto('/catalog/api-1');

    // Check breadcrumb within the header component
    const header = page.getByTestId('api-header');
    const breadcrumbLink = header.getByRole('link', { name: 'Catalog' });
    await expect(breadcrumbLink).toBeVisible();
    await expect(breadcrumbLink).toHaveAttribute('href', '/catalog');

    // Check title
    await expect(page.getByRole('heading', { name: 'Test API 1' })).toBeVisible();

    // Check badges
    await expect(page.getByTestId('kind-badge')).toBeVisible();
    await expect(page.getByTestId('lifecycle-badge')).toBeVisible();
  });

  test('displays overview tab with metadata by default', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);
    await page.goto('/catalog/api-1');

    // Overview tab should be active by default
    await expect(page.getByTestId('api-metadata')).toBeVisible();

    // Should show description in metadata section
    const metadata = page.getByTestId('api-metadata');
    await expect(metadata.getByText(/Description for API 1/)).toBeVisible();

    // Should show license
    await expect(metadata.getByText('MIT')).toBeVisible();

    // Should show contacts
    await expect(metadata.getByText('API Team')).toBeVisible();
  });

  test('tab navigation switches between sections', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);
    await page.goto('/catalog/api-1');

    // Default: Overview
    await expect(page.getByTestId('api-metadata')).toBeVisible();

    // Switch to Versions
    await page.getByRole('tab', { name: 'Versions' }).click();
    await expect(page.getByTestId('version-list')).toBeVisible();

    // Switch to Specification
    await page.getByRole('tab', { name: 'Specification' }).click();
    await expect(page.getByTestId('spec-download-button')).toBeVisible();

    // Switch to Deployments
    await page.getByRole('tab', { name: 'Deployments' }).click();
    await expect(page.getByTestId('deployments-table')).toBeVisible();

    // Switch back to Overview
    await page.getByRole('tab', { name: 'Overview' }).click();
    await expect(page.getByTestId('api-metadata')).toBeVisible();
  });

  test('versions tab shows version list and selector', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);
    await page.goto('/catalog/api-1');

    await page.getByRole('tab', { name: 'Versions' }).click();
    await expect(page.getByTestId('version-list')).toBeVisible();

    // Should show version rows
    await expect(page.getByTestId('version-row-v1')).toBeVisible();
  });

  test('deployments tab shows deployment table', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);
    await page.goto('/catalog/api-1');

    await page.getByRole('tab', { name: 'Deployments' }).click();
    await expect(page.getByTestId('deployments-table')).toBeVisible();

    // Should show deployment rows
    await expect(page.getByTestId('deployment-row-dep-1-prod')).toBeVisible();
    await expect(page.getByTestId('deployment-row-dep-1-staging')).toBeVisible();
  });

  test('specification tab shows spec content', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);
    await page.goto('/catalog/api-1');

    await page.getByRole('tab', { name: 'Specification' }).click();

    // Wait for spec to load (auto-loaded for first version)
    await expect(page.getByTestId('spec-viewer')).toBeVisible({ timeout: 10000 });

    // Should show download button
    await expect(page.getByTestId('spec-download-button')).toBeVisible();
    await expect(page.getByTestId('spec-download-button')).toBeEnabled();
  });

  test('breadcrumb navigates back to catalog', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);
    await page.goto('/catalog/api-1');

    await expect(page.getByRole('heading', { name: 'Test API 1' })).toBeVisible();

    // Click catalog breadcrumb (scoped to api-header to avoid sidebar match)
    const header = page.getByTestId('api-header');
    await header.getByRole('link', { name: 'Catalog' }).click();
    await expect(page).toHaveURL(/\/catalog$/);
  });

  test('version switching loads new spec', async ({ page }) => {
    // Create API with multiple versions
    const apis = generateMockApis(5);
    await mockDetailApis(page, apis);

    // api-3 has 3 versions (min(2+1, 3) = 3)
    await page.goto('/catalog/api-3');

    // Go to versions tab
    await page.getByRole('tab', { name: 'Versions' }).click();
    await expect(page.getByTestId('version-list')).toBeVisible();

    // Should show multiple version rows
    await expect(page.getByTestId('version-row-v1')).toBeVisible();
    await expect(page.getByTestId('version-row-v2')).toBeVisible();
    await expect(page.getByTestId('version-row-v3')).toBeVisible();

    // Click on v2 row to switch version
    await page.getByTestId('version-row-v2').click();

    // Switch to spec tab to see spec loaded
    await page.getByRole('tab', { name: 'Specification' }).click();
    await expect(page.getByTestId('spec-viewer')).toBeVisible({ timeout: 10000 });
  });

  test('shows error state for non-existent API', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);
    await page.goto('/catalog/non-existent-api');

    // Should show error alert
    await expect(page.getByText(/API request failed/)).toBeVisible({ timeout: 10000 });
  });

  test('navigating from catalog card lands on detail page', async ({ page }) => {
    const apis = generateMockApis(3);
    await mockDetailApis(page, apis);

    // Start at catalog page
    await page.goto('/catalog');
    await expect(page.getByText('Test API 1')).toBeVisible();

    // Click first API card
    await page.getByText('Test API 1').click();

    // Should navigate to detail
    await expect(page).toHaveURL(/\/catalog\/api-1/);
    await expect(page.getByRole('heading', { name: 'Test API 1' })).toBeVisible();
  });
});
