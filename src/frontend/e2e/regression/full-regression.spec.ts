/**
 * Full regression E2E test suite.
 *
 * This file runs a curated set of representative tests across all three
 * feature phases to confirm that the complete APIC Vibe Portal is
 * regression-free before a release.
 *
 * Structure:
 *   Phase 1 (MVP):      App shell, auth, catalog, search, API detail, chat
 *   Phase 2 (Phase 2):  Governance dashboard, API comparison
 *   Phase 3 (Phase 3):  Analytics (admin), metadata scores
 *   Cross-cutting:      Accessibility, navigation, 404
 *
 * All BFF calls are intercepted with page.route().
 */

import { test, expect, type Page } from '@playwright/test';
import { generateMockApis, generateMockSpec } from '../mock-server';
import AxeBuilder from '@axe-core/playwright';

// ---------------------------------------------------------------------------
// Shared test data
// ---------------------------------------------------------------------------

interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

const REGULAR_USER: AuthUser = {
  name: 'Reg User',
  email: 'reg@contoso.com',
  id: 'user-reg-1',
  roles: ['Portal.User'],
};

const ADMIN_USER: AuthUser = {
  name: 'Admin User',
  email: 'admin@contoso.com',
  id: 'user-admin-1',
  roles: ['Portal.Admin'],
};

async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

async function setupCoreMocks(page: Page) {
  const apis = generateMockApis(10);

  await page.route('**/api/catalog?*', async (route) => {
    const url = new URL(route.request().url());
    const lifecycle = url.searchParams.get('lifecycle');
    const kind = url.searchParams.get('kind');
    let filtered = [...apis];
    if (lifecycle) filtered = filtered.filter((a) => a.lifecycleStage === lifecycle);
    if (kind) filtered = filtered.filter((a) => a.kind === kind);
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
        meta: { page: 1, pageSize: 20, totalCount: 10, totalPages: 1 },
      }),
    });
  });

  await page.route(/\/api\/catalog\/[^/]+$/, async (route) => {
    const apiId = new URL(route.request().url()).pathname.split('/').pop();
    const api = apis.find((a) => a.id === apiId);
    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(api ? { data: api } : { error: { code: 'NOT_FOUND' } }),
    });
  });

  await page.route(/\/api\/catalog\/[^/]+\/versions$/, async (route) => {
    const parts = new URL(route.request().url()).pathname.split('/');
    const api = apis.find((a) => a.id === parts[parts.length - 2]);
    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(api ? { data: api.versions } : { error: { code: 'NOT_FOUND' } }),
    });
  });

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
                title: `${api!.title} ${version.title}`,
                specificationType: 'openapi',
                specificationVersion: '3.0.3',
                content: generateMockSpec(api!.title, version.title),
              },
            }
          : { error: { code: 'NOT_FOUND' } }
      ),
    });
  });

  await page.route(/\/api\/catalog\/[^/]+\/deployments$/, async (route) => {
    const parts = new URL(route.request().url()).pathname.split('/');
    const api = apis.find((a) => a.id === parts[parts.length - 2]);
    await route.fulfill({
      status: api ? 200 : 404,
      contentType: 'application/json',
      body: JSON.stringify(api ? { data: api.deployments } : { error: { code: 'NOT_FOUND' } }),
    });
  });

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
        facets: { kind: [], lifecycle: [], tags: [] },
        queryDuration: 25,
      }),
    });
  });

  await page.route('**/api/chat/stream', async (route) => {
    const content = 'Here are the APIs that match your query.';
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: [
        `data: ${JSON.stringify({ type: 'start', sessionId: 'regression-session' })}\n\n`,
        `data: ${JSON.stringify({ type: 'content', content })}\n\n`,
        `data: ${JSON.stringify({
          type: 'end',
          message: {
            id: 'msg-r1',
            role: 'assistant',
            content,
            citations: null,
            timestamp: new Date().toISOString(),
          },
          sessionId: 'regression-session',
        })}\n\n`,
      ].join(''),
    });
  });

  await page.route('**/api/governance/summary', (route) =>
    route.fulfill({
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
    })
  );

  await page.route('**/api/governance/scores*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: apis.slice(0, 4).map((a, i) => ({
          apiId: a.id,
          apiName: a.title,
          score: 90 - i * 8,
          category: 'Good',
          criticalFailures: 0,
          lastChecked: new Date().toISOString(),
        })),
      }),
    })
  );

  await page.route('**/api/governance/distribution*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: { excellent: 4, good: 3, needsImprovement: 2, nonCompliant: 1 },
      }),
    })
  );

  await page.route('**/api/compare*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          apis: apis.slice(0, 2),
          attributes: [{ key: 'kind', label: 'API Type' }],
        },
      }),
    });
  });

  await page.route('**/api/analytics/*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: {} }),
    })
  );

  await page.route('**/api/admin/*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ agents: [] }),
    })
  );
}

// ---------------------------------------------------------------------------
// Phase 1 — MVP regression tests
// ---------------------------------------------------------------------------

test.describe('Regression — Phase 1: App shell & auth', () => {
  test('root URL redirects to /catalog', async ({ page }) => {
    await setupCoreMocks(page);
    await page.goto('/');
    await expect(page).toHaveURL(/\/catalog/);
  });

  test('sign in button visible when unauthenticated', async ({ page }) => {
    await setupCoreMocks(page);
    await page.goto('/catalog');
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('user avatar visible when authenticated', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/catalog');
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();
  });
});

test.describe('Regression — Phase 1: Catalog', () => {
  test('catalog displays API cards', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/catalog');

    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByText('Test API 1', { exact: true })).toBeVisible();
  });

  test('lifecycle filter narrows results', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/catalog');

    await page.getByLabel('Filter by Production').click();
    await expect(page).toHaveURL(/lifecycle=production/);
  });

  test('clicking an API card navigates to detail', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/catalog');

    await page.getByText('Test API 1', { exact: true }).click();
    await expect(page).toHaveURL(/\/catalog\/api-1/);
    await expect(page.getByRole('heading', { name: 'Test API 1' })).toBeVisible();
  });
});

test.describe('Regression — Phase 1: Search', () => {
  test('global search navigates to search page', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/catalog');

    const searchInput = page.getByRole('combobox', { name: /search/i });
    await searchInput.fill('payment');
    await searchInput.press('Enter');

    await expect(page).toHaveURL(/\/search\?q=payment/i);
  });

  test('search results are displayed', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/search?q=test');

    await expect(page.getByTestId('search-result-api-1')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Regression — Phase 1: AI Chat', () => {
  test('chat page renders correctly', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/chat');

    const main = page.locator('main');
    await expect(main.getByRole('heading', { name: /AI Assistant/i })).toBeVisible();
    await expect(main.getByTestId('chat-input')).toBeVisible();
  });

  test('chat responds to user messages', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/chat');

    const main = page.locator('main');
    await main.getByTestId('chat-input').fill('Show me available APIs');
    await main.getByTestId('send-button').click();

    await expect(main.getByText(/Here are the APIs/i)).toBeVisible({ timeout: 10000 });
  });
});

// ---------------------------------------------------------------------------
// Phase 2 — Governance + Compare regression tests
// ---------------------------------------------------------------------------

test.describe('Regression — Phase 2: Governance', () => {
  test('governance dashboard renders with summary cards', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/governance');

    await expect(page.getByRole('heading', { name: /governance/i })).toBeVisible();
    await expect(page.getByTestId('governance-summary')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Regression — Phase 2: API Comparison', () => {
  test('comparison page renders', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/compare');

    await expect(page.getByRole('heading', { name: /compar/i })).toBeVisible({ timeout: 5000 });
  });
});

// ---------------------------------------------------------------------------
// Phase 3 — Analytics regression tests
// ---------------------------------------------------------------------------

test.describe('Regression — Phase 3: Admin Analytics', () => {
  test('admin can access analytics dashboard', async ({ page }) => {
    await setMockUser(page, ADMIN_USER);
    await setupCoreMocks(page);
    await page.goto('/analytics');

    await expect(page.getByRole('heading', { name: /analytics/i })).toBeVisible({ timeout: 5000 });
  });

  test('regular user is blocked from analytics dashboard', async ({ page }) => {
    await setMockUser(page, REGULAR_USER);
    await setupCoreMocks(page);
    await page.goto('/analytics');

    // Regular users see access denied on the analytics page
    await expect(page.getByTestId('access-denied-icon')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/access denied/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Cross-cutting regression tests
// ---------------------------------------------------------------------------

test.describe('Regression — Cross-cutting: Navigation', () => {
  test('404 page renders for unknown routes', async ({ page }) => {
    await setupCoreMocks(page);
    await page.goto('/this-does-not-exist');
    await expect(page.getByRole('heading', { name: /not found/i })).toBeVisible();
  });
});

test.describe('Regression — Cross-cutting: Accessibility', () => {
  test('catalog page has no critical axe violations', async ({ page }) => {
    await setupCoreMocks(page);
    await page.goto('/catalog');
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const critical = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(critical).toHaveLength(0);
  });
});
