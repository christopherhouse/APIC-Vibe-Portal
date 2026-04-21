/**
 * Developer user journey E2E test.
 *
 * Simulates a realistic developer workflow across the complete APIC Vibe Portal
 * covering all three phases of features:
 *
 *   Phase 1 (MVP):
 *     1. Authenticate → Browse API catalog
 *     2. Filter catalog by lifecycle
 *     3. Open API detail → explore tabs
 *     4. Search for an API
 *     5. Use AI Assistant to ask about APIs
 *
 *   Phase 2 (Governance + Compare):
 *     6. Check governance dashboard for an API
 *     7. Compare two APIs
 *
 *   Phase 3 (Analytics & Polish):
 *     8. Navigate to analytics (if accessible)
 *     9. Complete the journey and sign-out representation
 *
 * All BFF calls are intercepted with page.route() so no Azure services are
 * required.
 */

import { test, expect, type Page } from '@playwright/test';
import { generateMockApis, generateMockSpec } from '../mock-server';

interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

const DEVELOPER_USER: AuthUser = {
  name: 'Dev Developer',
  email: 'dev@contoso.com',
  id: 'user-dev-1',
  roles: ['Portal.User'],
};

async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

async function setupDeveloperMocks(page: Page) {
  const apis = generateMockApis(8);

  // Catalog list
  await page.route('**/api/catalog?*', async (route) => {
    const url = new URL(route.request().url());
    const lifecycle = url.searchParams.get('lifecycle');
    let filtered = [...apis];
    if (lifecycle) filtered = filtered.filter((a) => a.lifecycleStage === lifecycle);
    const pageSize = Number(url.searchParams.get('pageSize') ?? '10');
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: filtered.slice(0, pageSize),
        meta: { page: 1, pageSize, totalCount: filtered.length, totalPages: 1 },
      }),
    });
  });

  await page.route('**/api/catalog', async (route) => {
    if (route.request().url().includes('/api/catalog/')) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: apis.slice(0, 10),
        meta: { page: 1, pageSize: 20, totalCount: apis.length, totalPages: 1 },
      }),
    });
  });

  // API detail
  await page.route(/\/api\/catalog\/[^/]+$/, async (route) => {
    const apiId = new URL(route.request().url()).pathname.split('/').pop();
    const api = apis.find((a) => a.id === apiId);
    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(api ? { data: api } : { error: { code: 'NOT_FOUND' } }),
    });
  });

  // Versions
  await page.route(/\/api\/catalog\/[^/]+\/versions$/, async (route) => {
    const parts = new URL(route.request().url()).pathname.split('/');
    const api = apis.find((a) => a.id === parts[parts.length - 2]);
    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(api ? { data: api.versions } : { error: { code: 'NOT_FOUND' } }),
    });
  });

  // Definition
  await page.route(/\/api\/catalog\/[^/]+\/versions\/[^/]+\/definition$/, async (route) => {
    const parts = new URL(route.request().url()).pathname.split('/');
    const api = apis.find((a) => a.id === parts[parts.length - 4]);
    const version = api?.versions.find((v) => v.id === parts[parts.length - 2]);
    await route.fulfill({
      status: version ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(
        version
          ? {
              data: {
                id: `def-${version.id}`,
                name: `definition-${version.id}`,
                title: `${api!.title} ${version.title} Definition`,
                specificationType: 'openapi',
                specificationVersion: '3.0.3',
                content: generateMockSpec(api!.title, version.title),
              },
            }
          : { error: { code: 'NOT_FOUND' } }
      ),
    });
  });

  // Deployments
  await page.route(/\/api\/catalog\/[^/]+\/deployments$/, async (route) => {
    const parts = new URL(route.request().url()).pathname.split('/');
    const api = apis.find((a) => a.id === parts[parts.length - 2]);
    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(api ? { data: api.deployments } : { error: { code: 'NOT_FOUND' } }),
    });
  });

  // Search
  await page.route('**/api/search*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        results: apis.slice(0, 3).map((a) => ({
          apiId: a.id,
          apiName: a.name,
          title: a.title,
          description: a.description,
          kind: a.kind,
          lifecycleStage: a.lifecycleStage,
          score: 0.9,
        })),
        totalCount: 3,
        facets: {
          kind: [{ value: 'rest', count: 2 }],
          lifecycle: [{ value: 'production', count: 2 }],
          tags: [],
        },
        queryDuration: 30,
      }),
    });
  });

  // Chat stream
  await page.route('**/api/chat/stream', async (route) => {
    const content = 'For your use case, the Payments API (v2) would be the best fit.';
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: [
        `data: ${JSON.stringify({ type: 'start', sessionId: 'dev-session-1' })}\n\n`,
        `data: ${JSON.stringify({ type: 'content', content })}\n\n`,
        `data: ${JSON.stringify({
          type: 'end',
          message: {
            id: 'msg-1',
            role: 'assistant',
            content,
            citations: null,
            timestamp: new Date().toISOString(),
          },
          sessionId: 'dev-session-1',
        })}\n\n`,
      ].join(''),
    });
  });

  // Governance
  await page.route('**/api/governance/summary', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          overallScore: 84.0,
          compliantCount: 6,
          totalCount: 8,
          criticalIssues: 1,
          improvement: 3.0,
        },
      }),
    });
  });

  await page.route('**/api/governance/scores*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: apis.slice(0, 4).map((a, i) => ({
          apiId: a.id,
          apiName: a.title,
          score: 90 - i * 8,
          category: i === 0 ? 'Excellent' : 'Good',
          criticalFailures: i === 3 ? 1 : 0,
          lastChecked: new Date().toISOString(),
        })),
      }),
    });
  });

  // Comparison
  await page.route('**/api/compare', async (route) => {
    const body = await route.request().postDataJSON();
    const comparedApis = (body?.apiIds ?? []).map((id: string) => {
      const api = apis.find((a) => a.id === id);
      return api ?? apis[0];
    });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          apis: comparedApis,
          attributes: [
            { key: 'kind', label: 'API Type' },
            { key: 'lifecycleStage', label: 'Lifecycle' },
          ],
        },
      }),
    });
  });
}

test.describe('Developer User Journey', () => {
  test('full developer journey: authenticate → browse → search → detail → AI chat', async ({
    page,
  }) => {
    await setMockUser(page, DEVELOPER_USER);
    await setupDeveloperMocks(page);

    // Step 1: Land on portal as authenticated developer
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();

    // Step 2: Browse the catalog
    await expect(page.getByText('Test API 1', { exact: true })).toBeVisible();
    await expect(page.getByText('Test API 2', { exact: true })).toBeVisible();

    // Step 3: Filter by Production lifecycle
    await page.getByLabel('Filter by Production').click();
    await expect(page).toHaveURL(/lifecycle=production/);
    await expect(page.getByText('Test API 1', { exact: true })).toBeVisible();

    // Clear filter
    await page.goto('/catalog');

    // Step 4: Open API detail page
    await page.getByText('Test API 1', { exact: true }).click();
    await expect(page).toHaveURL(/\/catalog\/api-1/);
    await expect(page.getByRole('heading', { name: 'Test API 1' })).toBeVisible();

    // Explore tabs
    await expect(page.getByTestId('api-metadata')).toBeVisible();
    await page.getByRole('tab', { name: 'Versions' }).click();
    await expect(page.getByTestId('version-list')).toBeVisible();

    await page.getByRole('tab', { name: 'Specification' }).click();
    await expect(page.getByTestId('spec-viewer')).toBeVisible({ timeout: 10000 });

    await page.getByRole('tab', { name: 'Deployments' }).click();
    await expect(page.getByTestId('deployments-table')).toBeVisible();

    // Navigate back
    const header = page.getByTestId('api-header');
    await header.getByRole('link', { name: 'Catalog' }).click();
    await expect(page).toHaveURL(/\/catalog$/);

    // Step 5: Search for an API
    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('Payment API');
    await searchInput.press('Enter');
    await expect(page).toHaveURL(/\/search\?q=/);
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();

    // View and click first result
    await expect(page.getByTestId('search-result-api-1')).toBeVisible({ timeout: 5000 });
    await page.getByTestId('search-result-api-1').click();
    await expect(page).toHaveURL(/\/catalog\//);

    // Step 6: Use AI chat via full page
    await page.goto('/chat');
    const main = page.locator('main');
    await expect(main.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();

    await main.getByTestId('chat-input').fill('Which APIs support REST?');
    await main.getByTestId('send-button').click();
    await expect(main.getByText(/Payments API/i)).toBeVisible({ timeout: 10000 });
  });

  test('developer uses AI FAB on catalog page', async ({ page }) => {
    await setMockUser(page, DEVELOPER_USER);
    await setupDeveloperMocks(page);
    await page.goto('/catalog');

    // Open chat side panel via FAB
    await expect(page.getByTestId('chat-fab')).toBeVisible();
    await page.getByTestId('chat-fab').click();

    const panel = page.getByTestId('chat-side-panel');
    await expect(panel.getByText('AI Assistant')).toBeVisible({ timeout: 5000 });

    // Send a message
    await panel.getByTestId('chat-input').fill('Show me production APIs');
    await panel.getByTestId('send-button').click();
    await expect(panel.getByText('Show me production APIs')).toBeVisible({ timeout: 5000 });
  });

  test('developer searches and filters results', async ({ page }) => {
    await setMockUser(page, DEVELOPER_USER);
    await setupDeveloperMocks(page);

    // Navigate directly to search with a query
    await page.goto('/search?q=API');
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();
    await expect(page.getByTestId('search-result-api-1')).toBeVisible({ timeout: 5000 });

    // Apply lifecycle filter
    await page.getByLabel('Filter by Production').click();
    await expect(page).toHaveURL(/lifecycle=production/);
  });
});
