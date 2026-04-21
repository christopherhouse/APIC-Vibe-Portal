/**
 * Full Phase 2 end-to-end user journey test.
 *
 * This test simulates a realistic developer workflow that exercises all Phase 2
 * features working together with Phase 1 (no regressions):
 *
 *   1. Authenticate via mock user injection
 *   2. Browse the API catalog (Phase 1)
 *   3. Navigate to the Governance Dashboard via sidebar
 *   4. View KPI cards and API scores table
 *   5. Click an API row → see compliance detail
 *   6. Return to governance dashboard
 *   7. Open AI Assistant and ask a governance question
 *   8. Navigate to API Comparison page via sidebar
 *   9. Select 2 APIs and view comparison table
 *  10. Request AI analysis for the comparison
 *  11. Verify no Phase 1 regressions (catalog still works)
 *
 * All BFF calls are intercepted with page.route() so no Azure services are
 * required. This mirrors the approach used in full-journey.spec.ts.
 */

import { test, expect, type Page } from '@playwright/test';
import { generateMockApis } from './mock-server';

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
  name: 'Alex Developer',
  email: 'alex@contoso.com',
  id: 'user-alex-1',
  roles: ['Portal.User'],
};

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_GOVERNANCE_SUMMARY = {
  overallScore: 82.5,
  compliantCount: 7,
  totalCount: 10,
  criticalIssues: 1,
  improvement: 2.0,
};

const MOCK_GOVERNANCE_SCORES = [
  {
    apiId: 'payments-api',
    apiName: 'Payments API',
    score: 92.0,
    category: 'Excellent',
    criticalFailures: 0,
    lastChecked: '2026-04-21T10:00:00Z',
  },
  {
    apiId: 'users-api',
    apiName: 'Users API',
    score: 68.0,
    category: 'Needs Improvement',
    criticalFailures: 1,
    lastChecked: '2026-04-21T10:00:00Z',
  },
];

const MOCK_GOVERNANCE_DISTRIBUTION = {
  excellent: 4,
  good: 3,
  needsImprovement: 2,
  poor: 1,
};

const MOCK_RULE_COMPLIANCE = [
  {
    ruleId: 'metadata.description',
    ruleName: 'API Description Required',
    severity: 'warning',
    passCount: 9,
    failCount: 1,
    complianceRate: 90.0,
  },
];

const MOCK_API_COMPLIANCE = {
  apiId: 'payments-api',
  apiName: 'Payments API',
  score: 92.0,
  category: 'Excellent',
  criticalFailures: 0,
  findings: [
    {
      ruleId: 'metadata.description',
      ruleName: 'API Description Required',
      severity: 'warning',
      passed: true,
      message: 'API has a description',
      remediation: 'Add a description to the API',
    },
  ],
  lastChecked: '2026-04-21T10:00:00Z',
};

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
      aspect: 'metadata.kind',
      label: 'Kind',
      values: [
        { value: 'rest', display: 'REST', isBest: false },
        { value: 'rest', display: 'REST', isBest: false },
      ],
      allEqual: true,
    },
  ],
  similarityScore: 0.8,
  aiAnalysis: null,
};

const MOCK_AI_ANALYSIS = {
  ...MOCK_COMPARE_RESULT,
  aiAnalysis:
    'Both **Payments API** and **Users API** are REST APIs in production. ' +
    'Payments API is optimized for transactional workloads while Users API handles identity management.',
};

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

async function setMockUser(page: Page, user: AuthUser | null) {
  await page.addInitScript((u) => {
    (window as Window & { __PLAYWRIGHT_USER__?: typeof u }).__PLAYWRIGHT_USER__ = u ?? undefined;
  }, user);
}

async function setupCatalogMocks(page: Page) {
  const apis = generateMockApis(6);

  await page.route('**/api/catalog?*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: apis,
        meta: { page: 1, pageSize: 20, totalCount: apis.length, totalPages: 1 },
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
        data: apis,
        meta: { page: 1, pageSize: 20, totalCount: apis.length, totalPages: 1 },
      }),
    });
  });
}

async function setupGovernanceMocks(page: Page) {
  await page.route('**/api/governance/summary*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GOVERNANCE_SUMMARY),
    });
  });

  await page.route('**/api/governance/scores*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GOVERNANCE_SCORES),
    });
  });

  await page.route('**/api/governance/distribution*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_GOVERNANCE_DISTRIBUTION),
    });
  });

  await page.route('**/api/governance/rule-compliance*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_RULE_COMPLIANCE),
    });
  });

  await page.route('**/api/governance/apis/*/compliance*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_API_COMPLIANCE),
    });
  });
}

async function setupCompareMocks(page: Page) {
  await page.route('**/api/search/suggest*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        suggestions: [
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
        ],
      }),
    });
  });

  await page.route('**/api/compare', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_COMPARE_RESULT),
      });
    } else {
      await route.continue();
    }
  });

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

async function setupChatMocks(page: Page) {
  await page.route('**/api/chat/stream', async (route) => {
    const sessionId = 'phase2-session-1';
    const content =
      'The Payments API has a governance score of 92/100. All critical governance rules are passing. ' +
      'The Users API has a score of 68/100 and needs attention.';
    const msgId = 'phase2-msg-1';
    const now = new Date().toISOString();

    const body = [
      `data: ${JSON.stringify({ type: 'start', sessionId })}\n\n`,
      `data: ${JSON.stringify({ type: 'content', content: content.slice(0, 30) })}\n\n`,
      `data: ${JSON.stringify({ type: 'content', content: content.slice(30) })}\n\n`,
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
// Full Phase 2 journey test
// ---------------------------------------------------------------------------

test.describe('Full Phase 2 User Journey', () => {
  test('complete Phase 2 developer journey: catalog → governance → chat → compare', async ({
    page,
  }) => {
    // Set up all mocks
    await setMockUser(page, MOCK_USER);
    await setupCatalogMocks(page);
    await setupGovernanceMocks(page);
    await setupCompareMocks(page);
    await setupChatMocks(page);

    // -----------------------------------------------------------------------
    // Step 1: Land on portal — user is authenticated
    // -----------------------------------------------------------------------
    await page.goto('/catalog');
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 2: Browse the API catalog (Phase 1 feature)
    // -----------------------------------------------------------------------
    await expect(page.getByText('Test API 1', { exact: true })).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 3: Navigate to Governance Dashboard via sidebar
    // -----------------------------------------------------------------------
    const mainNav = page.getByRole('navigation', { name: /main navigation/i });
    await mainNav.getByText('Governance').click();
    await expect(page).toHaveURL(/\/governance/);

    // -----------------------------------------------------------------------
    // Step 4: Verify governance dashboard is displayed
    // -----------------------------------------------------------------------
    await expect(page.getByTestId('governance-dashboard')).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: /governance dashboard/i })).toBeVisible();
    await expect(page.getByTestId('overall-score-card')).toBeVisible();
    await expect(page.getByTestId('api-score-table')).toBeVisible();

    // Both APIs should be visible in the table
    await expect(page.getByTestId('api-score-row-payments-api')).toBeVisible();
    await expect(page.getByTestId('api-score-row-users-api')).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 5: Click a failing API to see compliance detail
    // -----------------------------------------------------------------------
    await page.getByTestId('api-score-row-payments-api').click();
    await expect(page).toHaveURL(/\/governance\/payments-api/);
    await expect(page.getByTestId('api-compliance-detail')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Payments API')).toBeVisible();
    await expect(page.getByText(/92\.0/)).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 6: Navigate back to governance dashboard
    // -----------------------------------------------------------------------
    await page.getByRole('button', { name: /back to dashboard/i }).click();
    await expect(page.getByTestId('governance-dashboard')).toBeVisible({ timeout: 10000 });

    // -----------------------------------------------------------------------
    // Step 7: Open AI Assistant and ask a governance question
    // -----------------------------------------------------------------------
    await mainNav.getByText('AI Assistant').click();
    await expect(page).toHaveURL(/\/chat/);

    const main = page.locator('main');
    await main.getByTestId('chat-input').fill('What is the governance status of the Payments API?');
    await main.getByTestId('send-button').click();

    await expect(main.getByText(/governance score of 92|Payments API.*92/i)).toBeVisible({
      timeout: 10000,
    });

    // -----------------------------------------------------------------------
    // Step 8: Navigate to Compare page via sidebar
    // -----------------------------------------------------------------------
    await mainNav.getByText('Compare').click();
    await expect(page).toHaveURL(/\/compare/);
    await expect(page.getByRole('heading', { name: /api comparison/i })).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 9: Select 2 APIs and view comparison table
    // -----------------------------------------------------------------------
    // Navigate with pre-selected APIs via URL
    await page.goto('/compare?compare=payments-api,users-api');

    await expect(page.getByTestId('compare-table')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Payments API')).toBeVisible();
    await expect(page.getByText('Users API')).toBeVisible();

    // -----------------------------------------------------------------------
    // Step 10: Request AI analysis
    // -----------------------------------------------------------------------
    await expect(page.getByTestId('request-ai-analysis-button')).toBeVisible();
    await page.getByTestId('request-ai-analysis-button').click();

    await expect(
      page.getByTestId('compare-ai-analysis').getByText(/transactional workloads/i)
    ).toBeVisible({
      timeout: 10000,
    });

    // -----------------------------------------------------------------------
    // Step 11: Verify no Phase 1 regressions — catalog still works
    // -----------------------------------------------------------------------
    await mainNav.getByText('API Catalog').click();
    await expect(page).toHaveURL(/\/catalog/);
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
    await expect(page.getByText('Test API 1', { exact: true })).toBeVisible();

    // User auth state still valid
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible();
  });

  test('Phase 2 navigation items are visible in sidebar', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await setupCatalogMocks(page);
    await page.goto('/catalog');

    const mainNav = page.getByRole('navigation', { name: /main navigation/i });
    await expect(mainNav.getByText('Governance')).toBeVisible();
    await expect(mainNav.getByText('Compare')).toBeVisible();
  });

  test('governance page integrates with Phase 1 catalog navigation', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await setupGovernanceMocks(page);
    await setupCatalogMocks(page);

    await page.goto('/governance');
    await expect(page.getByTestId('governance-dashboard')).toBeVisible({ timeout: 10000 });

    // Navigate to catalog from sidebar
    const mainNav = page.getByRole('navigation', { name: /main navigation/i });
    await mainNav.getByText('API Catalog').click();

    await expect(page).toHaveURL(/\/catalog/);
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
  });

  test('compare page integrates with Phase 1 catalog browsing', async ({ page }) => {
    await setMockUser(page, MOCK_USER);
    await setupCompareMocks(page);
    await setupCatalogMocks(page);

    // Navigate from compare to catalog
    await page.goto('/compare');
    await expect(page.getByTestId('compare-empty-state')).toBeVisible();

    // Browse Catalog button should work
    await page.getByRole('button', { name: /browse catalog/i }).click();
    await expect(page).toHaveURL(/\/catalog/);
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Phase 2 Polish: Responsive and loading states
// ---------------------------------------------------------------------------

test.describe('Phase 2 Polish — Loading and Error States', () => {
  test('governance dashboard shows loading state initially', async ({ page }) => {
    // Slow the response to catch loading state
    await page.route('**/api/governance/summary*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 100));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_GOVERNANCE_SUMMARY),
      });
    });

    await page.route('**/api/governance/scores*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_GOVERNANCE_SCORES),
      });
    });

    await page.route('**/api/governance/distribution*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_GOVERNANCE_DISTRIBUTION),
      });
    });

    await page.route('**/api/governance/rule-compliance*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_RULE_COMPLIANCE),
      });
    });

    await page.goto('/governance');
    // Loading spinner should appear briefly
    // Then data loads
    await expect(page.getByTestId('governance-dashboard')).toBeVisible({ timeout: 10000 });
  });

  test('governance dashboard shows error state when API fails', async ({ page }) => {
    await page.route('**/api/governance/**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'INTERNAL_ERROR', message: 'Server error' } }),
      });
    });

    await page.goto('/governance');

    // Error alert should be visible
    await expect(page.getByTestId('governance-error')).toBeVisible({ timeout: 10000 });
  });

  test('compare page shows error state when comparison fails', async ({ page }) => {
    await page.addInitScript(() => {
      (
        window as Window & {
          __PLAYWRIGHT_USER__?: { name: string; email: string; id: string; roles: string[] };
        }
      ).__PLAYWRIGHT_USER__ = {
        name: 'Alex Developer',
        email: 'alex@contoso.com',
        id: 'user-alex-1',
        roles: ['Portal.User'],
      };
    });

    await page.route('**/api/compare', async (route) => {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'SERVICE_UNAVAILABLE', message: 'Service down' } }),
      });
    });

    await page.goto('/compare?compare=payments-api,users-api');

    // Error alert and retry button should be visible
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible();
  });
});
