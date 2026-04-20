import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockSummary = {
  overallScore: 78.5,
  compliantCount: 8,
  totalCount: 10,
  criticalIssues: 2,
  improvement: 1.5,
};

const mockScores = [
  {
    apiId: 'payments-api',
    apiName: 'Payments API',
    score: 92.0,
    category: 'Excellent',
    criticalFailures: 0,
    lastChecked: '2026-04-20T18:00:00Z',
  },
  {
    apiId: 'users-api',
    apiName: 'Users API',
    score: 64.0,
    category: 'Needs Improvement',
    criticalFailures: 1,
    lastChecked: '2026-04-20T18:00:00Z',
  },
];

const mockDistribution = {
  excellent: 3,
  good: 5,
  needsImprovement: 2,
  poor: 0,
};

const mockRuleCompliance = [
  {
    ruleId: 'metadata.description',
    ruleName: 'API Description Required',
    severity: 'warning',
    passCount: 8,
    failCount: 2,
    complianceRate: 80.0,
  },
  {
    ruleId: 'versioning.has-version',
    ruleName: 'API Must Have Version',
    severity: 'critical',
    passCount: 10,
    failCount: 0,
    complianceRate: 100.0,
  },
];

const mockApiCompliance = {
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
    {
      ruleId: 'versioning.has-version',
      ruleName: 'API Must Have Version',
      severity: 'critical',
      passed: false,
      message: 'No version defined',
      remediation: 'Add at least one API version',
    },
  ],
  lastChecked: '2026-04-20T18:00:00Z',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function mockGovernanceApis(page: Page) {
  await page.route('**/api/governance/summary*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockSummary),
    });
  });

  await page.route('**/api/governance/scores*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockScores),
    });
  });

  await page.route('**/api/governance/distribution*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockDistribution),
    });
  });

  await page.route('**/api/governance/rule-compliance*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockRuleCompliance),
    });
  });

  await page.route('**/api/governance/apis/*/compliance*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockApiCompliance),
    });
  });
}

// ---------------------------------------------------------------------------
// Dashboard tests
// ---------------------------------------------------------------------------

test.describe('Governance Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockGovernanceApis(page);
    await page.goto('/governance');
  });

  test('should display governance dashboard', async ({ page }) => {
    await expect(page.getByTestId('governance-dashboard')).toBeVisible();
    await expect(page.getByRole('heading', { name: /governance dashboard/i })).toBeVisible();
  });

  test('should display KPI cards', async ({ page }) => {
    await expect(page.getByTestId('overall-score-card')).toBeVisible();
    await expect(page.getByTestId('compliant-apis-card')).toBeVisible();
    await expect(page.getByTestId('critical-issues-card')).toBeVisible();
    await expect(page.getByTestId('total-apis-card')).toBeVisible();
  });

  test('should display charts', async ({ page }) => {
    await expect(page.getByTestId('score-distribution-chart')).toBeVisible();
    await expect(page.getByTestId('rule-compliance-chart')).toBeVisible();
  });

  test('should display API scores table', async ({ page }) => {
    await expect(page.getByTestId('api-score-table')).toBeVisible();
    // Verify mock data rows appear
    await expect(page.getByTestId('api-score-row-payments-api')).toBeVisible();
    await expect(page.getByTestId('api-score-row-users-api')).toBeVisible();
  });

  test('should filter API scores', async ({ page }) => {
    const filterInput = page.getByTestId('api-score-table-filter');
    await expect(filterInput).toBeVisible();

    // Type in filter
    await filterInput.fill('payments');
    await expect(filterInput).toHaveValue('payments');

    // Only the matching row should remain visible
    await expect(page.getByTestId('api-score-row-payments-api')).toBeVisible();
    await expect(page.getByTestId('api-score-row-users-api')).not.toBeVisible();
  });

  test('should navigate to API detail on row click', async ({ page }) => {
    // Click the first mocked row unconditionally
    await page.getByTestId('api-score-row-payments-api').click();

    // Should navigate to detail page
    await expect(page).toHaveURL(/\/governance\/payments-api/);
    await expect(page.getByTestId('api-compliance-detail')).toBeVisible();
  });

  test('should refresh data', async ({ page }) => {
    const refreshButton = page.getByTestId('refresh-button');
    await expect(refreshButton).toBeVisible();
    await refreshButton.click();

    // Dashboard should still be visible after refresh
    await expect(page.getByTestId('governance-dashboard')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// API Compliance Detail tests
// ---------------------------------------------------------------------------

test.describe('API Compliance Detail', () => {
  test('should display compliance detail for an API', async ({ page }) => {
    await mockGovernanceApis(page);
    await page.goto('/governance');

    // Click the mocked API row
    await page.getByTestId('api-score-row-payments-api').click();

    // Should show compliance detail
    await expect(page.getByTestId('api-compliance-detail')).toBeVisible();

    // Should display score and API name
    await expect(page.getByText('Payments API')).toBeVisible();
    await expect(page.getByText(/92\.0/)).toBeVisible();
  });

  test('should navigate back to dashboard', async ({ page }) => {
    await mockGovernanceApis(page);
    await page.goto('/governance');

    await page.getByTestId('api-score-row-payments-api').click();
    await expect(page.getByTestId('api-compliance-detail')).toBeVisible();

    // Click back button
    await page.getByRole('button', { name: /back to dashboard/i }).click();

    // Should be back on dashboard
    await expect(page.getByTestId('governance-dashboard')).toBeVisible();
  });
});
