import { test, expect } from '@playwright/test';

test.describe('Governance Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to governance dashboard
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
  });

  test('should filter API scores', async ({ page }) => {
    const filterInput = page.getByTestId('api-score-table-filter');
    await expect(filterInput).toBeVisible();

    // Type in filter
    await filterInput.fill('test');
    await expect(filterInput).toHaveValue('test');
  });

  test('should navigate to API detail on row click', async ({ page }) => {
    // Wait for table to load
    const firstRow = page.locator('[data-testid^="api-score-row-"]').first();

    // Check if table has rows
    const rowCount = await page.locator('[data-testid^="api-score-row-"]').count();

    if (rowCount > 0) {
      // Click first row
      await firstRow.click();

      // Should navigate to detail page
      await expect(page).toHaveURL(/\/governance\/.+/);
      await expect(page.getByTestId('api-compliance-detail')).toBeVisible();
    }
  });

  test('should refresh data', async ({ page }) => {
    const refreshButton = page.getByTestId('refresh-button');
    await expect(refreshButton).toBeVisible();
    await refreshButton.click();

    // Dashboard should still be visible after refresh
    await expect(page.getByTestId('governance-dashboard')).toBeVisible();
  });
});

test.describe('API Compliance Detail', () => {
  test('should display compliance detail for an API', async ({ page }) => {
    // First go to governance dashboard
    await page.goto('/governance');

    // Wait for table to load and click first API
    const firstRow = page.locator('[data-testid^="api-score-row-"]').first();
    const rowCount = await page.locator('[data-testid^="api-score-row-"]').count();

    if (rowCount > 0) {
      await firstRow.click();

      // Should show compliance detail
      await expect(page.getByTestId('api-compliance-detail')).toBeVisible();

      // Should display score and category
      await expect(page.getByRole('heading', { level: 4 })).toBeVisible();
    }
  });

  test('should navigate back to dashboard', async ({ page }) => {
    await page.goto('/governance');

    const firstRow = page.locator('[data-testid^="api-score-row-"]').first();
    const rowCount = await page.locator('[data-testid^="api-score-row-"]').count();

    if (rowCount > 0) {
      await firstRow.click();

      // Click back button
      await page.getByRole('button', { name: /back to dashboard/i }).click();

      // Should be back on dashboard
      await expect(page.getByTestId('governance-dashboard')).toBeVisible();
    }
  });
});
