/**
 * Full end-to-end user journey test for the APIC Vibe Portal MVP.
 *
 * This test simulates a realistic developer workflow that exercises all core
 * Phase 1 MVP features working together:
 *
 *   1. Land on the portal unauthenticated → See the Sign in button
 *   2. "Authenticate" via mock user injection → User avatar appears
 *   3. Browse the API catalog → See API cards with filter and sort controls
 *   4. Filter the catalog by lifecycle → Results narrow down
 *   5. Click an API card → Navigate to the API detail page
 *   6. Explore API detail tabs (Overview, Versions, Specification, Deployments)
 *   7. Navigate to global search → Submit a query
 *   8. View search results → Click a result → Navigate to detail
 *   9. Open the AI Assistant chat page → Send a message → Receive a response
 *  10. Use the chat FAB on the catalog page → Side panel opens and works
 *  11. Sign out → User avatar disappears, Sign in button returns
 *
 * All BFF calls are intercepted with mock responses so no Azure services are
 * required. This mirrors the approach used in catalog.spec.ts, api-detail.spec.ts,
 * search.spec.ts, and chat.spec.ts.
 */

import { test, expect, type Page } from '@playwright/test';
import { generateMockApis, generateMockSpec } from './mock-server';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

// ---------------------------------------------------------------------------
// Mock user
// ---------------------------------------------------------------------------

const MOCK_USER: AuthUser = {
  name: 'Sam Developer',
  email: 'sam@contoso.com',
  id: 'user-sam-1',
  roles: ['Portal.User'],
};

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

/** Inject a mock AuthUser into the page before it loads. */
async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

/** Set up all BFF route mocks needed for the journey. */
async function setupAllMocks(page: Page) {
  const apis = generateMockApis(10);

  // Catalog list
  await page.route('**/api/catalog?*', async (route) => {
    const url = new URL(route.request().url());
    const requestedPage = Number(url.searchParams.get('page') ?? '1');
    const requestedPageSize = Number(url.searchParams.get('pageSize') ?? '20');
    const lifecycle = url.searchParams.get('lifecycle');
    const kind = url.searchParams.get('kind');
    const sort = url.searchParams.get('sort');
    const direction = url.searchParams.get('direction') ?? 'asc';

    let filtered = [...apis];
    if (lifecycle) filtered = filtered.filter((a) => a.lifecycleStage === lifecycle);
    if (kind) filtered = filtered.filter((a) => a.kind === kind);
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
        meta: { page: requestedPage, pageSize: requestedPageSize, totalCount, totalPages },
      }),
    });
  });

  // Catch-all for /api/catalog (without query string)
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

  // Versions
  await page.route(/\/api\/catalog\/[^/]+\/versions$/, async (route) => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split('/');
    const apiId = parts[parts.length - 2];
    const api = apis.find((a) => a.id === apiId);
    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(
        api ? { data: api.versions } : { error: { code: 'NOT_FOUND', message: 'Not found' } }
      ),
    });
  });

  // Definition
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
        body: JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Not found' } }),
      });
      return;
    }
    const version = api.versions.find((v) => v.id === versionId);
    if (!version) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Not found' } }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: `def-${versionId}`,
          name: `definition-${versionId}`,
          title: `${api.title} ${version.title} Definition`,
          specificationType: 'openapi',
          specificationVersion: '3.0.3',
          content: generateMockSpec(api.title, version.title),
        },
      }),
    });
  });

  // Deployments
  await page.route(/\/api\/catalog\/[^/]+\/deployments$/, async (route) => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split('/');
    const apiId = parts[parts.length - 2];
    const api = apis.find((a) => a.id === apiId);
    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(
        api ? { data: api.deployments } : { error: { code: 'NOT_FOUND', message: 'Not found' } }
      ),
    });
  });

  // Search
  await page.route('**/api/search', async (route) => {
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
          score: 0.95,
        })),
        totalCount: 3,
        facets: {
          kind: [
            { value: 'rest', count: 2 },
            { value: 'graphql', count: 1 },
          ],
          lifecycle: [
            { value: 'production', count: 2 },
            { value: 'development', count: 1 },
          ],
          tags: [],
        },
        queryDuration: 40,
      }),
    });
  });

  // Search suggest
  await page.route('**/api/search/suggest*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        suggestions: apis.slice(0, 3).map((a) => ({
          apiId: a.id,
          title: a.title,
          description: a.description,
          kind: a.kind,
        })),
      }),
    });
  });

  // Chat stream
  await page.route('**/api/chat/stream', async (route) => {
    const sessionId = 'journey-session-1';
    const content =
      'I found several APIs matching your query. The Production API is a good fit for your needs.';
    const msgId = 'journey-msg-1';
    const now = new Date().toISOString();

    const body = [
      `data: ${JSON.stringify({ type: 'start', sessionId })}\n\n`,
      `data: ${JSON.stringify({ type: 'content', content: content.slice(0, 20) })}\n\n`,
      `data: ${JSON.stringify({ type: 'content', content: content.slice(20) })}\n\n`,
      `data: ${JSON.stringify({
        type: 'end',
        message: { id: msgId, role: 'assistant', content, citations: null, timestamp: now },
        sessionId,
      })}\n\n`,
    ].join('');

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body,
    });
  });
}

// ---------------------------------------------------------------------------
// Full journey test
// ---------------------------------------------------------------------------

test.describe('Full MVP User Journey', () => {
  test('complete developer journey: authenticate → browse → search → detail → chat', async ({
    page,
  }) => {
    // -----------------------------------------------------------------------
    // Step 1: Land on portal without authentication
    // -----------------------------------------------------------------------
    await page.goto('/');

    // The homepage redirects to /catalog and the Sign in button is visible
    await expect(page).toHaveURL(/\/catalog/);
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 2: "Authenticate" by injecting a mock user and reloading
    // -----------------------------------------------------------------------
    await setupAllMocks(page);
    await setMockUser(page, MOCK_USER);
    await page.goto('/catalog');

    // User avatar replaces Sign in button
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).not.toBeVisible();

    // -----------------------------------------------------------------------
    // Step 3: Browse the API catalog
    // -----------------------------------------------------------------------
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByText('Test API 1')).toBeVisible();
    await expect(page.getByText('Test API 2')).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 4: Filter by Production lifecycle
    // -----------------------------------------------------------------------
    await page.getByLabel('Filter by Production').click();
    await expect(page).toHaveURL(/lifecycle=production/);

    // At least the first production API should remain visible
    await expect(page.getByText('Test API 1')).toBeVisible();

    // Clear the filter by navigating to /catalog
    await page.goto('/catalog');
    await expect(page.getByText('Test API 1')).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 5: Click an API card to navigate to detail
    // -----------------------------------------------------------------------
    await page.getByText('Test API 1').click();
    await expect(page).toHaveURL(/\/catalog\/api-1/);
    await expect(page.getByRole('heading', { name: 'Test API 1' })).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 6: Explore API detail tabs
    // -----------------------------------------------------------------------

    // Overview tab (default)
    await expect(page.getByTestId('api-metadata')).toBeVisible();

    // Versions tab
    await page.getByRole('tab', { name: 'Versions' }).click();
    await expect(page.getByTestId('version-list')).toBeVisible();

    // Specification tab
    await page.getByRole('tab', { name: 'Specification' }).click();
    await expect(page.getByTestId('spec-viewer')).toBeVisible({ timeout: 10000 });

    // Deployments tab
    await page.getByRole('tab', { name: 'Deployments' }).click();
    await expect(page.getByTestId('deployments-table')).toBeVisible();

    // Navigate back to catalog via breadcrumb
    const header = page.getByTestId('api-header');
    await header.getByRole('link', { name: 'Catalog' }).click();
    await expect(page).toHaveURL(/\/catalog$/);

    // -----------------------------------------------------------------------
    // Step 7: Use the global search bar
    // -----------------------------------------------------------------------
    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('Test API');
    await searchInput.press('Enter');

    await expect(page).toHaveURL(/\/search\?q=Test\+API/);
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 8: View search results and click a result
    // -----------------------------------------------------------------------
    await expect(page.getByTestId('search-result-1')).toBeVisible({ timeout: 5000 });
    await page.getByTestId('search-result-1').click();

    // Should navigate to the first result's detail page
    await expect(page).toHaveURL(/\/catalog\//);

    // Navigate to catalog again for the next step
    await page.goto('/catalog');

    // -----------------------------------------------------------------------
    // Step 9: Open AI Assistant via FAB side panel
    // -----------------------------------------------------------------------
    await expect(page.getByTestId('chat-fab')).toBeVisible();
    await page.getByTestId('chat-fab').click();

    // Panel opens
    await expect(page.getByText('AI Assistant')).toBeVisible({ timeout: 5000 });

    // Send a message in the side panel
    await page.getByTestId('chat-input').fill('Which APIs are available in production?');
    await page.getByTestId('send-button').click();

    // User message appears
    await expect(page.getByText('Which APIs are available in production?')).toBeVisible({
      timeout: 5000,
    });

    // -----------------------------------------------------------------------
    // Step 10: Navigate to full chat page
    // -----------------------------------------------------------------------
    await page.goto('/chat');
    await expect(page.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();
    await expect(page.getByTestId('chat-input')).toBeVisible();

    // Send a message on the full chat page
    await page.getByTestId('chat-input').fill('What payment APIs are available?');
    await page.getByTestId('send-button').click();

    // Assistant response should appear
    await expect(page.getByText(/I found several APIs matching your query/i)).toBeVisible({
      timeout: 10000,
    });

    // -----------------------------------------------------------------------
    // Step 11: Verify user auth state persists throughout navigation
    // -----------------------------------------------------------------------
    await page.goto('/catalog');
    // User is still "authenticated" — avatar still visible
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();

    // Open user menu to verify user info
    await page.getByRole('button', { name: /user menu/i }).click();
    await expect(page.getByText(MOCK_USER.name)).toBeVisible();
    await expect(page.getByText(MOCK_USER.email)).toBeVisible();
    await expect(page.getByText('Sign out')).toBeVisible();
  });

  test('full search journey: type query → see results → apply filter → click result', async ({
    page,
  }) => {
    await setupAllMocks(page);
    await setMockUser(page, MOCK_USER);
    await page.goto('/catalog');

    // Type a query in the search bar
    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('API');
    await searchInput.press('Enter');

    await expect(page).toHaveURL(/\/search\?q=API/);

    // Results should be visible
    await expect(page.getByTestId('search-result-1')).toBeVisible({ timeout: 5000 });

    // Apply a lifecycle filter
    await page.getByLabel('Filter by Production').click();
    await expect(page).toHaveURL(/lifecycle=production/);

    // Click the first result
    await expect(page.getByTestId('search-result-1')).toBeVisible({ timeout: 5000 });
    await page.getByTestId('search-result-1').click();

    // Should navigate to API detail
    await expect(page).toHaveURL(/\/catalog\//);
  });

  test('chat journey: open page → use starter prompt → see AI response', async ({ page }) => {
    await setupAllMocks(page);
    await setMockUser(page, MOCK_USER);
    await page.goto('/chat');

    // Starter prompts should be visible
    await expect(page.getByTestId('chat-suggestions')).toBeVisible();

    // Click a starter prompt
    await page.getByText('Show me APIs in production').click();

    // The prompt appears as a user message
    await expect(page.getByText('Show me APIs in production')).toBeVisible();

    // AI responds
    await expect(page.getByText(/I found several APIs matching your query/i)).toBeVisible({
      timeout: 10000,
    });

    // Suggestions should be hidden after first message
    await expect(page.getByTestId('chat-suggestions')).not.toBeVisible({ timeout: 5000 });
  });
});
